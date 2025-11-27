"""Metrics calculation for OKR analysis"""

import logging
from datetime import date
from typing import Dict, List, Any
from collections import defaultdict
from ..database.db import Database
from ..okr.models import OKRSet

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate analytics and metrics for OKR analysis"""

    def __init__(self, db: Database, okr_set: OKRSet, week_start: date):
        """
        Initialize metrics calculator

        Args:
            db: Database instance
            okr_set: OKR set
            week_start: Start date of analysis period
        """
        self.db = db
        self.okr_set = okr_set
        self.week_start = week_start

    def calculate_okr_coverage(self) -> Dict[str, Any]:
        """
        Calculate coverage metrics for each OKR

        Returns:
            Dictionary mapping OKR IDs to coverage data
        """
        coverage = {}

        for obj in self.okr_set.objectives:
            for kr in obj.key_results:
                okr_id = obj.get_key_result_id(kr.number)

                # Get mappings for this OKR
                mappings = self.db.get_mappings_for_okr(okr_id, self.week_start)

                # Group by category
                by_category = defaultdict(list)
                for mapping in mappings:
                    by_category[mapping.category].append(mapping)

                coverage[okr_id] = {
                    'objective_number': obj.number,
                    'objective_title': obj.title,
                    'key_result_number': kr.number,
                    'key_result_text': kr.text,
                    'total_issues': len(mappings),
                    'created': len(by_category['created']),
                    'updated': len(by_category['updated']),
                    'completed': len(by_category['completed']),
                    'avg_confidence': sum(m.confidence for m in mappings) / len(mappings) if mappings else 0,
                    'mappings': mappings
                }

        return coverage

    def identify_underprioritized_okrs(self, coverage: Dict[str, Any], threshold: int = 2) -> List[Dict[str, Any]]:
        """
        Identify OKRs with low or zero activity

        Args:
            coverage: OKR coverage data
            threshold: Minimum issue count to not be considered underprioritized

        Returns:
            List of underprioritized OKRs
        """
        underprioritized = []

        for okr_id, data in coverage.items():
            if data['total_issues'] < threshold:
                underprioritized.append({
                    'okr_id': okr_id,
                    'objective_number': data['objective_number'],
                    'objective_title': data['objective_title'],
                    'key_result_number': data['key_result_number'],
                    'key_result_text': data['key_result_text'],
                    'issue_count': data['total_issues']
                })

        # Sort by issue count (lowest first)
        underprioritized.sort(key=lambda x: x['issue_count'])

        return underprioritized

    def get_unaligned_issues(self) -> List[Any]:
        """Get issues that don't match any OKR"""
        return self.db.get_unaligned_issues_for_week(self.week_start)

    def calculate_summary_stats(self, coverage: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate summary statistics

        Args:
            coverage: OKR coverage data

        Returns:
            Summary statistics
        """
        # Get total unique issues from database
        all_mappings = self.db.get_mappings_for_week(self.week_start)
        unique_issues = len(set(m.issue_key for m in all_mappings))

        unaligned = self.get_unaligned_issues()

        total_issues = unique_issues + len(unaligned)

        # Count by category
        created_issues = len(set(m.issue_key for m in all_mappings if m.category == 'created'))
        updated_issues = len(set(m.issue_key for m in all_mappings if m.category == 'updated'))
        completed_issues = len(set(m.issue_key for m in all_mappings if m.category == 'completed'))

        # Find most active objective
        obj_counts = defaultdict(int)
        for okr_id, data in coverage.items():
            obj_counts[data['objective_number']] += data['total_issues']

        most_active_obj = max(obj_counts.items(), key=lambda x: x[1])[0] if obj_counts else None

        return {
            'total_issues': total_issues,
            'aligned_issues': unique_issues,
            'unaligned_issues': len(unaligned),
            'alignment_percentage': (unique_issues / total_issues * 100) if total_issues > 0 else 0,
            'created_issues': created_issues,
            'updated_issues': updated_issues,
            'completed_issues': completed_issues,
            'total_mappings': len(all_mappings),
            'most_active_objective': most_active_obj
        }

    def get_top_issues_by_okr(self, coverage: Dict[str, Any], limit: int = 5) -> Dict[str, List[Dict]]:
        """
        Get top issues for each OKR

        Args:
            coverage: OKR coverage data
            limit: Max issues per OKR

        Returns:
            Dictionary mapping OKR IDs to lists of top issues
        """
        top_issues = {}

        for okr_id, data in coverage.items():
            if data['mappings']:
                # Sort by confidence descending
                sorted_mappings = sorted(data['mappings'], key=lambda m: m.confidence, reverse=True)

                # Get top N unique issues
                seen_issues = set()
                top = []
                for mapping in sorted_mappings:
                    if mapping.issue_key not in seen_issues:
                        issue = self.db.get_issue(mapping.issue_key)
                        if issue:
                            top.append({
                                'issue_key': mapping.issue_key,
                                'summary': issue.summary,
                                'confidence': mapping.confidence,
                                'category': mapping.category,
                                'reasoning': mapping.reasoning
                            })
                            seen_issues.add(mapping.issue_key)
                            if len(top) >= limit:
                                break

                top_issues[okr_id] = top

        return top_issues
