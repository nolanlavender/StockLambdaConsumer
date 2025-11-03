"""Tests for configuration management."""
import os
import pytest

from src.config import Config, get_config


def test_config_defaults():
    """Test default configuration values."""
    config = Config()

    assert config.kinesis_stream_name == 'stock-prices-stream'
    assert config.dynamodb_table_name == 'stock-analytics'
    assert config.enforce_market_hours is True
    assert config.test_mode is False
    assert config.data_retention_days == 7


def test_config_from_env(monkeypatch):
    """Test configuration from environment variables."""
    monkeypatch.setenv('KINESIS_STREAM_NAME', 'test-stream')
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'test-table')
    monkeypatch.setenv('ENFORCE_MARKET_HOURS', 'false')
    monkeypatch.setenv('TEST_MODE', 'true')
    monkeypatch.setenv('DATA_RETENTION_DAYS', '14')

    config = Config()

    assert config.kinesis_stream_name == 'test-stream'
    assert config.dynamodb_table_name == 'test-table'
    assert config.enforce_market_hours is False
    assert config.test_mode is True
    assert config.data_retention_days == 14


def test_config_time_windows():
    """Test time window configuration."""
    config = Config()

    assert config.time_windows_minutes == [1, 5, 15, 30, 60, 120]
    assert config.moving_average_windows_minutes == [5, 15, 30, 60]


def test_config_from_env_time_windows(monkeypatch):
    """Test time windows from environment variables."""
    monkeypatch.setenv('TIME_WINDOWS_MINUTES', '1,5,10')
    monkeypatch.setenv('MOVING_AVERAGE_WINDOWS_MINUTES', '5,10')

    config = Config()

    assert config.time_windows_minutes == [1, 5, 10]
    assert config.moving_average_windows_minutes == [5, 10]


def test_config_get_nested():
    """Test getting nested configuration values."""
    config = Config()

    volatility = config.get('analytics.volatility_threshold')
    assert volatility == 0.02

    momentum = config.get('analytics.momentum_threshold')
    assert momentum == 0.015


def test_config_get_with_default():
    """Test getting configuration with default value."""
    config = Config()

    value = config.get('nonexistent.key', 'default_value')
    assert value == 'default_value'


def test_get_config_singleton():
    """Test global config singleton."""
    config1 = get_config()
    config2 = get_config()

    assert config1 is config2


def test_config_batch_settings():
    """Test batch configuration settings."""
    config = Config()

    assert config.batch_write_interval_minutes == 15
    assert config.batch_max_size == 500


def test_config_batch_from_env(monkeypatch):
    """Test batch configuration from environment variables."""
    monkeypatch.setenv('BATCH_WRITE_INTERVAL_MINUTES', '10')
    monkeypatch.setenv('BATCH_MAX_SIZE', '300')

    config = Config()

    assert config.batch_write_interval_minutes == 10
    assert config.batch_max_size == 300
