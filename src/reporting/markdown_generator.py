"""Markdown report generator for OKR analysis"""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Any
from .metrics import MetricsCalculator

logger = logging.getLogger(__name__)


class MarkdownReportGenerator:
    """Generate markdown reports from OKR analysis data"""

    def __init__(self, metrics: MetricsCalculator, week_start: date, week_end: date):
        """
        Initialize report generator

        Args:
            metrics: MetricsCalculator instance
            week_start: Start date of analysis period
            week_end: End date of analysis period
        """
        self.metrics = metrics
        self.week_start = week_start
        self.week_end = week_end

    def generate_report(self, output_path: Path) -> Path:
        """
        Generate complete markdown report

        Args:
            output_path: Directory to save report

        Returns:
            Path to generated report file
        """
        logger.info("Generating markdown report...")

        # Calculate all metrics
        coverage = self.metrics.calculate_okr_coverage()
        summary = self.metrics.calculate_summary_stats(coverage)
        underprioritized = self.metrics.identify_underprioritized_okrs(coverage)
        unaligned = self.metrics.get_unaligned_issues()
        top_issues = self.metrics.get_top_issues_by_okr(coverage, limit=3)

        # Generate report sections
        sections = []
        sections.append(self._generate_header())
        sections.append(self._generate_summary(summary))
        sections.append(self._generate_okr_coverage(coverage, top_issues))
        sections.append(self._generate_underprioritized(underprioritized))
        sections.append(self._generate_unaligned(unaligned))
        sections.append(self._generate_footer())

        # Combine and write
        report = "\n\n".join(sections)

        # Create output directory if needed
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename with date
        filename = f"okr_analysis_{self.week_start.strftime('%Y-%m-%d')}.md"
        report_file = output_path / filename

        with open(report_file, 'w') as f:
            f.write(report)

        logger.info(f"Report generated: {report_file}")
        return report_file

    def _generate_header(self) -> str:
        """Generate report header"""
        return f"""# Weekly OKR-Jira Analysis Report

**Period**: {self.week_start.strftime('%Y-%m-%d')} to {self.week_end.strftime('%Y-%m-%d')}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**OKR Period**: {self.metrics.okr_set.period}"""

    def _generate_summary(self, summary: Dict[str, Any]) -> str:
        """Generate executive summary"""
        return f"""## Executive Summary

- **Total Issues Analyzed**: {summary['total_issues']}
- **Aligned with OKRs**: {summary['aligned_issues']} ({summary['alignment_percentage']:.1f}%)
- **Unaligned Issues**: {summary['unaligned_issues']}
- **Total OKR Mappings**: {summary['total_mappings']} (issues can match multiple OKRs)

### Issue Breakdown

- **Created**: {summary['created_issues']} issues
- **Updated**: {summary['updated_issues']} issues
- **Completed**: {summary['completed_issues']} issues

### Most Active Objective

Objective {summary['most_active_objective']}: {self._get_objective_title(summary['most_active_objective'])}"""

    def _get_objective_title(self, obj_num: int) -> str:
        """Get objective title by number"""
        for obj in self.metrics.okr_set.objectives:
            if obj.number == obj_num:
                return obj.title
        return "Unknown"

    def _generate_okr_coverage(self, coverage: Dict[str, Any], top_issues: Dict[str, List[Dict]]) -> str:
        """Generate OKR coverage section"""
        lines = ["## OKR Coverage Analysis"]

        # Group by objective
        by_objective = {}
        for okr_id, data in coverage.items():
            obj_num = data['objective_number']
            if obj_num not in by_objective:
                by_objective[obj_num] = []
            by_objective[obj_num].append((okr_id, data))

        # Generate section for each objective
        for obj_num in sorted(by_objective.keys()):
            obj_data = by_objective[obj_num]
            obj_title = obj_data[0][1]['objective_title']

            # Calculate total for objective
            total_issues = sum(data['total_issues'] for _, data in obj_data)

            lines.append(f"\n### Objective {obj_num}: {obj_title}")
            lines.append(f"\n**Total Activity**: {total_issues} issue mappings")

            # Sort key results by number
            obj_data.sort(key=lambda x: x[1]['key_result_number'])

            for okr_id, data in obj_data:
                if data['total_issues'] > 0:  # Only show KRs with activity
                    lines.append(f"\n#### KR {obj_num}.{data['key_result_number']}: {data['key_result_text']}")
                    lines.append(f"\n- **Issues**: {data['total_issues']}")
                    lines.append(f"- **Average Confidence**: {data['avg_confidence']:.2f}")
                    lines.append(f"- **Breakdown**: {data['created']} created, {data['updated']} updated, {data['completed']} completed")

                    # Show top issues
                    if okr_id in top_issues and top_issues[okr_id]:
                        lines.append("\n**Top Issues**:")
                        for issue in top_issues[okr_id]:
                            lines.append(f"- **{issue['issue_key']}** ({issue['category']}, conf: {issue['confidence']:.2f}): {issue['summary']}")
                            if issue['reasoning']:
                                lines.append(f"  - *{issue['reasoning'][:100]}...*")

        return "\n".join(lines)

    def _generate_underprioritized(self, underprioritized: List[Dict[str, Any]]) -> str:
        """Generate underprioritized OKRs section"""
        lines = ["## Underprioritized OKRs"]

        if not underprioritized:
            lines.append("\n*All OKRs have active work assigned!*")
        else:
            lines.append(f"\n**{len(underprioritized)} OKRs** with minimal or no activity:")

            for okr in underprioritized[:10]:  # Show top 10
                lines.append(f"\n### Objective {okr['objective_number']}, KR {okr['key_result_number']}")
                lines.append(f"**{okr['key_result_text']}**")
                lines.append(f"- Issues: {okr['issue_count']}")

        return "\n".join(lines)

    def _generate_unaligned(self, unaligned: List[Any]) -> str:
        """Generate unaligned issues section"""
        lines = ["## Unaligned Work"]

        if not unaligned:
            lines.append("\n*All issues are aligned with OKRs!*")
        else:
            lines.append(f"\n**{len(unaligned)} issues** don't contribute to current OKRs:")

            # Group by reasoning
            lines.append("\n### Issues Without OKR Alignment\n")

            for unaligned_entry in unaligned[:20]:  # Show first 20
                issue = self.metrics.db.get_issue(unaligned_entry.issue_key)
                if issue:
                    lines.append(f"- **{issue.key}**: {issue.summary}")
                    lines.append(f"  - Status: {issue.status}, Type: {issue.issue_type}")
                    if unaligned_entry.reasoning:
                        lines.append(f"  - *{unaligned_entry.reasoning}*")

        return "\n".join(lines)

    def _generate_footer(self) -> str:
        """Generate report footer"""
        return f"""---

*Report generated by OKR-Jira Analysis System*
*Database: `output/data/okr_analysis.db`*"""
