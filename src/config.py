"""Configuration management for Stock Lambda Consumer."""
import json
import os
from typing import Any, Dict, List, Optional


class Config:
    """Configuration manager for the application."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_file: Optional path to JSON configuration file
        """
        self._config: Dict[str, Any] = {}

        # Load from file if provided
        if config_file and os.path.exists(config_file):
            self._load_from_file(config_file)

        # Override with environment variables
        self._load_from_env()

    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from JSON file."""
        try:
            with open(config_file, 'r') as f:
                self._config = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load config file {config_file}: {e}")
            self._config = {}

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # AWS Configuration
        if os.getenv('AWS_REGION'):
            self._config['aws_region'] = os.getenv('AWS_REGION')

        if os.getenv('KINESIS_STREAM_NAME'):
            self._config['kinesis_stream_name'] = os.getenv('KINESIS_STREAM_NAME')

        if os.getenv('DYNAMODB_TABLE_NAME'):
            self._config['dynamodb_table_name'] = os.getenv('DYNAMODB_TABLE_NAME')

        # Application Configuration
        if os.getenv('ENFORCE_MARKET_HOURS'):
            self._config['enforce_market_hours'] = os.getenv('ENFORCE_MARKET_HOURS', 'true').lower() == 'true'

        if os.getenv('TEST_MODE'):
            self._config['test_mode'] = os.getenv('TEST_MODE', 'false').lower() == 'true'

        if os.getenv('DATA_RETENTION_DAYS'):
            self._config['data_retention_days'] = int(os.getenv('DATA_RETENTION_DAYS', '7'))

        # Analytics Configuration
        if os.getenv('TIME_WINDOWS_MINUTES'):
            time_windows = os.getenv('TIME_WINDOWS_MINUTES', '1,5,15,30,60,120')
            if 'analytics' not in self._config:
                self._config['analytics'] = {}
            self._config['analytics']['time_windows_minutes'] = [
                int(x.strip()) for x in time_windows.split(',')
            ]

        if os.getenv('MOVING_AVERAGE_WINDOWS_MINUTES'):
            ma_windows = os.getenv('MOVING_AVERAGE_WINDOWS_MINUTES', '5,15,30,60')
            if 'analytics' not in self._config:
                self._config['analytics'] = {}
            self._config['analytics']['moving_average_windows_minutes'] = [
                int(x.strip()) for x in ma_windows.split(',')
            ]

        # Shutdown Configuration
        if os.getenv('NO_DATA_TIMEOUT_MINUTES'):
            if 'shutdown' not in self._config:
                self._config['shutdown'] = {}
            self._config['shutdown']['no_data_timeout_minutes'] = int(
                os.getenv('NO_DATA_TIMEOUT_MINUTES', '10')
            )

        if os.getenv('CHECK_INTERVAL_MINUTES'):
            if 'shutdown' not in self._config:
                self._config['shutdown'] = {}
            self._config['shutdown']['check_interval_minutes'] = int(
                os.getenv('CHECK_INTERVAL_MINUTES', '5')
            )

        # Batch Write Configuration
        if os.getenv('BATCH_WRITE_INTERVAL_MINUTES'):
            if 'batch' not in self._config:
                self._config['batch'] = {}
            self._config['batch']['write_interval_minutes'] = int(
                os.getenv('BATCH_WRITE_INTERVAL_MINUTES', '15')
            )

        if os.getenv('BATCH_MAX_SIZE'):
            if 'batch' not in self._config:
                self._config['batch'] = {}
            self._config['batch']['max_size'] = int(
                os.getenv('BATCH_MAX_SIZE', '500')
            )

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @property
    def kinesis_stream_name(self) -> str:
        """Get Kinesis stream name."""
        return self.get('kinesis_stream_name', 'stock-prices-stream')

    @property
    def dynamodb_table_name(self) -> str:
        """Get DynamoDB table name."""
        return self.get('dynamodb_table_name', 'stock-analytics')

    @property
    def aws_region(self) -> str:
        """Get AWS region."""
        return self.get('aws_region', os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))

    @property
    def enforce_market_hours(self) -> bool:
        """Whether to enforce market hours."""
        return self.get('enforce_market_hours', True)

    @property
    def test_mode(self) -> bool:
        """Whether test mode is enabled."""
        return self.get('test_mode', False)

    @property
    def data_retention_days(self) -> int:
        """Get data retention period in days."""
        return self.get('data_retention_days', 7)

    @property
    def time_windows_minutes(self) -> List[int]:
        """Get time windows for analytics in minutes."""
        return self.get('analytics.time_windows_minutes', [1, 5, 15, 30, 60, 120])

    @property
    def moving_average_windows_minutes(self) -> List[int]:
        """Get moving average windows in minutes."""
        return self.get('analytics.moving_average_windows_minutes', [5, 15, 30, 60])

    @property
    def volatility_threshold(self) -> float:
        """Get volatility threshold for trading signals."""
        return self.get('analytics.volatility_threshold', 0.02)

    @property
    def momentum_threshold(self) -> float:
        """Get momentum threshold for trading signals."""
        return self.get('analytics.momentum_threshold', 0.015)

    @property
    def no_data_timeout_minutes(self) -> int:
        """Get no-data timeout in minutes."""
        return self.get('shutdown.no_data_timeout_minutes', 10)

    @property
    def check_interval_minutes(self) -> int:
        """Get check interval in minutes."""
        return self.get('shutdown.check_interval_minutes', 5)

    @property
    def batch_write_interval_minutes(self) -> int:
        """Get batch write interval in minutes."""
        return self.get('batch.write_interval_minutes', 15)

    @property
    def batch_max_size(self) -> int:
        """Get maximum batch size before forced flush."""
        return self.get('batch.max_size', 500)

    def __repr__(self) -> str:
        """String representation of config (with sensitive data hidden)."""
        safe_config = self._config.copy()
        return f"Config({safe_config})"


# Global config instance
_config: Optional[Config] = None


def get_config(config_file: Optional[str] = None) -> Config:
    """
    Get global config instance (singleton pattern).

    Args:
        config_file: Optional path to JSON configuration file

    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_file)
    return _config
