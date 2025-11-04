"""Analytics calculator for stock trading signals."""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class TradingSignal(Enum):
    """Trading signal recommendations."""
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class StockAnalytics:
    """Calculates real-time stock analytics and trading signals."""

    def __init__(
        self,
        time_windows_minutes: Optional[List[int]] = None,
        moving_average_windows_minutes: Optional[List[int]] = None,
        volatility_threshold: float = 0.02,
        momentum_threshold: float = 0.015
    ):
        """
        Initialize analytics calculator.

        Args:
            time_windows_minutes: List of time windows for analysis (in minutes)
            moving_average_windows_minutes: List of MA windows (in minutes)
            volatility_threshold: Threshold for high volatility (as decimal)
            momentum_threshold: Threshold for momentum signal (as decimal)
        """
        self.time_windows_minutes = time_windows_minutes or [1, 5, 15, 30, 60, 120]
        self.ma_windows_minutes = moving_average_windows_minutes or [5, 15, 30, 60]
        self.volatility_threshold = volatility_threshold
        self.momentum_threshold = momentum_threshold

    def calculate_all_analytics(
        self,
        current_data: Dict[str, Any],
        time_window_data: Dict[int, List[Dict[str, Any]]],
        previous_day_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive analytics for a stock.

        Args:
            current_data: Current stock data point
            time_window_data: Historical data organized by time window
            previous_day_summary: Summary from previous trading day

        Returns:
            Dictionary with all analytics
        """
        symbol = current_data.get('symbol')
        current_price = float(current_data.get('price', 0))
        timestamp = current_data.get('timestamp')

        analytics = {
            'symbol': symbol,
            'timestamp': timestamp,
            'current_price': current_price,
            'date': datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d'),
        }

        # Add raw data fields
        analytics.update({
            'change': current_data.get('change'),
            'change_percent': current_data.get('change_percent'),
            'high': current_data.get('high'),
            'low': current_data.get('low'),
            'open': current_data.get('open'),
            'previous_close': current_data.get('previous_close'),
        })

        # Calculate intraday metrics
        intraday_metrics = self._calculate_intraday_metrics(current_data, previous_day_summary)
        analytics.update(intraday_metrics)

        # Calculate time window analytics
        window_analytics = self._calculate_time_window_analytics(
            current_price, time_window_data
        )
        analytics.update(window_analytics)

        # Calculate moving averages
        ma_analytics = self._calculate_moving_averages(time_window_data)
        analytics.update(ma_analytics)

        # Calculate volatility and momentum
        volatility_metrics = self._calculate_volatility_and_momentum(time_window_data)
        analytics.update(volatility_metrics)

        # Generate trading signal
        trading_signal = self._generate_trading_signal(
            analytics, volatility_metrics, ma_analytics
        )
        analytics['trading_signal'] = trading_signal.value
        analytics['signal_reason'] = self._get_signal_reason(
            analytics, volatility_metrics, ma_analytics, trading_signal
        )

        logger.debug(f"Analytics calculated for {symbol}: {trading_signal.value}")

        return analytics

    def _calculate_intraday_metrics(
        self,
        current_data: Dict[str, Any],
        previous_day_summary: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate intraday performance metrics."""
        metrics = {}
        current_price = float(current_data.get('price', 0))
        open_price = float(current_data.get('open', 0))

        # Intraday change from open
        if open_price > 0:
            metrics['intraday_change_from_open'] = current_price - open_price
            metrics['intraday_change_from_open_percent'] = (
                (current_price - open_price) / open_price * 100
            )
        else:
            metrics['intraday_change_from_open'] = 0
            metrics['intraday_change_from_open_percent'] = 0

        # Gap analysis (if we have previous day data)
        if previous_day_summary:
            prev_close = float(previous_day_summary.get('close', 0))
            if prev_close > 0:
                gap = open_price - prev_close
                gap_percent = (gap / prev_close) * 100
                metrics['gap'] = gap
                metrics['gap_percent'] = gap_percent
                metrics['gap_type'] = 'gap_up' if gap > 0 else 'gap_down' if gap < 0 else 'no_gap'

                # Compare to previous day's high/low
                prev_high = float(previous_day_summary.get('high', 0))
                prev_low = float(previous_day_summary.get('low', 0))

                if prev_high > 0 and current_price > prev_high:
                    metrics['breakout_above_prev_high'] = True
                    metrics['breakout_percent'] = ((current_price - prev_high) / prev_high) * 100
                elif prev_low > 0 and current_price < prev_low:
                    metrics['breakdown_below_prev_low'] = True
                    metrics['breakdown_percent'] = ((prev_low - current_price) / prev_low) * 100

        return metrics

    def _calculate_time_window_analytics(
        self,
        current_price: float,
        time_window_data: Dict[int, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Calculate analytics for different time windows."""
        analytics = {}

        for window_minutes, data_points in time_window_data.items():
            if not data_points:
                continue

            prices = [float(dp.get('current_price', 0)) for dp in data_points if 'current_price' in dp]
            if not prices:
                continue

            # Calculate change from window start
            window_start_price = prices[0]
            if window_start_price > 0:
                change = current_price - window_start_price
                change_percent = (change / window_start_price) * 100

                analytics[f'change_{window_minutes}min'] = change
                analytics[f'change_{window_minutes}min_percent'] = change_percent

            # Calculate high/low within window
            analytics[f'high_{window_minutes}min'] = max(prices)
            analytics[f'low_{window_minutes}min'] = min(prices)
            analytics[f'range_{window_minutes}min'] = max(prices) - min(prices)

            # Volume (number of updates) in window
            analytics[f'volume_{window_minutes}min'] = len(data_points)

        return analytics

    def _calculate_moving_averages(
        self,
        time_window_data: Dict[int, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Calculate moving averages for configured windows."""
        ma_analytics = {}

        for ma_window in self.ma_windows_minutes:
            if ma_window in time_window_data:
                data_points = time_window_data[ma_window]
                if data_points:
                    prices = [float(dp.get('current_price', 0)) for dp in data_points if 'current_price' in dp]
                    if prices:
                        ma_analytics[f'ma_{ma_window}min'] = statistics.mean(prices)

        return ma_analytics

    def _calculate_volatility_and_momentum(
        self,
        time_window_data: Dict[int, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Calculate volatility and momentum indicators."""
        metrics = {}

        # Use 15-minute window for volatility calculation (or largest available)
        volatility_window = 15
        available_windows = sorted([w for w in time_window_data.keys() if time_window_data[w]])

        if not available_windows:
            return metrics

        # Use 15-min window if available, otherwise use largest window
        if volatility_window not in available_windows:
            volatility_window = available_windows[-1]

        data_points = time_window_data[volatility_window]
        if len(data_points) < 2:
            return metrics

        prices = [float(dp.get('current_price', 0)) for dp in data_points if 'current_price' in dp]
        if len(prices) < 2:
            return metrics

        # Volatility (standard deviation of returns)
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

        if returns:
            volatility = statistics.stdev(returns) if len(returns) > 1 else 0
            metrics['volatility'] = volatility
            metrics['volatility_annualized'] = volatility * (252 ** 0.5)  # Approximate annualization

        # Momentum (rate of change)
        if len(prices) >= 2 and prices[0] != 0:
            momentum = (prices[-1] - prices[0]) / prices[0]
            metrics['momentum'] = momentum

            # Price velocity (acceleration)
            if len(prices) >= 3:
                mid_point = len(prices) // 2
                first_half_change = (prices[mid_point] - prices[0]) / prices[0] if prices[0] != 0 else 0
                second_half_change = (prices[-1] - prices[mid_point]) / prices[mid_point] if prices[mid_point] != 0 else 0
                acceleration = second_half_change - first_half_change
                metrics['price_acceleration'] = acceleration

        return metrics

    def _generate_trading_signal(
        self,
        analytics: Dict[str, Any],
        volatility_metrics: Dict[str, Any],
        ma_analytics: Dict[str, Any]
    ) -> TradingSignal:
        """
        Generate trading signal based on analytics.

        Strategy:
        - BUY: Strong upward momentum + low/normal volatility + price below recent MA
        - SELL: Downward momentum + high volatility + price above recent MA
        - HOLD: Everything else
        """
        current_price = analytics.get('current_price', 0)
        momentum = volatility_metrics.get('momentum', 0)
        volatility = volatility_metrics.get('volatility', 0)
        acceleration = volatility_metrics.get('price_acceleration', 0)

        # Check if we have moving averages
        ma_5min = ma_analytics.get('ma_5min')
        ma_15min = ma_analytics.get('ma_15min')

        # BUY Signal Conditions
        buy_conditions = [
            momentum > self.momentum_threshold,  # Positive momentum
            volatility < self.volatility_threshold,  # Low volatility
        ]

        # Additional buy condition: price below moving average (potential bounce)
        if ma_15min and current_price < ma_15min:
            buy_conditions.append(True)

        # Strong buy if acceleration is positive
        if acceleration and acceleration > 0:
            buy_conditions.append(True)

        # SELL Signal Conditions
        sell_conditions = [
            momentum < -self.momentum_threshold,  # Negative momentum
            volatility > self.volatility_threshold,  # High volatility
        ]

        # Additional sell condition: price above moving average (potential reversal)
        if ma_15min and current_price > ma_15min * 1.02:  # 2% above MA
            sell_conditions.append(True)

        # Strong sell if acceleration is negative
        if acceleration and acceleration < 0:
            sell_conditions.append(True)

        # Generate signal
        if sum(buy_conditions) >= 3:
            return TradingSignal.BUY
        elif sum(sell_conditions) >= 3:
            return TradingSignal.SELL
        else:
            return TradingSignal.HOLD

    def _get_signal_reason(
        self,
        analytics: Dict[str, Any],
        volatility_metrics: Dict[str, Any],
        ma_analytics: Dict[str, Any],
        signal: TradingSignal
    ) -> str:
        """Generate human-readable reason for the trading signal."""
        momentum = volatility_metrics.get('momentum', 0)
        volatility = volatility_metrics.get('volatility', 0)
        current_price = analytics.get('current_price', 0)
        ma_15min = ma_analytics.get('ma_15min')

        reasons = []

        if signal == TradingSignal.BUY:
            reasons.append(f"Positive momentum ({momentum:.4f})")
            if volatility < self.volatility_threshold:
                reasons.append(f"Low volatility ({volatility:.4f})")
            if ma_15min and current_price < ma_15min:
                reasons.append(f"Price below 15min MA (potential bounce)")

        elif signal == TradingSignal.SELL:
            reasons.append(f"Negative momentum ({momentum:.4f})")
            if volatility > self.volatility_threshold:
                reasons.append(f"High volatility ({volatility:.4f})")
            if ma_15min and current_price > ma_15min:
                reasons.append(f"Price above 15min MA (potential reversal)")

        else:  # HOLD
            reasons.append("Stable price action within normal parameters")

        return "; ".join(reasons) if reasons else "Normal trading conditions"
