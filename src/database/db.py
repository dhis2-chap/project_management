"""Database operations for OKR-Jira analysis system"""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Index
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, OKR, Issue, WeeklySnapshot, IssueOKRMapping, UnalignedIssue

logger = logging.getLogger(__name__)


class Database:
    """Database operations manager"""

    def __init__(self, db_path: Path):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        # Create parent directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine and session
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.Session = sessionmaker(bind=self.engine)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

        # Create indexes for performance
        self._create_indexes()

        logger.info(f"Database initialized at {db_path}")

    def _create_indexes(self):
        """Create database indexes for performance"""
        Index('idx_mappings_week', IssueOKRMapping.week_start)
        Index('idx_mappings_issue', IssueOKRMapping.issue_key)
        Index('idx_mappings_okr', IssueOKRMapping.okr_id)
        Index('idx_unaligned_week', UnalignedIssue.week_start)

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.Session()

    # OKR operations
    def store_okr(self, okr_id: str, objective_number: int, objective_title: str,
                  key_result_number: Optional[int], key_result_text: Optional[str],
                  okr_period: str) -> OKR:
        """Store or update an OKR"""
        with self.get_session() as session:
            okr = session.query(OKR).filter_by(id=okr_id).first()
            if okr:
                # Update existing
                okr.objective_number = objective_number
                okr.objective_title = objective_title
                okr.key_result_number = key_result_number
                okr.key_result_text = key_result_text
                okr.okr_period = okr_period
            else:
                # Create new
                okr = OKR(
                    id=okr_id,
                    objective_number=objective_number,
                    objective_title=objective_title,
                    key_result_number=key_result_number,
                    key_result_text=key_result_text,
                    okr_period=okr_period
                )
                session.add(okr)
            session.commit()
            session.refresh(okr)
            return okr

    def get_okrs_by_period(self, okr_period: str) -> List[OKR]:
        """Get all OKRs for a specific period"""
        with self.get_session() as session:
            return session.query(OKR).filter_by(okr_period=okr_period).all()

    # Issue operations
    def store_issue(self, key: str, summary: str, description: Optional[str],
                    issue_type: Optional[str], status: Optional[str],
                    assignee: Optional[str]) -> Issue:
        """Store or update an issue"""
        with self.get_session() as session:
            issue = session.query(Issue).filter_by(key=key).first()
            if issue:
                # Update existing
                issue.summary = summary
                issue.description = description
                issue.issue_type = issue_type
                issue.status = status
                issue.assignee = assignee
                issue.last_seen = datetime.utcnow()
            else:
                # Create new
                issue = Issue(
                    key=key,
                    summary=summary,
                    description=description,
                    issue_type=issue_type,
                    status=status,
                    assignee=assignee
                )
                session.add(issue)
            session.commit()
            session.refresh(issue)
            return issue

    def get_issue(self, key: str) -> Optional[Issue]:
        """Get an issue by key"""
        with self.get_session() as session:
            return session.query(Issue).filter_by(key=key).first()

    # Issue-OKR mapping operations
    def store_mapping(self, issue_key: str, okr_id: str, confidence: float,
                      reasoning: str, category: str, week_start: date) -> IssueOKRMapping:
        """Store an issue-OKR mapping"""
        with self.get_session() as session:
            # Check if mapping already exists for this week
            existing = session.query(IssueOKRMapping).filter_by(
                issue_key=issue_key,
                okr_id=okr_id,
                week_start=week_start
            ).first()

            if existing:
                # Update existing mapping
                existing.confidence = confidence
                existing.reasoning = reasoning
                existing.category = category
                existing.analyzed_at = datetime.utcnow()
                mapping = existing
            else:
                # Create new mapping
                mapping = IssueOKRMapping(
                    issue_key=issue_key,
                    okr_id=okr_id,
                    confidence=confidence,
                    reasoning=reasoning,
                    category=category,
                    week_start=week_start
                )
                session.add(mapping)

            session.commit()
            session.refresh(mapping)
            return mapping

    def get_mappings_for_week(self, week_start: date) -> List[IssueOKRMapping]:
        """Get all mappings for a specific week"""
        with self.get_session() as session:
            return session.query(IssueOKRMapping).filter_by(week_start=week_start).all()

    def get_mappings_for_okr(self, okr_id: str, week_start: date) -> List[IssueOKRMapping]:
        """Get all mappings for a specific OKR in a week"""
        with self.get_session() as session:
            return session.query(IssueOKRMapping).filter_by(
                okr_id=okr_id,
                week_start=week_start
            ).all()

    # Unaligned issue operations
    def store_unaligned_issue(self, issue_key: str, week_start: date,
                               reasoning: str) -> UnalignedIssue:
        """Store an unaligned issue"""
        with self.get_session() as session:
            # Check if already exists for this week
            existing = session.query(UnalignedIssue).filter_by(
                issue_key=issue_key,
                week_start=week_start
            ).first()

            if existing:
                existing.reasoning = reasoning
                existing.analyzed_at = datetime.utcnow()
                unaligned = existing
            else:
                unaligned = UnalignedIssue(
                    issue_key=issue_key,
                    week_start=week_start,
                    reasoning=reasoning
                )
                session.add(unaligned)

            session.commit()
            session.refresh(unaligned)
            return unaligned

    def get_unaligned_issues_for_week(self, week_start: date) -> List[UnalignedIssue]:
        """Get all unaligned issues for a specific week"""
        with self.get_session() as session:
            return session.query(UnalignedIssue).filter_by(week_start=week_start).all()

    # Weekly snapshot operations
    def store_weekly_snapshot(self, week_start: date, week_end: date,
                               total_issues: int, aligned_issues: int,
                               unaligned_issues: int, okr_period: str) -> WeeklySnapshot:
        """Store a weekly analysis snapshot"""
        with self.get_session() as session:
            snapshot = WeeklySnapshot(
                week_start=week_start,
                week_end=week_end,
                total_issues=total_issues,
                aligned_issues=aligned_issues,
                unaligned_issues=unaligned_issues,
                okr_period=okr_period
            )
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)
            return snapshot

    def get_weekly_snapshots(self, limit: int = 4) -> List[WeeklySnapshot]:
        """Get recent weekly snapshots"""
        with self.get_session() as session:
            return session.query(WeeklySnapshot).order_by(
                WeeklySnapshot.week_start.desc()
            ).limit(limit).all()

    def get_okr_coverage_trends(self, okr_id: str, weeks: int = 4) -> List[Dict[str, Any]]:
        """Get trend data for a specific OKR over multiple weeks"""
        with self.get_session() as session:
            # Get recent snapshots to determine week range
            snapshots = session.query(WeeklySnapshot).order_by(
                WeeklySnapshot.week_start.desc()
            ).limit(weeks).all()

            if not snapshots:
                return []

            week_starts = [s.week_start for s in snapshots]

            # Get mapping counts for each week
            trends = []
            for week_start in reversed(week_starts):
                count = session.query(IssueOKRMapping).filter_by(
                    okr_id=okr_id,
                    week_start=week_start
                ).count()
                trends.append({
                    'week_start': week_start,
                    'issue_count': count
                })

            return trends
