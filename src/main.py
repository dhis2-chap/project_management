"""Main script for OKR-Jira analysis"""

import logging
from datetime import date, timedelta
from pathlib import Path
from rich.logging import RichHandler
from rich.console import Console

from .config import Config, set_config
from .database.db import Database
from .okr.parser import OKRParser
from .jira.client import JiraClient
from .matching.claude_matcher import ClaudeMatcher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)
console = Console()


def main():
    """Main execution function"""
    console.print("[bold blue]OKR-Jira Analysis System[/bold blue]")
    console.print("=" * 60)

    try:
        # 1. Load configuration
        console.print("\n[cyan]1. Loading configuration...[/cyan]")
        config = Config()
        config.validate()
        set_config(config)
        console.print(f"  ✓ Project: {config.jira_project_key}")
        console.print(f"  ✓ Analysis period: Last {config.jira_analysis_days} days")

        # 2. Initialize database
        console.print("\n[cyan]2. Initializing database...[/cyan]")
        db = Database(config.database_path)
        console.print(f"  ✓ Database: {config.database_path}")

        # 3. Load OKRs
        console.print("\n[cyan]3. Loading OKRs...[/cyan]")
        okr_parser = OKRParser(config.okr_directory)
        okr_set = okr_parser.load_okrs(
            auto_detect=config.okr_auto_detect_latest,
            default_file=config.okr_default_file
        )
        console.print(f"  ✓ Period: {okr_set.period}")
        console.print(f"  ✓ Objectives: {len(okr_set.objectives)}")

        # Store OKRs in database
        for obj in okr_set.objectives:
            for kr in obj.key_results:
                db.store_okr(
                    okr_id=obj.get_key_result_id(kr.number),
                    objective_number=obj.number,
                    objective_title=obj.title,
                    key_result_number=kr.number,
                    key_result_text=kr.text,
                    okr_period=okr_set.period
                )

        # 4. Fetch Jira issues
        console.print("\n[cyan]4. Fetching Jira issues...[/cyan]")
        jira_client = JiraClient(config.jira_project_key, config.jira_analysis_days)

        try:
            issues = jira_client.fetch_all_issues()
            console.print(f"  ✓ Fetched {len(issues)} issues")
        except Exception as e:
            console.print(f"  [red]✗ Failed to fetch issues: {e}[/red]")
            console.print("\n[yellow]Note: Make sure acli is installed and authenticated:[/yellow]")
            console.print("  1. Install: brew install atlassian-cli")
            console.print("  2. Login: acli auth login")
            return 1

        if not issues:
            console.print("\n[yellow]No issues found in the analysis period.[/yellow]")
            return 0

        # Store issues in database
        for issue in issues:
            db.store_issue(
                key=issue.key,
                summary=issue.summary,
                description=issue.description,
                issue_type=issue.issue_type,
                status=issue.status,
                assignee=issue.assignee
            )

        # 5. Match issues to OKRs
        console.print("\n[cyan]5. Matching issues to OKRs with Claude AI...[/cyan]")
        console.print(f"  [dim]This may take a while ({len(issues)} API calls)...[/dim]")

        matcher = ClaudeMatcher(config.anthropic_api_key, config.claude_model)
        match_results = matcher.match_issues(issues, okr_set)

        # 6. Store results in database
        console.print("\n[cyan]6. Storing results...[/cyan]")
        week_start = date.today() - timedelta(days=config.jira_analysis_days)

        aligned_count = 0
        unaligned_count = 0

        for issue in issues:
            result = match_results[issue.key]

            if result.get('no_okr_match', False):
                # Store as unaligned
                db.store_unaligned_issue(
                    issue_key=issue.key,
                    week_start=week_start,
                    reasoning=result.get('no_match_reasoning', 'No matching OKRs found')
                )
                unaligned_count += 1
            else:
                # Store matches
                for match in result.get('matches', []):
                    if match['confidence'] >= config.confidence_threshold:
                        # Construct OKR ID from objective and key result
                        obj_id = match['objective_id'].replace('obj', '')
                        kr_id = match['key_result_id'].replace('kr', '')

                        # Handle formats like "1", "1.2", "kr1.2", etc.
                        try:
                            obj_num = int(float(obj_id))
                            kr_num = int(float(kr_id))
                        except ValueError:
                            logger.warning(f"Invalid OKR ID format for {issue.key}: obj={match['objective_id']}, kr={match['key_result_id']}")
                            continue

                        okr_id = f"obj{obj_num}_kr{kr_num}"

                        db.store_mapping(
                            issue_key=issue.key,
                            okr_id=okr_id,
                            confidence=match['confidence'],
                            reasoning=match['reasoning'],
                            category=issue.category,
                            week_start=week_start
                        )
                aligned_count += 1

        # Store weekly snapshot
        week_end = date.today()
        db.store_weekly_snapshot(
            week_start=week_start,
            week_end=week_end,
            total_issues=len(issues),
            aligned_issues=aligned_count,
            unaligned_issues=unaligned_count,
            okr_period=okr_set.period
        )

        # 7. Generate report
        console.print("\n[cyan]7. Generating markdown report...[/cyan]")
        from .reporting.metrics import MetricsCalculator
        from .reporting.markdown_generator import MarkdownReportGenerator

        metrics = MetricsCalculator(db, okr_set, week_start)
        report_gen = MarkdownReportGenerator(metrics, week_start, week_end)
        report_file = report_gen.generate_report(config.report_output_dir)

        console.print(f"  ✓ Report: {report_file}")

        # 8. Summary
        console.print("\n[bold green]✓ Analysis Complete![/bold green]")
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Total issues analyzed: {len(issues)}")
        console.print(f"  Aligned with OKRs: {aligned_count} ({aligned_count/len(issues)*100:.1f}%)")
        console.print(f"  Unaligned: {unaligned_count} ({unaligned_count/len(issues)*100:.1f}%)")

        console.print(f"\n[dim]Database: {config.database_path}[/dim]")
        console.print(f"[dim]Report: {report_file}[/dim]")

        return 0

    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
