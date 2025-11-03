"""Pytest configuration and fixtures."""
import json
import os
from datetime import datetime
from typing import Dict, Any

import pytest
from moto import mock_dynamodb, mock_lambda
import boto3


@pytest.fixture
def aws_credentials():
    """Mock AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'


@pytest.fixture
def test_config():
    """Load test configuration."""
    config_path = os.path.join(
        os.path.dirname(__file__),
        'test_config.json'
    )
    with open(config_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def mock_dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table."""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

        table = dynamodb.create_table(
            TableName='test-stock-analytics',
            KeySchema=[
                {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'symbol', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'date', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'DateIndex',
                    'KeySchema': [
                        {'AttributeName': 'symbol', 'KeyType': 'HASH'},
                        {'AttributeName': 'date', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        yield table


@pytest.fixture
def sample_stock_data() -> Dict[str, Any]:
    """Sample stock data record."""
    return {
        'symbol': 'AAPL',
        'price': 268.04,
        'change': -2.33,
        'change_percent': '-0.86',
        'high': 270.85,
        'low': 266.25,
        'open': 269.7,
        'previous_close': 270.37,
        'timestamp': '2025-11-03T17:19:39.193597'
    }


@pytest.fixture
def sample_kinesis_event(sample_stock_data):
    """Sample Kinesis event."""
    import base64

    data = json.dumps(sample_stock_data).encode('utf-8')
    encoded_data = base64.b64encode(data).decode('utf-8')

    return {
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


@pytest.fixture
def sample_previous_day_summary() -> Dict[str, Any]:
    """Sample previous day summary."""
    return {
        'symbol': 'AAPL',
        'date': '2025-11-02',
        'open': 270.0,
        'close': 270.37,
        'high': 272.5,
        'low': 268.0,
        'previous_close': 269.5,
        'volume_count': 1000,
        'average_price': 270.2,
        'first_timestamp': '2025-11-02T09:30:00.000000',
        'last_timestamp': '2025-11-02T16:00:00.000000'
    }


@pytest.fixture
def sample_time_window_data() -> Dict[int, list]:
    """Sample time window data."""
    base_time = datetime.fromisoformat('2025-11-03T17:00:00')

    return {
        5: [
            {
                'symbol': 'AAPL',
                'price': 267.0,
                'timestamp': base_time.isoformat()
            },
            {
                'symbol': 'AAPL',
                'price': 267.5,
                'timestamp': (base_time.replace(minute=2)).isoformat()
            },
            {
                'symbol': 'AAPL',
                'price': 268.04,
                'timestamp': (base_time.replace(minute=4)).isoformat()
            }
        ],
        15: [
            {
                'symbol': 'AAPL',
                'price': 266.5,
                'timestamp': (base_time.replace(minute=0)).isoformat()
            },
            {
                'symbol': 'AAPL',
                'price': 267.0,
                'timestamp': (base_time.replace(minute=5)).isoformat()
            },
            {
                'symbol': 'AAPL',
                'price': 267.5,
                'timestamp': (base_time.replace(minute=10)).isoformat()
            },
            {
                'symbol': 'AAPL',
                'price': 268.04,
                'timestamp': (base_time.replace(minute=14)).isoformat()
            }
        ]
    }
