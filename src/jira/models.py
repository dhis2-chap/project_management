"""Jira issue data models"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class JiraIssue:
    """A Jira issue"""
    key: str
    summary: str
    description: Optional[str]
    issue_type: Optional[str]
    status: Optional[str]
    assignee: Optional[str]
    category: str  # 'created', 'updated', or 'completed'
