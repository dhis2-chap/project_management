"""OKR data models"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class KeyResult:
    """A single key result"""
    number: int
    text: str


@dataclass
class Objective:
    """An objective with its key results"""
    number: int
    title: str
    key_results: List[KeyResult]

    def get_id(self) -> str:
        """Get objective ID"""
        return f"obj{self.number}"

    def get_key_result_id(self, kr_number: int) -> str:
        """Get key result ID"""
        return f"obj{self.number}_kr{kr_number}"


@dataclass
class OKRSet:
    """A set of objectives for a period"""
    period: str  # e.g., "may_2026"
    objectives: List[Objective]

    def get_all_key_results(self) -> List[tuple]:
        """Get all (objective, key_result) pairs"""
        results = []
        for obj in self.objectives:
            for kr in obj.key_results:
                results.append((obj, kr))
        return results
