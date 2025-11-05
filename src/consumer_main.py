"""Continuous Kinesis consumer for ECS/Fargate deployment."""
import base64
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

from config import get_config, Config
from analytics import StockAnalytics
from historical_data import HistoricalDataLoader
from dynamodb_writer import DynamoDBWriter
from rolling_windows import RollingWindowStore
from state_persistence import StatePersistence
from market_hours import MarketHours

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Global state
config: Optional[Config] = None
analytics_calculator: Optional[StockAnalytics] = None
dynamodb_writer: Optional[DynamoDBWriter] = None
rolling_store: Optional[RollingWindowStore] = None
state_persistence: Optional[StatePersistence] = None
market_hours: Optional[MarketHours] = None
kinesis_client: Optional[Any] = None
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def initialize():
    """Initialize all global resources."""
    global config, analytics_calculator, dynamodb_writer, rolling_store
    global state_persistence, market_hours, kinesis_client

    logger.info("Initializing consumer...")

    # Load configuration
    config = get_config()
    logger.info("Configuration loaded")

    # Initialize analytics calculator
    analytics_calculator = StockAnalytics(
        time_windows_minutes=config.time_windows_minutes,
        moving_average_windows_minutes=config.moving_average_windows_minutes,
        volatility_threshold=config.volatility_threshold,
        momentum_threshold=config.momentum_threshold
    )
    logger.info("Analytics calculator initialized")

    # Initialize DynamoDB writer
    dynamodb_writer = DynamoDBWriter(
        table_name=config.dynamodb_table_name,
        region=config.aws_region,
        retention_days=config.data_retention_days
    )
    logger.info("DynamoDB writer initialized")

    # Initialize rolling window store
    rolling_store = RollingWindowStore(config.time_windows_minutes)
    logger.info(f"Rolling window store initialized with windows: {config.time_windows_minutes}")

    # Initialize state persistence
    state_bucket = os.environ.get('STATE_BUCKET')
    if state_bucket:
        state_persistence = StatePersistence(state_bucket, config.aws_region)
        logger.info(f"State persistence initialized with bucket: {state_bucket}")

        # Try to load previous state
        loaded_store = state_persistence.load_state()
        if loaded_store:
            rolling_store = loaded_store
            logger.info("Previous state loaded successfully")
        else:
            logger.info("No previous state found, starting fresh")
    else:
        logger.warning("STATE_BUCKET not set, state persistence disabled")

    # Initialize market hours checker
    market_hours = MarketHours()
    logger.info("Market hours checker initialized")

    # Initialize Kinesis client
    kinesis_client = boto3.client('kinesis', region_name=config.aws_region)
    logger.info("Kinesis client initialized")

    logger.info("Initialization complete!")


def load_historical_context(symbol: str) -> Dict[str, Any]:
    """
    Load historical context for a symbol from DynamoDB.

    Args:
        symbol: Stock symbol

    Returns:
        Dictionary with historical context
    """
    historical_loader = HistoricalDataLoader(
        table_name=config.dynamodb_table_name,
        region=config.aws_region
    )

    previous_day_summary = historical_loader.get_previous_day_summary(symbol)

    return {
        'previous_day_summary': previous_day_summary
    }


