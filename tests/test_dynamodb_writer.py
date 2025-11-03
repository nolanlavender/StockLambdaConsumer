"""Tests for DynamoDB writer."""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from src.dynamodb_writer import DynamoDBWriter


@pytest.mark.unit
def test_convert_floats_to_decimal(mock_dynamodb_table):
    """Test float to Decimal conversion."""
    writer = DynamoDBWriter('test-stock-analytics')

    test_data = {
        'price': 123.45,
        'nested': {
            'value': 67.89
        },
        'list': [1.1, 2.2, 3.3]
    }

    result = writer._convert_floats_to_decimal(test_data)

    assert isinstance(result['price'], Decimal)
    assert isinstance(result['nested']['value'], Decimal)
    assert all(isinstance(x, Decimal) for x in result['list'])


@pytest.mark.unit
def test_write_analytics(mock_dynamodb_table):
    """Test writing analytics to DynamoDB."""
    writer = DynamoDBWriter('test-stock-analytics', retention_days=7)

    analytics = {
        'symbol': 'AAPL',
        'timestamp': '2025-11-03T17:19:39.193597',
        'date': '2025-11-03',
        'current_price': 268.04,
        'trading_signal': 'HOLD'
    }

    result = writer.write_analytics(analytics)
    assert result is True

    # Verify item was written
    table = mock_dynamodb_table
    response = table.get_item(
        Key={
            'symbol': 'AAPL',
            'timestamp': '2025-11-03T17:19:39.193597'
        }
    )

    assert 'Item' in response
    item = response['Item']
    assert item['symbol'] == 'AAPL'
    assert 'ttl' in item


@pytest.mark.unit
def test_batch_write_analytics(mock_dynamodb_table):
    """Test batch writing analytics."""
    writer = DynamoDBWriter('test-stock-analytics')

    analytics_list = [
        {
            'symbol': 'AAPL',
            'timestamp': f'2025-11-03T17:19:{i:02d}.000000',
            'date': '2025-11-03',
            'current_price': 268.0 + i,
            'trading_signal': 'HOLD'
        }
        for i in range(10)
    ]

    result = writer.batch_write_analytics(analytics_list)

    assert result['success'] == 10
    assert result['failed'] == 0


@pytest.mark.unit
def test_get_latest_timestamp(mock_dynamodb_table):
    """Test getting latest timestamp for a symbol."""
    writer = DynamoDBWriter('test-stock-analytics')

    # Write some test data
    timestamps = [
        '2025-11-03T17:19:30.000000',
        '2025-11-03T17:19:35.000000',
        '2025-11-03T17:19:40.000000'
    ]

    for ts in timestamps:
        writer.write_analytics({
            'symbol': 'AAPL',
            'timestamp': ts,
            'date': '2025-11-03',
            'current_price': 268.04
        })

    latest = writer.get_latest_timestamp('AAPL')
    assert latest == timestamps[-1]
