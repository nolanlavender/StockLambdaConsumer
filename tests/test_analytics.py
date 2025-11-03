"""Tests for analytics calculator."""
import pytest

from src.analytics import StockAnalytics, TradingSignal


def test_analytics_initialization():
    """Test analytics calculator initialization."""
    analytics = StockAnalytics()

    assert analytics.time_windows_minutes == [1, 5, 15, 30, 60, 120]
    assert analytics.ma_windows_minutes == [5, 15, 30, 60]
    assert analytics.volatility_threshold == 0.02
    assert analytics.momentum_threshold == 0.015


def test_calculate_intraday_metrics(sample_stock_data):
    """Test intraday metrics calculation."""
    analytics = StockAnalytics()

    metrics = analytics._calculate_intraday_metrics(sample_stock_data, None)

    assert 'intraday_change_from_open' in metrics
    assert 'intraday_change_from_open_percent' in metrics

    # Current: 268.04, Open: 269.7
    expected_change = 268.04 - 269.7
    assert abs(metrics['intraday_change_from_open'] - expected_change) < 0.01


def test_calculate_intraday_metrics_with_gap(
    sample_stock_data,
    sample_previous_day_summary
):
    """Test gap analysis with previous day data."""
    analytics = StockAnalytics()

    metrics = analytics._calculate_intraday_metrics(
        sample_stock_data,
        sample_previous_day_summary
    )

    assert 'gap' in metrics
    assert 'gap_percent' in metrics
    assert 'gap_type' in metrics

    # Open: 269.7, Prev Close: 270.37
    expected_gap = 269.7 - 270.37
    assert abs(metrics['gap'] - expected_gap) < 0.01


def test_calculate_time_window_analytics(sample_time_window_data):
    """Test time window analytics calculation."""
    analytics = StockAnalytics()
    current_price = 268.04

    window_analytics = analytics._calculate_time_window_analytics(
        current_price,
        sample_time_window_data
    )

    assert 'change_5min' in window_analytics
    assert 'change_5min_percent' in window_analytics
    assert 'high_5min' in window_analytics
    assert 'low_5min' in window_analytics
    assert 'volume_5min' in window_analytics


def test_calculate_moving_averages(sample_time_window_data):
    """Test moving average calculation."""
    analytics = StockAnalytics()

    ma_analytics = analytics._calculate_moving_averages(sample_time_window_data)

    assert 'ma_5min' in ma_analytics
    assert 'ma_15min' in ma_analytics

    # Verify MA is average of prices
    ma_5 = ma_analytics['ma_5min']
    prices_5 = [267.0, 267.5, 268.04]
    expected_ma_5 = sum(prices_5) / len(prices_5)
    assert abs(ma_5 - expected_ma_5) < 0.01


def test_calculate_volatility_and_momentum(sample_time_window_data):
    """Test volatility and momentum calculation."""
    analytics = StockAnalytics()

    metrics = analytics._calculate_volatility_and_momentum(sample_time_window_data)

    assert 'volatility' in metrics
    assert 'momentum' in metrics


def test_generate_buy_signal():
    """Test BUY signal generation."""
    analytics = StockAnalytics()

    test_analytics = {
        'current_price': 100.0
    }
    volatility_metrics = {
        'momentum': 0.02,  # Above threshold
        'volatility': 0.01,  # Below threshold
        'price_acceleration': 0.005
    }
    ma_analytics = {
        'ma_15min': 101.0  # Price below MA
    }

    signal = analytics._generate_trading_signal(
        test_analytics,
        volatility_metrics,
        ma_analytics
    )

    assert signal == TradingSignal.BUY


def test_generate_sell_signal():
    """Test SELL signal generation."""
    analytics = StockAnalytics()

    test_analytics = {
        'current_price': 103.0
    }
    volatility_metrics = {
        'momentum': -0.02,  # Negative momentum
        'volatility': 0.03,  # High volatility
        'price_acceleration': -0.005
    }
    ma_analytics = {
        'ma_15min': 100.0  # Price above MA
    }

    signal = analytics._generate_trading_signal(
        test_analytics,
        volatility_metrics,
        ma_analytics
    )

    assert signal == TradingSignal.SELL


def test_generate_hold_signal():
    """Test HOLD signal generation."""
    analytics = StockAnalytics()

    test_analytics = {
        'current_price': 100.0
    }
    volatility_metrics = {
        'momentum': 0.005,  # Low momentum
        'volatility': 0.015,  # Normal volatility
    }
    ma_analytics = {
        'ma_15min': 100.0
    }

    signal = analytics._generate_trading_signal(
        test_analytics,
        volatility_metrics,
        ma_analytics
    )

    assert signal == TradingSignal.HOLD


def test_calculate_all_analytics(
    sample_stock_data,
    sample_time_window_data,
    sample_previous_day_summary
):
    """Test complete analytics calculation."""
    analytics = StockAnalytics()

    result = analytics.calculate_all_analytics(
        current_data=sample_stock_data,
        time_window_data=sample_time_window_data,
        previous_day_summary=sample_previous_day_summary
    )

    # Verify required fields
    assert result['symbol'] == 'AAPL'
    assert result['current_price'] == 268.04
    assert 'trading_signal' in result
    assert 'signal_reason' in result
    assert 'intraday_change_from_open' in result
    assert 'gap' in result
    assert 'ma_5min' in result
    assert 'volatility' in result
    assert 'momentum' in result
