"""Historical data loader for querying previous day's stock data."""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)


class HistoricalDataLoader:
    """Loads historical stock data from DynamoDB."""

    def __init__(self, table_name: str, region: str = 'us-east-1'):
        """
        Initialize historical data loader.

        Args:
            table_name: DynamoDB table name
            region: AWS region
        """
        self.table_name = table_name
        self.region = region
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_previous_day_summary(
        self,
        symbol: str,
        reference_date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get previous trading day's summary for a symbol.

        Args:
            symbol: Stock symbol
            reference_date: Reference date (defaults to today)

        Returns:
            Dictionary with previous day's summary or None if not found
        """
        # Check cache first
        cache_key = f"{symbol}:{reference_date or datetime.now().date()}"
        if cache_key in self._cache:
            logger.debug(f"Returning cached data for {cache_key}")
            return self._cache[cache_key]

        if reference_date is None:
            reference_date = datetime.now()

        # Get previous day (simple approach - actual implementation should skip weekends/holidays)
        previous_date = reference_date - timedelta(days=1)
        date_str = previous_date.strftime('%Y-%m-%d')

        try:
            # Query using DateIndex GSI for all records from previous day
            response = self.table.query(
                IndexName='DateIndex',
                KeyConditionExpression=Key('symbol').eq(symbol) & Key('date').eq(date_str),
                ScanIndexForward=True  # Ascending order
            )

            items = response.get('Items', [])
            if not items:
                logger.info(f"No historical data found for {symbol} on {date_str}")
                return None

            # Calculate summary from all records
            summary = self._calculate_daily_summary(items, symbol, date_str)

            # Cache the result
            self._cache[cache_key] = summary

            return summary

        except Exception as e:
            logger.error(f"Error querying historical data for {symbol}: {e}")
            return None

    def get_time_window_data(
        self,
        symbol: str,
        window_minutes: int,
        reference_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get stock data for a specific time window.

        Args:
            symbol: Stock symbol
            window_minutes: Time window in minutes
            reference_time: Reference time (defaults to now)

        Returns:
            List of stock records within the time window
        """
        if reference_time is None:
            reference_time = datetime.now()

        start_time = reference_time - timedelta(minutes=window_minutes)
        start_timestamp = start_time.isoformat()
        end_timestamp = reference_time.isoformat()

        try:
            response = self.table.query(
                KeyConditionExpression=(
                    Key('symbol').eq(symbol) &
                    Key('timestamp').between(start_timestamp, end_timestamp)
                ),
                ScanIndexForward=True
            )

            items = response.get('Items', [])

            # Convert Decimal to float for easier processing
            return [self._convert_decimals(item) for item in items]

        except Exception as e:
            logger.error(f"Error querying time window data for {symbol}: {e}")
            return []

    def _calculate_daily_summary(
        self,
        items: List[Dict[str, Any]],
        symbol: str,
        date: str
    ) -> Dict[str, Any]:
        """
        Calculate daily summary statistics from items.

        Args:
            items: List of stock records from a day
            symbol: Stock symbol
            date: Date string

        Returns:
            Summary dictionary
        """
        if not items:
            return {}

        # Convert Decimals to float
        items = [self._convert_decimals(item) for item in items]

        # Sort by timestamp
        sorted_items = sorted(items, key=lambda x: x.get('timestamp', ''))

        # Extract prices
        prices = [float(item.get('price', 0)) for item in sorted_items if 'price' in item]

        if not prices:
            return {}

        first_item = sorted_items[0]
        last_item = sorted_items[-1]

        summary = {
            'symbol': symbol,
            'date': date,
            'open': first_item.get('open', first_item.get('price')),
            'close': last_item.get('price'),
            'high': max(prices),
            'low': min(prices),
            'previous_close': first_item.get('previous_close'),
            'volume_count': len(items),
            'average_price': sum(prices) / len(prices),
            'first_timestamp': first_item.get('timestamp'),
            'last_timestamp': last_item.get('timestamp'),
        }

        logger.info(
            f"Daily summary for {symbol} on {date}: "
            f"open={summary['open']:.2f}, close={summary['close']:.2f}, "
            f"high={summary['high']:.2f}, low={summary['low']:.2f}, "
            f"count={summary['volume_count']}"
        )

        return summary

    def _convert_decimals(self, obj: Any) -> Any:
        """
        Recursively convert Decimal objects to float.

        Args:
            obj: Object to convert

        Returns:
            Converted object
        """
        if isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_decimals(value) for key, value in obj.items()}
        elif isinstance(obj, Decimal):
            return float(obj)
        else:
            return obj

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()
        logger.debug("Historical data cache cleared")
