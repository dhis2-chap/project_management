"""Configuration management for OKR-Jira analysis system"""

import os
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv


class Config:
    """Configuration loader and manager"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration

        Args:
            config_path: Path to config.yaml file. If None, uses default location.
        """
        # Determine project root and config path
        self.project_root = Path(__file__).parent.parent

        # Load environment variables from config/.env
        env_path = self.project_root / "config" / ".env"
        load_dotenv(dotenv_path=env_path)
        if config_path is None:
            config_path = self.project_root / "config" / "config.yaml"
        else:
            config_path = Path(config_path)

        # Load YAML configuration
        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)

    # Jira configuration
    @property
    def jira_project_key(self) -> str:
        return self._config['jira']['project_key']

    @property
    def jira_analysis_days(self) -> int:
        return self._config['jira']['analysis_days']

    # OKR configuration
    @property
    def okr_directory(self) -> Path:
        return self.project_root / self._config['okr']['directory']

    @property
    def okr_auto_detect_latest(self) -> bool:
        return self._config['okr']['auto_detect_latest']

    @property
    def okr_default_file(self) -> str:
        return self._config['okr']['default_file']

    # Matching configuration
    @property
    def claude_model(self) -> str:
        return self._config['matching']['claude_model']

    @property
    def confidence_threshold(self) -> float:
        return self._config['matching']['confidence_threshold']

    @property
    def individual_analysis(self) -> bool:
        return self._config['matching']['individual_analysis']

    @property
    def allow_multiple_matches(self) -> bool:
        return self._config['matching']['allow_multiple_matches']

    # Database configuration
    @property
    def database_path(self) -> Path:
        return self.project_root / self._config['database']['path']

    # Reporting configuration
    @property
    def report_output_dir(self) -> Path:
        return self.project_root / self._config['reporting']['output_dir']

    @property
    def trend_weeks(self) -> int:
        return self._config['reporting']['trend_weeks']

    # Notifications configuration
    @property
    def slack_enabled(self) -> bool:
        return self._config['notifications']['slack']['enabled']

    @property
    def slack_detail_level(self) -> str:
        return self._config['notifications']['slack']['detail_level']

    @property
    def slack_max_unaligned_issues(self) -> int:
        return self._config['notifications']['slack']['max_unaligned_issues']

    @property
    def slack_max_underprioritized_okrs(self) -> int:
        return self._config['notifications']['slack']['max_underprioritized_okrs']

    # Environment variables
    @property
    def anthropic_api_key(self) -> str:
        key = os.getenv('ANTHROPIC_API_KEY')
        if not key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        return key

    @property
    def slack_webhook_url(self) -> Optional[str]:
        return os.getenv('SLACK_WEBHOOK_URL')

    def validate(self):
        """Validate configuration"""
        errors = []

        # Check required directories exist
        if not self.okr_directory.exists():
            errors.append(f"OKR directory not found: {self.okr_directory}")

        # Check environment variables
        try:
            _ = self.anthropic_api_key
        except ValueError as e:
            errors.append(str(e))

        if self.slack_enabled and not self.slack_webhook_url:
            errors.append("Slack is enabled but SLACK_WEBHOOK_URL is not set")

        # Check confidence threshold is valid
        if not 0 <= self.confidence_threshold <= 1:
            errors.append(f"confidence_threshold must be between 0 and 1, got {self.confidence_threshold}")

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

        return True


# Global config instance (will be initialized in main.py)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config):
    """Set the global configuration instance"""
    global _config
    _config = config
