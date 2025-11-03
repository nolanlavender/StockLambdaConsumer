"""Main Lambda function for processing Kinesis stock data stream."""
import base64
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from config import get_config, Config
from analytics import StockAnalytics
from historical_data import HistoricalDataLoader
from dynamodb_writer import DynamoDBWriter

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global instances (reused across invocations)
config: Optional[Config] = None
analytics_calculator: Optional[StockAnalytics] = None
historical_loader: Optional[HistoricalDataLoader] = None
dynamodb_writer: Optional[DynamoDBWriter] = None

# Cache for historical data (per symbol)
historical_cache: Dict[str, Dict[str, Any]] = {}

# Batch management
analytics_batch: List[Dict[str, Any]] = []
last_batch_flush: Optional[datetime] = None


def initialize():
    """Initialize global resources (called on cold start)."""
    global config, analytics_calculator, historical_loader, dynamodb_writer

    if config is None:
        config = get_config()
        logger.info("Configuration loaded")

    if analytics_calculator is None:
        analytics_calculator = StockAnalytics(
            time_windows_minutes=config.time_windows_minutes,
            moving_average_windows_minutes=config.moving_average_windows_minutes,
            volatility_threshold=config.volatility_threshold,
            momentum_threshold=config.momentum_threshold
        )
        logger.info("Analytics calculator initialized")

    if historical_loader is None:
        historical_loader = HistoricalDataLoader(
            table_name=config.dynamodb_table_name,
            region=config.aws_region
        )
        logger.info("Historical data loader initialized")

    if dynamodb_writer is None:
        dynamodb_writer = DynamoDBWriter(
            table_name=config.dynamodb_table_name,
            region=config.aws_region,
            retention_days=config.data_retention_days
        )
        logger.info("DynamoDB writer initialized")


def load_historical_context(symbol: str) -> Dict[str, Any]:
    """
    Load historical context for a symbol.

    Args:
        symbol: Stock symbol

    Returns:
        Dictionary with historical context
    """
    if historical_loader is None:
        logger.error("Historical loader not initialized")
        return {'previous_day_summary': None}

    # Check cache first
    today = datetime.now().date()
    cache_key = f"{symbol}:{today}"

    if cache_key in historical_cache:
        logger.debug(f"Using cached historical data for {symbol}")
        return historical_cache[cache_key]

    # Load from DynamoDB
    previous_day_summary = historical_loader.get_previous_day_summary(symbol)

    context = {
        'previous_day_summary': previous_day_summary
    }

    # Cache the result
    historical_cache[cache_key] = context

    if previous_day_summary:
        logger.info(
            f"Loaded historical context for {symbol}: "
            f"prev_close={previous_day_summary.get('close'):.2f}, "
            f"prev_high={previous_day_summary.get('high'):.2f}, "
            f"prev_low={previous_day_summary.get('low'):.2f}"
        )
    else:
        logger.info(f"No historical data found for {symbol}")

    return context


def load_time_window_data(symbol: str) -> Dict[int, List[Dict[str, Any]]]:
    """
    Load data for all configured time windows.

    Args:
        symbol: Stock symbol

    Returns:
        Dictionary mapping window size (in minutes) to list of data points
    """
    if config is None or historical_loader is None:
        logger.error("Config or historical_loader not initialized")
        return {}

    time_window_data = {}

    for window_minutes in config.time_windows_minutes:
        data = historical_loader.get_time_window_data(symbol, window_minutes)
        time_window_data[window_minutes] = data

        logger.debug(
            f"Loaded {len(data)} data points for {symbol} "
            f"{window_minutes}min window"
        )

    return time_window_data


def flush_batch() -> Dict[str, int]:
    """
    Flush the current analytics batch to DynamoDB.

    Returns:
        Dictionary with success and failed counts
    """
    global analytics_batch, last_batch_flush

    if not analytics_batch:
        return {'success': 0, 'failed': 0}

    if dynamodb_writer is None:
        logger.error("DynamoDB writer not initialized")
        return {'success': 0, 'failed': len(analytics_batch)}

    batch_size = len(analytics_batch)
    logger.info(f"Flushing batch of {batch_size} analytics to DynamoDB")

    try:
        result = dynamodb_writer.batch_write_analytics(analytics_batch)
        logger.info(
            f"Batch flush complete: {result['success']} success, "
            f"{result['failed']} failed"
        )

        # Clear the batch and update flush time
        analytics_batch.clear()
        last_batch_flush = datetime.now()

        return result

    except Exception as e:
        logger.error(f"Error flushing batch: {e}", exc_info=True)
        return {'success': 0, 'failed': batch_size}


