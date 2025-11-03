import pytz
from datetime import datetime, time
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class MarketHours:
    """
    Utility class to check if the stock market is currently open
    Supports US market hours with holiday awareness
    """

    def __init__(self):
        self.market_timezone = pytz.timezone('America/New_York')
        self.market_open_time = time(9, 30)  # 9:30 AM EST
        self.market_close_time = time(16, 0)  # 4:00 PM EST

        # US stock market holidays (add more as needed)
        self.market_holidays_2024 = [
            # New Year's Day
            datetime(2024, 1, 1),
            # Martin Luther King Jr. Day
            datetime(2024, 1, 15),
            # Presidents' Day
            datetime(2024, 2, 19),
            # Good Friday
            datetime(2024, 3, 29),
            # Memorial Day
            datetime(2024, 5, 27),
            # Juneteenth
            datetime(2024, 6, 19),
            # Independence Day
            datetime(2024, 7, 4),
            # Labor Day
            datetime(2024, 9, 2),
            # Thanksgiving Day
            datetime(2024, 11, 28),
            # Christmas Day
            datetime(2024, 12, 25),
        ]

        self.market_holidays_2025 = [
            # New Year's Day
            datetime(2025, 1, 1),
            # Martin Luther King Jr. Day
            datetime(2025, 1, 20),
            # Presidents' Day
            datetime(2025, 2, 17),
            # Good Friday
            datetime(2025, 4, 18),
            # Memorial Day
            datetime(2025, 5, 26),
            # Juneteenth
            datetime(2025, 6, 19),
            # Independence Day
            datetime(2025, 7, 4),
            # Labor Day
            datetime(2025, 9, 1),
            # Thanksgiving Day
            datetime(2025, 11, 27),
            # Christmas Day
            datetime(2025, 12, 25),
        ]

    def get_current_market_time(self) -> datetime:
        """Get current time in market timezone (Eastern)"""
        return datetime.now(self.market_timezone)

    def is_market_holiday(self, date: datetime) -> bool:
        """Check if given date is a market holiday"""
        date_only = date.date()

        # Check 2024 holidays
        for holiday in self.market_holidays_2024:
            if holiday.date() == date_only:
                return True

        # Check 2025 holidays
        for holiday in self.market_holidays_2025:
            if holiday.date() == date_only:
                return True

        return False

    def is_weekday(self, date: datetime) -> bool:
        """Check if given date is a weekday (Monday=0 to Friday=4)"""
        return date.weekday() < 5

    def is_market_open(self, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Check if the market is currently open

        Args:
            current_time: Optional datetime to check (defaults to current time)

        Returns:
            Tuple of (is_open: bool, reason: str)
        """
        if current_time is None:
            current_time = self.get_current_market_time()
        elif current_time.tzinfo is None:
            # If timezone naive, assume it's already in market timezone
            current_time = self.market_timezone.localize(current_time)
        else:
            # Convert to market timezone
            current_time = current_time.astimezone(self.market_timezone)

        # Check if it's a weekday
        if not self.is_weekday(current_time):
            return False, f"Market closed: Weekend ({current_time.strftime('%A')})"

        # Check if it's a holiday
        if self.is_market_holiday(current_time):
            return False, f"Market closed: Holiday ({current_time.strftime('%Y-%m-%d')})"

        # Check market hours
        current_time_only = current_time.time()
        if current_time_only < self.market_open_time:
            return False, f"Market closed: Before opening hours (opens at {self.market_open_time})"
        elif current_time_only >= self.market_close_time:
            return False, f"Market closed: After closing hours (closed at {self.market_close_time})"

        return True, f"Market open: Regular trading hours"

    def get_next_market_open(self, current_time: Optional[datetime] = None) -> datetime:
        """
        Get the next time the market will open

        Args:
            current_time: Optional datetime to check from (defaults to current time)

        Returns:
            datetime of next market open
        """
        if current_time is None:
            current_time = self.get_current_market_time()
        elif current_time.tzinfo is None:
            current_time = self.market_timezone.localize(current_time)
        else:
            current_time = current_time.astimezone(self.market_timezone)

        # Start checking from tomorrow if market is closed today
        check_date = current_time.date()
        if current_time.time() >= self.market_close_time:
            check_date = check_date.replace(day=check_date.day + 1)

        # Find next weekday that's not a holiday
        while True:
            next_open = datetime.combine(check_date, self.market_open_time)
            next_open = self.market_timezone.localize(next_open)

            if self.is_weekday(next_open) and not self.is_market_holiday(next_open):
                return next_open

            # Move to next day
            check_date = check_date.replace(day=check_date.day + 1)

    def log_market_status(self, current_time: Optional[datetime] = None) -> None:
        """Log current market status"""
        is_open, reason = self.is_market_open(current_time)

        if current_time is None:
            current_time = self.get_current_market_time()

        logger.info(f"Market status check at {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}: {reason}")

        if not is_open:
            next_open = self.get_next_market_open(current_time)
            logger.info(f"Next market open: {next_open.strftime('%Y-%m-%d %H:%M:%S %Z')}")
