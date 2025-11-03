"""Integration tests for the complete flow."""
import json
import base64
import pytest
from unittest.mock import Mock

from src import lambda_function
from src.analytics import TradingSignal


@pytest.mark.integration
def test_end_to_end_processing(mock_dynamodb_table, sample_stock_data):
    """Test complete end-to-end processing flow."""
    # Reset global state
    lambda_function.config = None
    lambda_function.analytics_calculator = None
    lambda_function.historical_loader = None
    lambda_function.dynamodb_writer = None
    lambda_function.historical_cache.clear()

    # Create Kinesis event
    data = json.dumps(sample_stock_data).encode('utf-8')
    encoded_data = base64.b64encode(data).decode('utf-8')

    event = {
        'Records': [
            {
                'kinesis': {
                    'data': encoded_data,
                    'partitionKey': 'AAPL',
                    'sequenceNumber': '12345'
                },
                'eventSource': 'aws:kinesis'
            }
        ]
    }

    context = Mock()
    context.function_name = 'test-function'

    # Process the event
    response = lambda_function.lambda_handler(event, context)

    # Verify response
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['processed'] == 1
    assert body['failed'] == 0

    # Verify data was written to DynamoDB
    table = mock_dynamodb_table
    db_response = table.get_item(
        Key={
            'symbol': 'AAPL',
            'timestamp': sample_stock_data['timestamp']
        }
    )

    assert 'Item' in db_response
    item = db_response['Item']
    assert item['symbol'] == 'AAPL'
    assert 'trading_signal' in item
    assert 'current_price' in item


@pytest.mark.integration
def test_multiple_records_batch_processing(mock_dynamodb_table):
    """Test batch processing of multiple records."""
    lambda_function.config = None
    lambda_function.analytics_calculator = None
    lambda_function.historical_loader = None
    lambda_function.dynamodb_writer = None
    lambda_function.historical_cache.clear()

    # Create multiple stock data records
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    records = []

    for symbol in symbols:
        stock_data = {
            'symbol': symbol,
            'price': 268.04,
            'change': -2.33,
            'change_percent': '-0.86',
            'high': 270.85,
            'low': 266.25,
            'open': 269.7,
            'previous_close': 270.37,
            'timestamp': f'2025-11-03T17:19:39.{symbols.index(symbol):06d}'
        }

        data = json.dumps(stock_data).encode('utf-8')
        encoded_data = base64.b64encode(data).decode('utf-8')

        records.append({
            'kinesis': {
                'data': encoded_data,
                'partitionKey': symbol,
                'sequenceNumber': f'{symbols.index(symbol):05d}'
            },
            'eventSource': 'aws:kinesis'
        })

    event = {'Records': records}
    context = Mock()

    # Process the event
    response = lambda_function.lambda_handler(event, context)

    # Verify all records were processed
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['processed'] == 3
    assert body['failed'] == 0


@pytest.mark.integration
def test_analytics_with_time_windows(mock_dynamodb_table):
    """Test analytics calculation with time window data."""
    lambda_function.config = None
    lambda_function.analytics_calculator = None
    lambda_function.historical_loader = None
    lambda_function.dynamodb_writer = None
    lambda_function.historical_cache.clear()

    # Initialize
    lambda_function.initialize()

    # First, write some historical data to DynamoDB
    for i in range(5):
        analytics = {
            'symbol': 'AAPL',
            'timestamp': f'2025-11-03T17:{14+i}:00.000000',
            'date': '2025-11-03',
            'price': 267.0 + i * 0.2,
            'current_price': 267.0 + i * 0.2,
            'trading_signal': 'HOLD'
        }
        lambda_function.dynamodb_writer.write_analytics(analytics)

    # Now process a new record
    stock_data = {
        'symbol': 'AAPL',
        'price': 268.04,
        'change': -2.33,
        'change_percent': '-0.86',
        'high': 270.85,
        'low': 266.25,
        'open': 269.7,
        'previous_close': 270.37,
        'timestamp': '2025-11-03T17:19:39.000000'
    }

    analytics = lambda_function.process_stock_record(stock_data)

    # Verify analytics were calculated
    assert analytics is not None
    assert analytics['symbol'] == 'AAPL'
    assert 'trading_signal' in analytics
    assert analytics['trading_signal'] in ['BUY', 'HOLD', 'SELL']
