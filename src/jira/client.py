"""Jira client for fetching issues via acli"""

import json
import logging
import subprocess
from typing import List
from .models import JiraIssue

logger = logging.getLogger(__name__)


class JiraClient:
    """Client for fetching Jira issues using acli"""

    def __init__(self, project_key: str, analysis_days: int = 7):
        """
        Initialize Jira client

        Args:
            project_key: Jira project key (e.g., "CLIM")
            analysis_days: Number of days to look back
        """
        self.project_key = project_key
        self.analysis_days = analysis_days

    def _run_acli_query(self, jql: str) -> List[dict]:
        """
        Run acli JQL query and return results

        Args:
            jql: JQL query string

        Returns:
            List of issue dictionaries
        """
        logger.debug(f"Running JQL: {jql}")

        try:
            # Run acli command
            result = subprocess.run(
                ['acli', 'jira', 'workitem', 'search', '--jql', jql, '--json'],
                capture_output=True,
                text=True,
                check=True
            )

            # Parse JSON output
            # acli returns a JSON array of issues
            try:
                data = json.loads(result.stdout)
                # Handle both array and single object responses
                if isinstance(data, list):
                    issues = data
                else:
                    issues = [data]
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse acli JSON output: {e}")
                logger.debug(f"Output was: {result.stdout[:500]}")
                return []

            logger.info(f"Fetched {len(issues)} issues")
            return issues

        except subprocess.CalledProcessError as e:
            logger.error(f"acli command failed: {e.stderr}")
            raise
        except FileNotFoundError:
            logger.error("acli command not found. Is Atlassian CLI installed?")
            raise

    def _parse_issue(self, issue_data: dict, category: str) -> JiraIssue:
        """
        Parse issue data from acli JSON response

        Args:
            issue_data: Issue dictionary from acli
            category: Issue category ('created', 'updated', 'completed')

        Returns:
            JiraIssue object
        """
        # Extract fields (acli JSON structure may vary)
        key = issue_data.get('key', '')
        fields = issue_data.get('fields', {})

        summary = fields.get('summary', '')
        description = fields.get('description', '')
        issue_type = fields.get('issuetype', {}).get('name', '')
        status = fields.get('status', {}).get('name', '')

        assignee_data = fields.get('assignee')
        assignee = assignee_data.get('displayName', '') if assignee_data else None

        return JiraIssue(
            key=key,
            summary=summary,
            description=description,
            issue_type=issue_type,
            status=status,
            assignee=assignee,
            category=category
        )

    def fetch_created_issues(self) -> List[JiraIssue]:
        """Fetch issues created in the last N days"""
        jql = f'project = {self.project_key} AND created >= -{self.analysis_days}d'
        issues_data = self._run_acli_query(jql)
        return [self._parse_issue(issue, 'created') for issue in issues_data]

    def fetch_updated_issues(self) -> List[JiraIssue]:
        """Fetch issues updated in the last N days (excluding just-created)"""
        jql = f'project = {self.project_key} AND updated >= -{self.analysis_days}d AND created < -{self.analysis_days}d'
        issues_data = self._run_acli_query(jql)
        return [self._parse_issue(issue, 'updated') for issue in issues_data]

    def fetch_completed_issues(self) -> List[JiraIssue]:
        """Fetch issues completed in the last N days"""
        jql = f'project = {self.project_key} AND status changed to Done during (-{self.analysis_days}d, now())'
        issues_data = self._run_acli_query(jql)
        return [self._parse_issue(issue, 'completed') for issue in issues_data]

    def fetch_all_issues(self) -> List[JiraIssue]:
        """Fetch all three categories of issues"""
        logger.info("Fetching all issue categories...")

        created = self.fetch_created_issues()
        updated = self.fetch_updated_issues()
        completed = self.fetch_completed_issues()

        all_issues = created + updated + completed
        logger.info(f"Total issues: {len(all_issues)} (created: {len(created)}, updated: {len(updated)}, completed: {len(completed)})")

        return all_issues