def should_flush_batch() -> bool:
    """
    Determine if batch should be flushed based on time or size.

    Returns:
        True if batch should be flushed
    """
    if config is None:
        return False

    # Check size limit
    if len(analytics_batch) >= config.batch_max_size:
        logger.info(
            f"Batch size ({len(analytics_batch)}) reached max size "
            f"({config.batch_max_size}), forcing flush"
        )
        return True

    # Check time limit
    if last_batch_flush is not None:
        time_since_flush = datetime.now() - last_batch_flush
        flush_interval = timedelta(minutes=config.batch_write_interval_minutes)

        if time_since_flush >= flush_interval:
            logger.info(
                f"Batch flush interval ({config.batch_write_interval_minutes} min) "
                f"reached, flushing batch"
            )
            return True

    return False


def process_stock_record(record_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process a single stock record.

    Args:
        record_data: Stock data from Kinesis

    Returns:
        Analytics dictionary or None if processing fails
    """
    if analytics_calculator is None:
        logger.error("Analytics calculator not initialized")
        return None

    symbol = record_data.get('symbol')
    if not symbol:
        logger.error("Record missing symbol field")
        return None

    logger.info(
        f"Processing {symbol}: price={record_data.get('price')}, "
        f"change={record_data.get('change_percent')}%"
    )

    # Load historical context
    historical_context = load_historical_context(symbol)
    previous_day_summary = historical_context.get('previous_day_summary')

    # Load time window data
    time_window_data = load_time_window_data(symbol)

    # Calculate analytics
    analytics = analytics_calculator.calculate_all_analytics(
        current_data=record_data,
        time_window_data=time_window_data,
        previous_day_summary=previous_day_summary
    )

    logger.info(
        f"Analytics for {symbol}: "
        f"signal={analytics.get('trading_signal')}, "
        f"momentum={analytics.get('momentum', 0):.4f}, "
        f"volatility={analytics.get('volatility', 0):.4f}"
    )

    return analytics


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing Kinesis events.

    Args:
        event: Kinesis event
        _context: Lambda context (unused)

    Returns:
        Response dictionary
    """
    global analytics_batch, last_batch_flush

    # Initialize on cold start
    initialize()

    # Initialize flush time if this is the first invocation
    if last_batch_flush is None:
        last_batch_flush = datetime.now()

    logger.info(f"Processing {len(event.get('Records', []))} Kinesis records")

    processed_count = 0
    failed_count = 0
    periodic_flush_count = 0

    for record in event.get('Records', []):
        try:
            # Decode Kinesis data
            payload = base64.b64decode(record['kinesis']['data'])
            stock_data = json.loads(payload)

            # Process the record
            analytics = process_stock_record(stock_data)
            if analytics:
                analytics_batch.append(analytics)
                processed_count += 1

                # Check if we should flush the batch periodically
                if should_flush_batch():
                    flush_result = flush_batch()
                    periodic_flush_count += 1
                    logger.info(
                        f"Periodic flush #{periodic_flush_count}: "
                        f"{flush_result['success']} success, "
                        f"{flush_result['failed']} failed"
                    )

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from Kinesis record: {e}")
            failed_count += 1
        except KeyError as e:
            logger.error(f"Missing required field in record: {e}")
            failed_count += 1
        except Exception as e:
            logger.error(f"Error processing record: {e}", exc_info=True)
            failed_count += 1

    # Final flush of any remaining analytics
    final_flush_result = {'success': 0, 'failed': 0}
    if analytics_batch:
        logger.info(f"Final flush of {len(analytics_batch)} remaining analytics")
        final_flush_result = flush_batch()

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'processed': processed_count,
            'failed': failed_count,
            'total_records': len(event.get('Records', [])),
            'periodic_flushes': periodic_flush_count,
            'batch_remaining': len(analytics_batch),
            'final_flush_success': final_flush_result['success'],
            'final_flush_failed': final_flush_result['failed']
        })
    }

    logger.info(
        f"Batch processing complete: {processed_count} processed, "
        f"{failed_count} failed, {periodic_flush_count} periodic flushes"
    )

    return response
