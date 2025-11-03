"""Tests for historical data loader."""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.historical_data import HistoricalDataLoader


@pytest.mark.unit
def test_convert_decimals(mock_dynamodb_table):
    """Test Decimal to float conversion."""
    loader = HistoricalDataLoader('test-stock-analytics')

    test_data = {
        'price': Decimal('123.45'),
        'nested': {
            'value': Decimal('67.89')
        },
        'list': [Decimal('1.1'), Decimal('2.2')]
    }

    result = loader._convert_decimals(test_data)

    assert isinstance(result['price'], float)
    assert isinstance(result['nested']['value'], float)
    assert all(isinstance(x, float) for x in result['list'])


@pytest.mark.unit
def test_calculate_daily_summary(mock_dynamodb_table):
    """Test daily summary calculation."""
    loader = HistoricalDataLoader('test-stock-analytics')

    items = [
        {
            'symbol': 'AAPL',
            'timestamp': '2025-11-03T09:30:00.000000',
            'price': Decimal('270.0'),
            'open': Decimal('270.0'),
            'previous_close': Decimal('269.5')
        },
        {
            'symbol': 'AAPL',
            'timestamp': '2025-11-03T12:00:00.000000',
            'price': Decimal('271.5')
        },
        {
            'symbol': 'AAPL',
            'timestamp': '2025-11-03T16:00:00.000000',
            'price': Decimal('270.37')
        }
    ]

    summary = loader._calculate_daily_summary(items, 'AAPL', '2025-11-03')

    assert summary['symbol'] == 'AAPL'
    assert summary['date'] == '2025-11-03'
    assert summary['open'] == 270.0
    assert summary['close'] == 270.37
    assert summary['high'] == 271.5
    assert summary['low'] == 270.0
    assert summary['volume_count'] == 3


@pytest.mark.unit
def test_get_time_window_data_empty(mock_dynamodb_table):
    """Test getting time window data when no data exists."""
    loader = HistoricalDataLoader('test-stock-analytics')

    data = loader.get_time_window_data('AAPL', 5)

    assert data == []


@pytest.mark.unit
def test_clear_cache(mock_dynamodb_table):
    """Test cache clearing."""
    loader = HistoricalDataLoader('test-stock-analytics')

    # Add something to cache
    loader._cache['test'] = {'data': 'value'}
    assert len(loader._cache) > 0

    loader.clear_cache()
    assert len(loader._cache) == 0
