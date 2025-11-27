"""Database models for OKR-Jira analysis system"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Date, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class OKR(Base):
    """OKR (Objective and Key Result) table"""
    __tablename__ = 'okrs'

    id = Column(String, primary_key=True)  # e.g., "obj1_kr2"
    objective_number = Column(Integer, nullable=False)
    objective_title = Column(Text, nullable=False)
    key_result_number = Column(Integer)  # NULL for objective-level entries
    key_result_text = Column(Text)
    okr_period = Column(String, nullable=False)  # e.g., "may_2026"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    mappings = relationship("IssueOKRMapping", back_populates="okr")


class Issue(Base):
    """Jira issue table"""
    __tablename__ = 'issues'

    key = Column(String, primary_key=True)  # e.g., "CLIM-123"
    summary = Column(Text, nullable=False)
    description = Column(Text)
    issue_type = Column(String)  # Task, Bug, Story, etc.
    status = Column(String)
    assignee = Column(String)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    mappings = relationship("IssueOKRMapping", back_populates="issue")
    unaligned_entries = relationship("UnalignedIssue", back_populates="issue")


class WeeklySnapshot(Base):
    """Weekly analysis snapshot table"""
    __tablename__ = 'weekly_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    total_issues = Column(Integer, nullable=False)
    aligned_issues = Column(Integer, nullable=False)
    unaligned_issues = Column(Integer, nullable=False)
    okr_period = Column(String, nullable=False)


class IssueOKRMapping(Base):
    """Many-to-many mapping between issues and OKRs with confidence scores"""
    __tablename__ = 'issue_okr_mappings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_key = Column(String, ForeignKey('issues.key'), nullable=False)
    okr_id = Column(String, ForeignKey('okrs.id'), nullable=False)
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text)
    category = Column(String, nullable=False)  # 'created', 'updated', 'completed'
    week_start = Column(Date, nullable=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    issue = relationship("Issue", back_populates="mappings")
    okr = relationship("OKR", back_populates="mappings")


class UnalignedIssue(Base):
    """Issues that don't match any OKR"""
    __tablename__ = 'unaligned_issues'

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_key = Column(String, ForeignKey('issues.key'), nullable=False)
    week_start = Column(Date, nullable=False)
    reasoning = Column(Text)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    issue = relationship("Issue", back_populates="unaligned_entries")
