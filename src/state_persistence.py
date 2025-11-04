"""State persistence for rolling windows to S3."""
import logging
import json
import gzip
from datetime import datetime
from typing import Optional
import boto3
from botocore.exceptions import ClientError

from rolling_windows import RollingWindowStore

logger = logging.getLogger(__name__)


class StatePersistence:
    """Handles saving and loading rolling window state to/from S3."""

    def __init__(self, bucket_name: str, region: str = 'us-east-1'):
        """
        Initialize state persistence.

        Args:
            bucket_name: S3 bucket name for state storage
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)

    def _get_state_key(self, date: Optional[datetime] = None) -> str:
        """
        Get the S3 key for state storage.

        Args:
            date: Date for the state file (defaults to today)

        Returns:
            S3 key
        """
        if date is None:
            date = datetime.now()

        return f"state/rolling-windows/{date.strftime('%Y-%m-%d')}.json.gz"

    def save_state(
        self,
        store: RollingWindowStore,
        date: Optional[datetime] = None
    ) -> bool:
        """
        Save rolling window state to S3.

        Args:
            store: RollingWindowStore to save
            date: Date for the state file (defaults to today)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize to JSON
            json_data = store.to_json()

            # Compress
            compressed_data = gzip.compress(json_data.encode('utf-8'))

            # Get S3 key
            key = self._get_state_key(date)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=compressed_data,
                ContentType='application/json',
                ContentEncoding='gzip',
                Metadata={
                    'timestamp': datetime.now().isoformat(),
                    'uncompressed_size': str(len(json_data)),
                    'compressed_size': str(len(compressed_data))
                }
            )

            stats = store.get_all_stats()
            total_points = sum(
                sum(window_stats.values())
                for window_stats in stats.values()
            )

            logger.info(
                f"State saved to S3: s3://{self.bucket_name}/{key} "
                f"({len(stats)} symbols, {total_points} total data points, "
                f"{len(compressed_data):,} bytes compressed)"
            )

            return True

        except ClientError as e:
            logger.error(f"Error saving state to S3: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving state: {e}", exc_info=True)
            return False

    def load_state(
        self,
        date: Optional[datetime] = None
    ) -> Optional[RollingWindowStore]:
        """
        Load rolling window state from S3.

        Args:
            date: Date for the state file (defaults to today)

        Returns:
            RollingWindowStore if found, None otherwise
        """
        try:
            # Get S3 key
            key = self._get_state_key(date)

            logger.info(f"Loading state from S3: s3://{self.bucket_name}/{key}")

            # Download from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )

            # Decompress
            compressed_data = response['Body'].read()
            json_data = gzip.decompress(compressed_data).decode('utf-8')

            # Deserialize
            store = RollingWindowStore.from_json(json_data)

            stats = store.get_all_stats()
            total_points = sum(
                sum(window_stats.values())
                for window_stats in stats.values()
            )

            logger.info(
                f"State loaded from S3: {len(stats)} symbols, "
                f"{total_points} total data points, "
                f"{len(compressed_data):,} bytes compressed"
            )

            return store

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.info(f"No state file found at s3://{self.bucket_name}/{key}")
                return None
            else:
                logger.error(f"Error loading state from S3: {e}", exc_info=True)
                return None
        except Exception as e:
            logger.error(f"Unexpected error loading state: {e}", exc_info=True)
            return None

    def state_exists(self, date: Optional[datetime] = None) -> bool:
        """
        Check if state file exists for a given date.

        Args:
            date: Date for the state file (defaults to today)

        Returns:
            True if state file exists, False otherwise
        """
        try:
            key = self._get_state_key(date)

            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )

            return True

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"Error checking state existence: {e}")
                return False

    def list_available_states(self, limit: int = 10) -> list:
        """
        List available state files.

        Args:
            limit: Maximum number of files to return

        Returns:
            List of state file keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix='state/rolling-windows/',
                MaxKeys=limit
            )

            if 'Contents' not in response:
                return []

            files = [
                {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                }
                for obj in response['Contents']
            ]

            return sorted(files, key=lambda x: x['last_modified'], reverse=True)

        except ClientError as e:
            logger.error(f"Error listing states: {e}")
            return []

    def delete_state(self, date: Optional[datetime] = None) -> bool:
        """
        Delete state file for a given date.

        Args:
            date: Date for the state file (defaults to today)

        Returns:
            True if successful, False otherwise
        """
        try:
            key = self._get_state_key(date)

            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )

            logger.info(f"State deleted from S3: s3://{self.bucket_name}/{key}")
            return True

        except ClientError as e:
            logger.error(f"Error deleting state: {e}")
            return False