def process_record(record_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process a single stock record.

    Args:
        record_data: Stock data from Kinesis

    Returns:
        Analytics dictionary or None if processing fails
    """
    if not analytics_calculator or not rolling_store:
        logger.error("Analytics calculator or rolling store not initialized")
        return None

    symbol = record_data.get('symbol')
    if not symbol:
        logger.error("Record missing symbol field")
        return None

    # Add to rolling windows
    rolling_store.add_data_point(symbol, record_data)

    # Get window data from in-memory store
    time_window_data = rolling_store.get_all_window_data(symbol)

    # Load previous day summary (only once per symbol per day, could be cached)
    historical_context = load_historical_context(symbol)
    previous_day_summary = historical_context.get('previous_day_summary')

    # Calculate analytics
    analytics = analytics_calculator.calculate_all_analytics(
        current_data=record_data,
        time_window_data=time_window_data,
        previous_day_summary=previous_day_summary
    )

    return analytics


def get_shard_iterator(stream_name: str, shard_id: str) -> Optional[str]:
    """
    Get a shard iterator for reading from Kinesis.

    Args:
        stream_name: Kinesis stream name
        shard_id: Shard ID

    Returns:
        Shard iterator or None if error
    """
    try:
        response = kinesis_client.get_shard_iterator(
            StreamName=stream_name,
            ShardId=shard_id,
            ShardIteratorType='LATEST'
        )
        return response['ShardIterator']
    except ClientError as e:
        logger.error(f"Error getting shard iterator: {e}")
        return None


def process_kinesis_records(stream_name: str):
    """
    Continuously poll Kinesis and process records.

    Args:
        stream_name: Kinesis stream name
    """
    logger.info(f"Starting to poll Kinesis stream: {stream_name}")

    # Get list of shards
    try:
        response = kinesis_client.describe_stream(StreamName=stream_name)
        shards = response['StreamDescription']['Shards']
        logger.info(f"Found {len(shards)} shards")
    except ClientError as e:
        logger.error(f"Error describing stream: {e}")
        return

    # For now, process the first shard (could be extended for multiple shards)
    shard_id = shards[0]['ShardId']
    logger.info(f"Processing shard: {shard_id}")

    shard_iterator = get_shard_iterator(stream_name, shard_id)
    if not shard_iterator:
        logger.error("Failed to get shard iterator")
        return

    analytics_batch = []
    last_batch_flush = datetime.now()
    records_processed = 0
    last_stats_log = datetime.now()

    while not shutdown_requested:
        try:
            # Check market hours
            if config and config.enforce_market_hours and not config.test_mode:
                is_open, reason = market_hours.is_market_open()
                if not is_open:
                    logger.info(f"Market closed: {reason}. Sleeping for 60 seconds...")
                    time.sleep(60)
                    continue

            # Get records from Kinesis
            response = kinesis_client.get_records(
                ShardIterator=shard_iterator,
                Limit=100
            )

            records = response['Records']
            shard_iterator = response['NextShardIterator']

            if records:
                logger.info(f"Received {len(records)} records from Kinesis")

                for record in records:
                    # Decode data - handle both direct bytes and base64-encoded formats
                    data = record['Data']

                    # boto3 returns bytes, try to decode as JSON directly first
                    try:
                        stock_data = json.loads(data)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        # If direct decode fails, data might be in unexpected format
                        # Try decoding as UTF-8 string first
                        try:
                            if isinstance(data, bytes):
                                data_str = data.decode('utf-8')
                                stock_data = json.loads(data_str)
                            else:
                                # If it's already a string, just parse it
                                stock_data = json.loads(data)
                        except Exception as decode_error:
                            logger.error(f"Failed to decode record data. Type: {type(data)}, First 100 bytes: {repr(data[:100] if len(data) > 100 else data)}")
                            raise decode_error

                    # Track latency from record timestamp to analytics completion
                    record_timestamp_str = stock_data.get('timestamp')
                    if record_timestamp_str:
                        try:
                            record_timestamp = datetime.fromisoformat(record_timestamp_str.replace('Z', '+00:00'))
                            analytics_start = datetime.now(record_timestamp.tzinfo or None)
                        except Exception:
                            record_timestamp = None
                            analytics_start = None
                    else:
                        record_timestamp = None
                        analytics_start = None

                    # Process record
                    analytics = process_record(stock_data)

                    # Calculate and log latency (excluding DynamoDB write time)
                    if analytics and record_timestamp and analytics_start:
                        analytics_end = datetime.now(record_timestamp.tzinfo or None)
                        latency_ms = (analytics_end - record_timestamp).total_seconds() * 1000
                        # Log latency every 50 records to avoid log spam
                        if records_processed % 50 == 0:
                            logger.info(f"Latency (record timestamp → analytics complete): {latency_ms:.2f}ms for {stock_data.get('symbol', 'Unknown')}")

                    if analytics:
                        analytics_batch.append(analytics)
                        records_processed += 1

                        # Log progress
                        symbol = stock_data.get('symbol', 'Unknown')
                        logger.debug(
                            f"Processed {symbol}: "
                            f"signal={analytics.get('trading_signal')}, "
                            f"momentum={analytics.get('momentum', 0):.4f}"
                        )

                # Check if batch should be flushed
                if len(analytics_batch) >= config.batch_max_size:
                    logger.info(f"Flushing batch of {len(analytics_batch)} analytics (size limit)")
                    result = dynamodb_writer.batch_write_analytics(analytics_batch)
                    logger.info(
                        f"Batch written: {result['success']} success, {result['failed']} failed"
                    )
                    analytics_batch.clear()
                    last_batch_flush = datetime.now()

                elif datetime.now() - last_batch_flush > timedelta(minutes=config.batch_write_interval_minutes):
                    if analytics_batch:
                        logger.info(f"Flushing batch of {len(analytics_batch)} analytics (time limit)")
                        result = dynamodb_writer.batch_write_analytics(analytics_batch)
                        logger.info(
                            f"Batch written: {result['success']} success, {result['failed']} failed"
                        )
                        analytics_batch.clear()
                    last_batch_flush = datetime.now()

            else:
                # No records available, sleep briefly
                time.sleep(1)

            # Log stats periodically
            if datetime.now() - last_stats_log > timedelta(minutes=5):
                stats = rolling_store.get_all_stats()
                total_points = sum(
                    sum(window_stats.values())
                    for window_stats in stats.values()
                )
                logger.info(
                    f"Stats: {len(stats)} symbols tracked, "
                    f"{total_points} total data points in memory, "
                    f"{records_processed} records processed total"
                )
                last_stats_log = datetime.now()

                # Save state periodically
                if state_persistence:
                    logger.info("Saving state to S3...")
                    state_persistence.save_state(rolling_store)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            break
        except Exception as e:
            logger.error(f"Error processing records: {e}", exc_info=True)
            time.sleep(5)  # Brief pause on error

    # Final flush
    if analytics_batch:
        logger.info(f"Final flush of {len(analytics_batch)} analytics")
        result = dynamodb_writer.batch_write_analytics(analytics_batch)
        logger.info(
            f"Final batch written: {result['success']} success, {result['failed']} failed"
        )

    # Save final state
    if state_persistence and rolling_store:
        logger.info("Saving final state to S3...")
        state_persistence.save_state(rolling_store)

    logger.info(f"Consumer stopped. Total records processed: {records_processed}")


def main():
    """Main entry point for the consumer."""
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("=" * 60)
    logger.info("Stock Analytics Consumer - ECS/Fargate Mode")
    logger.info("=" * 60)

    try:
        # Initialize
        initialize()

        # Get stream name from environment
        stream_name = os.environ.get('KINESIS_STREAM_NAME')
        if not stream_name:
            logger.error("KINESIS_STREAM_NAME environment variable not set")
            sys.exit(1)

        # Start processing
        process_kinesis_records(stream_name)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Consumer shutdown complete")


if __name__ == '__main__':
    main()
