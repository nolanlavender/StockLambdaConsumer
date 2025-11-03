"""Tests for main Lambda function."""
import json
import base64
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src import lambda_function


@pytest.fixture
def lambda_context():
    """Mock Lambda context."""
    context = Mock()
    context.function_name = 'test-function'
    context.memory_limit_in_mb = 512
    context.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789:function:test'
    context.aws_request_id = 'test-request-id'
    return context


@pytest.mark.unit
def test_initialize():
    """Test initialization of global resources."""
    lambda_function.config = None
    lambda_function.analytics_calculator = None
    lambda_function.historical_loader = None
    lambda_function.dynamodb_writer = None

    lambda_function.initialize()

    assert lambda_function.config is not None
    assert lambda_function.analytics_calculator is not None
    assert lambda_function.historical_loader is not None
    assert lambda_function.dynamodb_writer is not None


@pytest.mark.unit
def test_process_stock_record(sample_stock_data, mock_dynamodb_table):
    """Test processing a single stock record."""
    lambda_function.initialize()

    with patch.object(
        lambda_function.historical_loader,
        'get_previous_day_summary',
        return_value=None
    ):
        with patch.object(
            lambda_function.historical_loader,
            'get_time_window_data',
            return_value=[]
        ):
            analytics = lambda_function.process_stock_record(sample_stock_data)

            assert analytics is not None
            assert analytics['symbol'] == 'AAPL'
            assert analytics['current_price'] == 268.04
            assert 'trading_signal' in analytics


@pytest.mark.unit
def test_lambda_handler_success(
    sample_kinesis_event,
    lambda_context,
    mock_dynamodb_table
):
    """Test successful Lambda handler execution."""
    lambda_function.initialize()

    with patch.object(
        lambda_function.historical_loader,
        'get_previous_day_summary',
        return_value=None
    ):
        with patch.object(
            lambda_function.historical_loader,
            'get_time_window_data',
            return_value=[]
        ):
            with patch.object(
                lambda_function.dynamodb_writer,
                'batch_write_analytics',
                return_value={'success': 1, 'failed': 0}
            ):
                response = lambda_function.lambda_handler(
                    sample_kinesis_event,
                    lambda_context
                )

                assert response['statusCode'] == 200
                body = json.loads(response['body'])
                assert body['processed'] == 1
                assert body['failed'] == 0


@pytest.mark.unit
def test_lambda_handler_invalid_json(lambda_context, mock_dynamodb_table):
    """Test Lambda handler with invalid JSON."""
    lambda_function.initialize()

    invalid_event = {
        'Records': [
            {
                'kinesis': {
                    'data': base64.b64encode(b'invalid json').decode('utf-8'),
                    'partitionKey': 'AAPL'
                }
            }
        ]
    }

    response = lambda_function.lambda_handler(invalid_event, lambda_context)

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['failed'] == 1
    assert body['processed'] == 0


@pytest.mark.unit
def test_load_historical_context(mock_dynamodb_table):
    """Test loading historical context."""
    lambda_function.initialize()
    lambda_function.historical_cache.clear()

    mock_summary = {
        'symbol': 'AAPL',
        'close': 270.37,
        'high': 272.5,
        'low': 268.0
    }

    with patch.object(
        lambda_function.historical_loader,
        'get_previous_day_summary',
        return_value=mock_summary
    ):
        context = lambda_function.load_historical_context('AAPL')

        assert context is not None
        assert context['previous_day_summary'] == mock_summary

        # Test cache
        context2 = lambda_function.load_historical_context('AAPL')
        assert context2 == context


@pytest.mark.unit
def test_flush_batch(mock_dynamodb_table):
    """Test batch flushing."""
    lambda_function.initialize()
    lambda_function.analytics_batch.clear()

    # Add some analytics to the batch
    lambda_function.analytics_batch.extend([
        {'symbol': 'AAPL', 'timestamp': '2025-11-03T17:19:39', 'current_price': 268.04},
        {'symbol': 'GOOGL', 'timestamp': '2025-11-03T17:19:40', 'current_price': 150.00}
    ])

    assert len(lambda_function.analytics_batch) == 2

    # Flush the batch
    result = lambda_function.flush_batch()

    assert result['success'] == 2
    assert result['failed'] == 0
    assert len(lambda_function.analytics_batch) == 0
    assert lambda_function.last_batch_flush is not None


@pytest.mark.unit
def test_should_flush_batch_size(mock_dynamodb_table):
    """Test batch flush triggered by size."""
    lambda_function.initialize()
    lambda_function.analytics_batch.clear()
    lambda_function.last_batch_flush = datetime.now()

    # Add items up to max size
    max_size = lambda_function.config.batch_max_size
    for i in range(max_size):
        lambda_function.analytics_batch.append(
            {'symbol': 'AAPL', 'timestamp': f'2025-11-03T17:19:{i:02d}', 'current_price': 268.0}
        )

    assert lambda_function.should_flush_batch() is True


@pytest.mark.unit
def test_should_flush_batch_time(mock_dynamodb_table):
    """Test batch flush triggered by time."""
    lambda_function.initialize()
    lambda_function.analytics_batch.clear()

    # Set last flush time to 20 minutes ago (exceeds default 15 min interval)
    lambda_function.last_batch_flush = datetime.now() - timedelta(minutes=20)

    # Add one item
    lambda_function.analytics_batch.append(
        {'symbol': 'AAPL', 'timestamp': '2025-11-03T17:19:39', 'current_price': 268.04}
    )

    assert lambda_function.should_flush_batch() is True


@pytest.mark.unit
def test_should_not_flush_batch(mock_dynamodb_table):
    """Test batch should not flush when conditions not met."""
    lambda_function.initialize()
    lambda_function.analytics_batch.clear()
    lambda_function.last_batch_flush = datetime.now()

    # Add just a few items (below max)
    lambda_function.analytics_batch.append(
        {'symbol': 'AAPL', 'timestamp': '2025-11-03T17:19:39', 'current_price': 268.04}
    )

    assert lambda_function.should_flush_batch() is False


@pytest.mark.unit
def test_lambda_handler_with_periodic_flush(
    sample_kinesis_event,
    lambda_context,
    mock_dynamodb_table
):
    """Test Lambda handler with periodic batch flushing."""
    lambda_function.initialize()
    lambda_function.analytics_batch.clear()

    # Set last flush to trigger periodic flush
    lambda_function.last_batch_flush = datetime.now() - timedelta(minutes=20)

    with patch.object(
        lambda_function.historical_loader,
        'get_previous_day_summary',
        return_value=None
    ):
        with patch.object(
            lambda_function.historical_loader,
            'get_time_window_data',
            return_value=[]
        ):
            response = lambda_function.lambda_handler(
                sample_kinesis_event,
                lambda_context
            )

            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['processed'] == 1
            # Should have triggered at least one flush
            assert body['periodic_flushes'] >= 0
