"""Claude API-based semantic matching of issues to OKRs"""

import json
import logging
from typing import List, Dict, Any
from anthropic import Anthropic
from ..jira.models import JiraIssue
from ..okr.models import OKRSet

logger = logging.getLogger(__name__)


class ClaudeMatcher:
    """Match Jira issues to OKRs using Claude API"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        """
        Initialize Claude matcher

        Args:
            api_key: Anthropic API key
            model: Claude model to use
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def _format_okrs(self, okr_set: OKRSet) -> str:
        """Format OKRs for the prompt"""
        lines = []
        for obj in okr_set.objectives:
            lines.append(f"\nObjective {obj.number}: {obj.title}")
            for kr in obj.key_results:
                lines.append(f"  - KR {obj.number}.{kr.number}: {kr.text}")
        return "\n".join(lines)

    def _create_prompt(self, issue: JiraIssue, okr_set: OKRSet) -> str:
        """Create matching prompt for Claude"""
        return f"""You are analyzing project management data to map Jira issues to OKRs.

Issue Key: {issue.key}
Summary: {issue.summary}
Description: {issue.description or 'N/A'}
Issue Type: {issue.issue_type}
Status: {issue.status}

OKRs for {okr_set.period}:
{self._format_okrs(okr_set)}

Analyze this issue and identify ALL OKRs it contributes to. An issue can match multiple OKRs.

Respond in JSON format ONLY (no other text):
{{
  "matches": [
    {{"objective_id": "obj1", "key_result_id": "kr2", "confidence": 0.85, "reasoning": "Brief explanation"}},
    {{"objective_id": "obj2", "key_result_id": "kr3", "confidence": 0.65, "reasoning": "Brief explanation"}}
  ],
  "no_okr_match": false,
  "no_match_reasoning": null
}}

Confidence scale:
- 0.8-1.0: Directly implements this key result
- 0.5-0.79: Supports this key result indirectly
- 0.3-0.49: Tangentially related
- <0.3: Not a match (don't include)

If the issue doesn't match ANY OKR, set no_okr_match to true and provide reasoning."""

    def match_issue(self, issue: JiraIssue, okr_set: OKRSet) -> Dict[str, Any]:
        """
        Match a single issue to OKRs

        Args:
            issue: Jira issue to match
            okr_set: Set of OKRs

        Returns:
            Dictionary with matches and reasoning
        """
        logger.debug(f"Matching issue {issue.key}")

        prompt = self._create_prompt(issue, okr_set)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract response text
            response_text = response.content[0].text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                # Find the start and end of the JSON
                lines = response_text.split('\n')
                # Skip first line if it's ```json
                start_idx = 1 if lines[0].strip().startswith('```') else 0
                # Find the closing ```
                end_idx = len(lines)
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].strip() == '```':
                        end_idx = i
                        break
                response_text = '\n'.join(lines[start_idx:end_idx])

            # Parse JSON response
            result = json.loads(response_text)

            logger.debug(f"Issue {issue.key}: {len(result.get('matches', []))} matches, no_match={result.get('no_okr_match', False)}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response for {issue.key}: {e}")
            logger.error(f"Response was: {response_text[:200]}")
            # Return no matches on error
            return {"matches": [], "no_okr_match": True, "no_match_reasoning": "Failed to parse AI response"}

        except Exception as e:
            logger.error(f"Error matching issue {issue.key}: {e}")
            return {"matches": [], "no_okr_match": True, "no_match_reasoning": str(e)}

    def match_issues(self, issues: List[JiraIssue], okr_set: OKRSet) -> Dict[str, Dict[str, Any]]:
        """
        Match multiple issues to OKRs

        Args:
            issues: List of Jira issues
            okr_set: Set of OKRs

        Returns:
            Dictionary mapping issue keys to match results
        """
        logger.info(f"Matching {len(issues)} issues to OKRs...")

        results = {}
        for i, issue in enumerate(issues, 1):
            logger.info(f"Processing issue {i}/{len(issues)}: {issue.key}")
            results[issue.key] = self.match_issue(issue, okr_set)

        return results
