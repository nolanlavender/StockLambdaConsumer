"""Monitor Lambda for auto-shutdown mechanism."""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

from config import get_config, Config
from market_hours import MarketHours
from dynamodb_writer import DynamoDBWriter

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global instances
config: Optional[Config] = None
market_hours: Optional[MarketHours] = None
lambda_client: Optional[Any] = None
dynamodb_writer: Optional[DynamoDBWriter] = None


def initialize():
    """Initialize global resources."""
    global config, market_hours, lambda_client, dynamodb_writer

    if config is None:
        config = get_config()
        logger.info("Configuration loaded")

    if market_hours is None:
        market_hours = MarketHours()
        logger.info("Market hours checker initialized")

    if lambda_client is None:
        lambda_client = boto3.client('lambda', region_name=config.aws_region)
        logger.info("Lambda client initialized")

    if dynamodb_writer is None:
        dynamodb_writer = DynamoDBWriter(
            table_name=config.dynamodb_table_name,
            region=config.aws_region
        )
        logger.info("DynamoDB writer initialized")


def get_event_source_mapping_state(event_source_uuid: str) -> Optional[Dict[str, Any]]:
    """
    Get the current state of the Kinesis event source mapping.

    Args:
        event_source_uuid: UUID of the event source mapping

    Returns:
        Event source mapping info or None
    """
    if lambda_client is None:
        logger.error("Lambda client not initialized")
        return None

    try:
        response = lambda_client.get_event_source_mapping(
            UUID=event_source_uuid
        )
        return response
    except ClientError as e:
        logger.error(f"Error getting event source mapping: {e}")
        return None


def update_event_source_mapping(event_source_uuid: str, enabled: bool) -> bool:
    """
    Enable or disable the Kinesis event source mapping.

    Args:
        event_source_uuid: UUID of the event source mapping
        enabled: True to enable, False to disable

    Returns:
        True if successful, False otherwise
    """
    if lambda_client is None:
        logger.error("Lambda client not initialized")
        return False

    try:
        response = lambda_client.update_event_source_mapping(
            UUID=event_source_uuid,
            Enabled=enabled
        )

        state = response.get('State')
        logger.info(
            f"Event source mapping updated: enabled={enabled}, state={state}"
        )
        return True

    except ClientError as e:
        logger.error(f"Error updating event source mapping: {e}")
        return False


def check_last_data_update() -> Optional[datetime]:
    """
    Check when the last data was written to DynamoDB.

    Returns:
        datetime of last update or None if no data found
    """
    if dynamodb_writer is None:
        logger.error("DynamoDB writer not initialized")
        return None

    try:
        last_update = dynamodb_writer.get_last_update_time()
        return last_update
    except Exception as e:
        logger.error(f"Error checking last data update: {e}")
        return None


def should_disable_consumer() -> tuple[bool, str]:
    """
    Determine if consumer should be disabled.

    Returns:
        Tuple of (should_disable: bool, reason: str)
    """
    if config is None or market_hours is None:
        logger.error("Config or market_hours not initialized")
        return False, "Not initialized"

    # Check market hours (if enforced and not in test mode)
    if config.enforce_market_hours and not config.test_mode:
        is_open, reason = market_hours.is_market_open()
        if not is_open:
            return True, f"Market closed: {reason}"

    # Check last data update
    last_update = check_last_data_update()
    if last_update is None:
        logger.warning("No last update time found - keeping consumer enabled")
        return False, "No data found yet - keeping enabled"

    # Calculate time since last update
    time_since_update = datetime.now(last_update.tzinfo) - last_update
    timeout_minutes = config.no_data_timeout_minutes
    timeout_delta = timedelta(minutes=timeout_minutes)

    if time_since_update > timeout_delta:
        return True, (
            f"No data received in {time_since_update.total_seconds() / 60:.1f} minutes "
            f"(timeout: {timeout_minutes} minutes)"
        )

    logger.info(
        f"Data received {time_since_update.total_seconds() / 60:.1f} minutes ago - "
        f"consumer active"
    )
    return False, "Consumer active - data flowing"


def should_enable_consumer() -> tuple[bool, str]:
    """
    Determine if consumer should be enabled.

    Returns:
        Tuple of (should_enable: bool, reason: str)
    """
    if config is None or market_hours is None:
        logger.error("Config or market_hours not initialized")
        return False, "Not initialized"

    # Only enable during market hours (if enforced and not in test mode)
    if config.enforce_market_hours and not config.test_mode:
        is_open, reason = market_hours.is_market_open()
        if is_open:
            return True, f"Market open: {reason}"
        else:
            return False, f"Market closed: {reason}"

    # In test mode or market hours not enforced, always suggest enabled
    if config.test_mode:
        return True, "Test mode - enabling consumer"

    return True, "Market hours enforcement disabled - enabling consumer"


def lambda_handler(_event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Lambda handler for monitoring and auto-shutdown.

    Args:
        _event: EventBridge event (unused)
        _context: Lambda context (unused)

    Returns:
        Response dictionary
    """
    initialize()

    logger.info("Monitor check started")

    # Get event source UUID from environment
    event_source_uuid = os.environ.get('EVENT_SOURCE_UUID')
    if not event_source_uuid:
        logger.error("EVENT_SOURCE_UUID environment variable not set")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'EVENT_SOURCE_UUID not configured'})
        }

    # Get current state of event source mapping
    mapping_info = get_event_source_mapping_state(event_source_uuid)
    if not mapping_info:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Could not get event source mapping'})
        }

    current_state = mapping_info.get('State')
    is_currently_enabled = current_state in ['Enabled', 'Enabling']

    logger.info(f"Current event source state: {current_state}")

    action_taken = None

    if is_currently_enabled:
        # Check if we should disable
        should_disable, reason = should_disable_consumer()

        if should_disable:
            logger.info(f"Disabling consumer: {reason}")
            if update_event_source_mapping(event_source_uuid, False):
                action_taken = f"DISABLED: {reason}"
            else:
                action_taken = f"FAILED TO DISABLE: {reason}"
        else:
            logger.info(f"Consumer remains enabled: {reason}")
            action_taken = f"ACTIVE: {reason}"

    else:
        # Check if we should enable
        should_enable, reason = should_enable_consumer()

        if should_enable:
            logger.info(f"Enabling consumer: {reason}")
            if update_event_source_mapping(event_source_uuid, True):
                action_taken = f"ENABLED: {reason}"
            else:
                action_taken = f"FAILED TO ENABLE: {reason}"
        else:
            logger.info(f"Consumer remains disabled: {reason}")
            action_taken = f"DISABLED: {reason}"

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'action': action_taken,
            'event_source_uuid': event_source_uuid,
            'previous_state': current_state,
            'timestamp': datetime.now().isoformat()
        })
    }

    logger.info(f"Monitor check complete: {action_taken}")

    return response
