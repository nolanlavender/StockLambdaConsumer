"""Tests for market hours checker."""
import pytest
from datetime import datetime
import pytz

from src.market_hours import MarketHours


def test_market_hours_initialization():
    """Test MarketHours initialization."""
    mh = MarketHours()

    assert mh.market_timezone.zone == 'America/New_York'
    assert mh.market_open_time.hour == 9
    assert mh.market_open_time.minute == 30
    assert mh.market_close_time.hour == 16
    assert mh.market_close_time.minute == 0


def test_is_weekday():
    """Test weekday check."""
    mh = MarketHours()

    # Monday
    monday = datetime(2025, 11, 3, 10, 0)
    assert mh.is_weekday(monday) is True

    # Saturday
    saturday = datetime(2025, 11, 8, 10, 0)
    assert mh.is_weekday(saturday) is False

    # Sunday
    sunday = datetime(2025, 11, 9, 10, 0)
    assert mh.is_weekday(sunday) is False


def test_is_market_holiday():
    """Test holiday check."""
    mh = MarketHours()

    # New Year's Day 2025
    new_years = datetime(2025, 1, 1, 10, 0)
    assert mh.is_market_holiday(new_years) is True

    # Regular day
    regular_day = datetime(2025, 11, 3, 10, 0)
    assert mh.is_market_holiday(regular_day) is False


def test_is_market_open_during_hours():
    """Test market open check during trading hours."""
    mh = MarketHours()

    # Monday at 10 AM EST (market open)
    est = pytz.timezone('America/New_York')
    market_time = est.localize(datetime(2025, 11, 3, 10, 0))

    is_open, reason = mh.is_market_open(market_time)
    assert is_open is True
    assert 'open' in reason.lower()


def test_is_market_open_weekend():
    """Test market closed on weekend."""
    mh = MarketHours()

    # Saturday
    est = pytz.timezone('America/New_York')
    saturday = est.localize(datetime(2025, 11, 8, 10, 0))

    is_open, reason = mh.is_market_open(saturday)
    assert is_open is False
    assert 'weekend' in reason.lower()


def test_is_market_open_before_hours():
    """Test market closed before opening."""
    mh = MarketHours()

    # Monday at 9:00 AM EST (before market open)
    est = pytz.timezone('America/New_York')
    before_open = est.localize(datetime(2025, 11, 3, 9, 0))

    is_open, reason = mh.is_market_open(before_open)
    assert is_open is False
    assert 'before' in reason.lower()


def test_is_market_open_after_hours():
    """Test market closed after closing."""
    mh = MarketHours()

    # Monday at 5:00 PM EST (after market close)
    est = pytz.timezone('America/New_York')
    after_close = est.localize(datetime(2025, 11, 3, 17, 0))

    is_open, reason = mh.is_market_open(after_close)
    assert is_open is False
    assert 'after' in reason.lower()


def test_is_market_open_holiday():
    """Test market closed on holiday."""
    mh = MarketHours()

    # New Year's Day 2025 at 10 AM
    est = pytz.timezone('America/New_York')
    holiday = est.localize(datetime(2025, 1, 1, 10, 0))

    is_open, reason = mh.is_market_open(holiday)
    assert is_open is False
    assert 'holiday' in reason.lower()
