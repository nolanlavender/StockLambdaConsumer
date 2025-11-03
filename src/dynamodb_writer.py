"""DynamoDB writer for storing stock analytics."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DynamoDBWriter:
    """Writes stock analytics to DynamoDB."""

    def __init__(
        self,
        table_name: str,
        region: str = 'us-east-1',
        retention_days: int = 7
    ):
        """
        Initialize DynamoDB writer.

        Args:
            table_name: DynamoDB table name
            region: AWS region
            retention_days: Number of days to retain data (for TTL)
        """
        self.table_name = table_name
        self.region = region
        self.retention_days = retention_days
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)

    def write_analytics(self, analytics: Dict[str, Any]) -> bool:
        """
        Write analytics record to DynamoDB.

        Args:
            analytics: Analytics dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add TTL (time to live)
            ttl_timestamp = int(
                (datetime.now() + timedelta(days=self.retention_days)).timestamp()
            )

            # Convert floats to Decimal for DynamoDB
            item = self._convert_floats_to_decimal(analytics)
            item['ttl'] = ttl_timestamp

            # Write to DynamoDB
            self.table.put_item(Item=item)

            logger.debug(
                f"Wrote analytics for {analytics.get('symbol')} at "
                f"{analytics.get('timestamp')} to DynamoDB"
            )

            return True

        except ClientError as e:
            logger.error(
                f"Error writing to DynamoDB: {e.response['Error']['Message']}"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing to DynamoDB: {e}")
            return False

    def batch_write_analytics(self, analytics_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Write multiple analytics records in batch.

        Args:
            analytics_list: List of analytics dictionaries

        Returns:
            Dictionary with success and failure counts
        """
        if not analytics_list:
            return {'success': 0, 'failed': 0}

        success_count = 0
        failed_count = 0
        ttl_timestamp = int(
            (datetime.now() + timedelta(days=self.retention_days)).timestamp()
        )

        try:
            # DynamoDB batch write can handle up to 25 items at a time
            with self.table.batch_writer() as batch:
                for analytics in analytics_list:
                    try:
                        item = self._convert_floats_to_decimal(analytics)
                        item['ttl'] = ttl_timestamp
                        batch.put_item(Item=item)
                        success_count += 1
                    except Exception as e:
                        logger.error(
                            f"Error preparing item for batch write: {e}"
                        )
                        failed_count += 1

            logger.info(
                f"Batch write completed: {success_count} success, "
                f"{failed_count} failed"
            )

        except ClientError as e:
            logger.error(
                f"Batch write error: {e.response['Error']['Message']}"
            )
            failed_count = len(analytics_list) - success_count

        return {'success': success_count, 'failed': failed_count}

    def _convert_floats_to_decimal(self, obj: Any) -> Any:
        """
        Recursively convert float values to Decimal for DynamoDB.

        Args:
            obj: Object to convert

        Returns:
            Converted object
        """
        if isinstance(obj, float):
            # Convert to string first to avoid precision issues
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {key: self._convert_floats_to_decimal(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimal(item) for item in obj]
        else:
            return obj

    def get_latest_timestamp(self, symbol: str) -> str:
        """
        Get the timestamp of the most recent record for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            ISO timestamp string or empty string if not found
        """
        try:
            response = self.table.query(
                KeyConditionExpression='symbol = :symbol',
                ExpressionAttributeValues={':symbol': symbol},
                ScanIndexForward=False,  # Descending order (newest first)
                Limit=1,
                ProjectionExpression='#ts',
                ExpressionAttributeNames={'#ts': 'timestamp'}
            )

            items = response.get('Items', [])
            if items:
                return items[0].get('timestamp', '')

            return ''

        except Exception as e:
            logger.error(f"Error getting latest timestamp for {symbol}: {e}")
            return ''

    def get_last_update_time(self) -> datetime:
        """
        Get the timestamp of the most recent record across all symbols.

        Returns:
            datetime of last update or None if no records found
        """
        try:
            # Scan table for most recent timestamp
            # Note: This is not efficient for large tables
            # In production, consider maintaining a separate metadata table
            response = self.table.scan(
                ProjectionExpression='#ts',
                ExpressionAttributeNames={'#ts': 'timestamp'},
                Limit=1000  # Limit scan
            )

            items = response.get('Items', [])
            if not items:
                return None

            # Find the most recent timestamp
            timestamps = [
                datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00'))
                for item in items
                if 'timestamp' in item
            ]

            if timestamps:
                return max(timestamps)

            return None

        except Exception as e:
            logger.error(f"Error getting last update time: {e}")
            return None
