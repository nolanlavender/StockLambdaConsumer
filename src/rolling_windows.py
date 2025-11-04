"""In-memory rolling window manager for stock data."""
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger(__name__)


class RollingWindow:
    """Manages a single rolling time window for stock data."""

    def __init__(self, window_minutes: int):
        """
        Initialize a rolling window.

        Args:
            window_minutes: Size of the window in minutes
        """
        self.window_minutes = window_minutes
        self.window_seconds = window_minutes * 60
        self.data = deque()

    def add(self, data_point: Dict[str, Any]) -> None:
        """
        Add a data point to the window.

        Args:
            data_point: Stock data point with 'timestamp' field
        """
        self.data.append(data_point)
        self._evict_old_data()

    def _evict_old_data(self) -> None:
        """Remove data points older than the window size."""
        if not self.data:
            return

        # Get the newest timestamp
        try:
            newest = datetime.fromisoformat(
                self.data[-1]['timestamp'].replace('Z', '+00:00')
            )
        except (KeyError, ValueError) as e:
            logger.warning(f"Could not parse timestamp for eviction: {e}")
            return

        cutoff = newest - timedelta(seconds=self.window_seconds)

        # Remove old data from the left
        while self.data:
            try:
                oldest = datetime.fromisoformat(
                    self.data[0]['timestamp'].replace('Z', '+00:00')
                )
                if oldest < cutoff:
                    self.data.popleft()
                else:
                    break
            except (KeyError, ValueError) as e:
                logger.warning(f"Could not parse timestamp, removing bad data: {e}")
                self.data.popleft()

    def get_data(self) -> List[Dict[str, Any]]:
        """
        Get all data points in the current window.

        Returns:
            List of data points
        """
        self._evict_old_data()  # Clean up before returning
        return list(self.data)

    def size(self) -> int:
        """Get the number of data points in the window."""
        return len(self.data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the window to a dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'window_minutes': self.window_minutes,
            'data': list(self.data)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RollingWindow':
        """
        Deserialize a window from a dictionary.

        Args:
            data: Dictionary representation

        Returns:
            RollingWindow instance
        """
        window = cls(data['window_minutes'])
        window.data = deque(data['data'])
        window._evict_old_data()  # Clean up old data on restore
        return window


class SymbolWindowManager:
    """Manages all rolling windows for a single stock symbol."""

    def __init__(self, symbol: str, window_sizes: List[int]):
        """
        Initialize window manager for a symbol.

        Args:
            symbol: Stock symbol
            window_sizes: List of window sizes in minutes
        """
        self.symbol = symbol
        self.windows = {
            size: RollingWindow(size) for size in window_sizes
        }

    def add(self, data_point: Dict[str, Any]) -> None:
        """
        Add a data point to all windows.

        Args:
            data_point: Stock data point
        """
        for window in self.windows.values():
            window.add(data_point)

    def get_window_data(self, window_minutes: int) -> List[Dict[str, Any]]:
        """
        Get data for a specific window.

        Args:
            window_minutes: Window size in minutes

        Returns:
            List of data points in the window
        """
        if window_minutes not in self.windows:
            logger.warning(
                f"Window {window_minutes}min not found for {self.symbol}"
            )
            return []
        return self.windows[window_minutes].get_data()

    def get_all_window_data(self) -> Dict[int, List[Dict[str, Any]]]:
        """
        Get data for all windows.

        Returns:
            Dictionary mapping window size to data points
        """
        return {
            size: window.get_data()
            for size, window in self.windows.items()
        }

    def get_stats(self) -> Dict[int, int]:
        """
        Get statistics for all windows.

        Returns:
            Dictionary mapping window size to number of data points
        """
        return {
            size: window.size()
            for size, window in self.windows.items()
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the manager to a dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'symbol': self.symbol,
            'windows': {
                size: window.to_dict()
                for size, window in self.windows.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SymbolWindowManager':
        """
        Deserialize a manager from a dictionary.

        Args:
            data: Dictionary representation

        Returns:
            SymbolWindowManager instance
        """
        window_sizes = [int(size) for size in data['windows'].keys()]
        manager = cls(data['symbol'], window_sizes)

        for size_str, window_data in data['windows'].items():
            size = int(size_str)
            manager.windows[size] = RollingWindow.from_dict(window_data)

        return manager


class RollingWindowStore:
    """Global store for all symbol window managers."""

    def __init__(self, window_sizes: List[int]):
        """
        Initialize the store.

        Args:
            window_sizes: List of window sizes in minutes
        """
        self.window_sizes = window_sizes
        self.managers: Dict[str, SymbolWindowManager] = {}

    def get_manager(self, symbol: str) -> SymbolWindowManager:
        """
        Get or create a window manager for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            SymbolWindowManager instance
        """
        if symbol not in self.managers:
            self.managers[symbol] = SymbolWindowManager(symbol, self.window_sizes)
        return self.managers[symbol]

    def add_data_point(self, symbol: str, data_point: Dict[str, Any]) -> None:
        """
        Add a data point for a symbol.

        Args:
            symbol: Stock symbol
            data_point: Stock data point
        """
        manager = self.get_manager(symbol)
        manager.add(data_point)

    def get_window_data(
        self,
        symbol: str,
        window_minutes: int
    ) -> List[Dict[str, Any]]:
        """
        Get window data for a symbol.

        Args:
            symbol: Stock symbol
            window_minutes: Window size in minutes

        Returns:
            List of data points in the window
        """
        if symbol not in self.managers:
            return []
        return self.managers[symbol].get_window_data(window_minutes)

    def get_all_window_data(
        self,
        symbol: str
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Get all window data for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary mapping window size to data points
        """
        if symbol not in self.managers:
            return {size: [] for size in self.window_sizes}
        return self.managers[symbol].get_all_window_data()

    def get_all_stats(self) -> Dict[str, Dict[int, int]]:
        """
        Get statistics for all symbols.

        Returns:
            Dictionary mapping symbol to window stats
        """
        return {
            symbol: manager.get_stats()
            for symbol, manager in self.managers.items()
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the entire store to a dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'window_sizes': self.window_sizes,
            'managers': {
                symbol: manager.to_dict()
                for symbol, manager in self.managers.items()
            }
        }

    def to_json(self) -> str:
        """
        Serialize the entire store to JSON.

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RollingWindowStore':
        """
        Deserialize a store from a dictionary.

        Args:
            data: Dictionary representation

        Returns:
            RollingWindowStore instance
        """
        store = cls(data['window_sizes'])

        for symbol, manager_data in data['managers'].items():
            store.managers[symbol] = SymbolWindowManager.from_dict(manager_data)

        return store

    @classmethod
    def from_json(cls, json_str: str) -> 'RollingWindowStore':
        """
        Deserialize a store from JSON.

        Args:
            json_str: JSON string

        Returns:
            RollingWindowStore instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)
