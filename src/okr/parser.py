"""OKR markdown file parser"""

import re
import logging
from pathlib import Path
from typing import Optional
from .models import Objective, KeyResult, OKRSet

logger = logging.getLogger(__name__)


class OKRParser:
    """Parse OKR markdown files"""

    def __init__(self, okr_directory: Path):
        """
        Initialize parser

        Args:
            okr_directory: Directory containing OKR markdown files
        """
        self.okr_directory = okr_directory

    def find_latest_okr_file(self, default_file: Optional[str] = None) -> Path:
        """
        Find the most recent OKR file

        Args:
            default_file: Fallback filename if auto-detection fails

        Returns:
            Path to OKR file
        """
        # Get all .md files in OKR directory
        md_files = list(self.okr_directory.glob("*.md"))

        if not md_files:
            if default_file:
                fallback = self.okr_directory / default_file
                if fallback.exists():
                    logger.info(f"Using default OKR file: {default_file}")
                    return fallback
            raise FileNotFoundError(f"No OKR files found in {self.okr_directory}")

        # Sort by modification time (most recent first)
        md_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        selected = md_files[0]
        logger.info(f"Auto-detected latest OKR file: {selected.name}")
        return selected

    def parse_file(self, file_path: Path) -> OKRSet:
        """
        Parse an OKR markdown file

        Args:
            file_path: Path to markdown file

        Returns:
            OKRSet with parsed objectives and key results
        """
        logger.info(f"Parsing OKR file: {file_path}")

        with open(file_path, 'r') as f:
            content = f.read()

        # Extract period from filename (e.g., "may_2026" from "may_2026.md")
        period = file_path.stem

        objectives = []
        current_objective = None
        current_kr_list = []

        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Match "## Objective N: Title"
            obj_match = re.match(r'^##\s+Objective\s+(\d+):\s+(.+)$', line)
            if obj_match:
                # Save previous objective if exists
                if current_objective:
                    current_objective.key_results = current_kr_list
                    objectives.append(current_objective)

                obj_num = int(obj_match.group(1))
                obj_title = obj_match.group(2)
                current_objective = Objective(number=obj_num, title=obj_title, key_results=[])
                current_kr_list = []
                logger.debug(f"Found objective {obj_num}: {obj_title}")
                i += 1
                continue

            # Match "### Key Results" section header
            if re.match(r'^###\s+Key Results?', line):
                i += 1
                continue

            # Match bullet points "- Key result text"
            if line.startswith('-') and current_objective:
                kr_text = line[1:].strip()
                # Number key results sequentially
                kr_num = len(current_kr_list) + 1
                current_kr_list.append(KeyResult(number=kr_num, text=kr_text))
                logger.debug(f"  Found KR {kr_num}: {kr_text[:50]}...")

            i += 1

        # Save last objective
        if current_objective:
            current_objective.key_results = current_kr_list
            objectives.append(current_objective)

        logger.info(f"Parsed {len(objectives)} objectives")
        return OKRSet(period=period, objectives=objectives)

    def load_okrs(self, auto_detect: bool = True, default_file: Optional[str] = None) -> OKRSet:
        """
        Load OKRs from file

        Args:
            auto_detect: If True, auto-detect latest file
            default_file: Default filename to use

        Returns:
            Parsed OKRSet
        """
        if auto_detect:
            file_path = self.find_latest_okr_file(default_file)
        else:
            if not default_file:
                raise ValueError("default_file must be provided when auto_detect is False")
            file_path = self.okr_directory / default_file

        return self.parse_file(file_path)
