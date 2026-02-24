"""
Watchlist management for daily trading.

Two-tier approach:
1. Universe: Broad set of tradeable stocks (S&P 500 + momentum stocks)
2. Watchlist: Daily filtered list based on volume, liquidity, events
"""

from typing import List, Set, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, date
from loguru import logger


@dataclass
class UniverseConfig:
    """
    Configuration for stock universe.
    """
    include_sp500: bool = True
    include_nasdaq100: bool = False
    min_price: float = 5.0
    max_price: float = 1000.0
    min_avg_volume: int = 1_000_000  # 1M shares/day
    max_stocks: int = 500
    
    # Sector limits (% of watchlist)
    max_tech_pct: float = 0.30
    max_financial_pct: float = 0.30
    max_energy_pct: float = 0.20


@dataclass
class WatchlistFilters:
    """
    Daily filters for watchlist generation.
    """
    min_volume_ratio: float = 1.5  # Today vs 20-day avg
    max_spread_pct: float = 0.5  # Max bid-ask spread %
    avoid_earnings_days: int = 1  # Skip N days before/after earnings
    max_gap_pct: float = 5.0  # Skip if gap > 5%
    require_options: bool = False  # Must have liquid options


@dataclass
class WatchlistEntry:
    """
    Single entry in daily watchlist.
    """
    symbol: str
    name: str
    sector: str
    price: float
    volume: int
    avg_volume_20d: int
    volume_ratio: float
    spread_pct: float
    atr_pct: float
    days_to_earnings: Optional[int] = None
    options_available: bool = False
    
    def __str__(self):
        return (
            f"{self.symbol:6} | ${self.price:7.2f} | "
            f"Vol: {self.volume/1e6:5.1f}M ({self.volume_ratio:.1f}x) | "
            f"Spread: {self.spread_pct:.2%} | ATR: {self.atr_pct:.2%}"
        )


class WatchlistManager:
    """
    Manages stock universe and daily watchlist generation.
    """
    
    def __init__(
        self,
        universe_config: Optional[UniverseConfig] = None,
        watchlist_filters: Optional[WatchlistFilters] = None,
        custom_symbols: Optional[List[str]] = None
    ):
        """
        Initialize watchlist manager.
        
        Args:
            universe_config: Universe configuration (uses default if None)
            watchlist_filters: Daily filters (uses default if None)
            custom_symbols: Additional symbols to always include
        """
        self.universe_config = universe_config or UniverseConfig()
        self.filters = watchlist_filters or WatchlistFilters()
        self.custom_symbols = set(custom_symbols or [])
        
        # Cache
        self._universe: Optional[Set[str]] = None
        self._universe_updated: Optional[datetime] = None
        
        logger.info(
            f"WatchlistManager initialized: {len(self.custom_symbols)} custom symbols"
        )
    
    def get_universe(self, force_refresh: bool = False) -> Set[str]:
        """
        Get current stock universe (cached, refreshes weekly).
        
        Args:
            force_refresh: Force refresh even if cached
            
        Returns:
            Set of ticker symbols
        """
        # Check cache (refresh weekly)
        if not force_refresh and self._universe is not None:
            age = (datetime.now() - self._universe_updated).days
            if age < 7:
                logger.debug(f"Using cached universe ({age} days old)")
                return self._universe
        
        # Build fresh universe
        logger.info("Building stock universe...")
        universe = set()
        
        # Add S&P 500 (stub - would use real API)
        if self.universe_config.include_sp500:
            sp500 = self._get_sp500_symbols()
            universe.update(sp500)
            logger.info(f"Added {len(sp500)} S&P 500 symbols")
        
        # Add NASDAQ 100 (stub)
        if self.universe_config.include_nasdaq100:
            nasdaq100 = self._get_nasdaq100_symbols()
            universe.update(nasdaq100)
            logger.info(f"Added {len(nasdaq100)} NASDAQ 100 symbols")
        
        # Add custom symbols
        universe.update(self.custom_symbols)
        
        # Apply basic filters
        universe = self._filter_universe(universe)
        
        # Limit size
        if len(universe) > self.universe_config.max_stocks:
            universe = set(list(universe)[:self.universe_config.max_stocks])
        
        self._universe = universe
        self._universe_updated = datetime.now()
        
        logger.info(f"Universe built: {len(universe)} symbols")
        return universe
    
    def generate_watchlist(
        self,
        market_data: Dict[str, Dict],
        max_symbols: int = 20
    ) -> List[WatchlistEntry]:
        """
        Generate daily watchlist from universe.
        
        Args:
            market_data: Dict mapping symbol -> market data dict with:
                - price, volume, avg_volume_20d, spread_pct, atr_pct, etc.
            max_symbols: Max symbols in watchlist
            
        Returns:
            List of WatchlistEntry sorted by attractiveness
        """
        universe = self.get_universe()
        
        entries = []
        for symbol in universe:
            data = market_data.get(symbol)
            if not data:
                continue
            
            # Apply filters
            if not self._passes_filters(symbol, data):
                continue
            
            entry = WatchlistEntry(
                symbol=symbol,
                name=data.get('name', symbol),
                sector=data.get('sector', 'Unknown'),
                price=data['price'],
                volume=data['volume'],
                avg_volume_20d=data['avg_volume_20d'],
                volume_ratio=data['volume'] / data['avg_volume_20d'],
                spread_pct=data.get('spread_pct', 0),
                atr_pct=data.get('atr_pct', 0),
                days_to_earnings=data.get('days_to_earnings'),
                options_available=data.get('options_available', False)
            )
            entries.append(entry)
        
        # Sort by volume ratio (liquidity proxy)
        entries.sort(key=lambda e: e.volume_ratio, reverse=True)
        
        # Apply sector limits
        entries = self._apply_sector_limits(entries, max_symbols)
        
        logger.info(
            f"Watchlist generated: {len(entries)} symbols from {len(universe)} universe"
        )
        
        return entries[:max_symbols]
    
    def add_custom_symbol(self, symbol: str):
        """Add symbol to custom watchlist."""
        self.custom_symbols.add(symbol.upper())
        logger.info(f"Added {symbol} to custom symbols")
    
    def remove_custom_symbol(self, symbol: str):
        """Remove symbol from custom watchlist."""
        self.custom_symbols.discard(symbol.upper())
        logger.info(f"Removed {symbol} from custom symbols")
    
    def _get_sp500_symbols(self) -> Set[str]:
        """
        Get S&P 500 symbols (stub implementation).
        
        TODO: Integrate with real data source:
        - Wikipedia table scraping
        - Or use yfinance: pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        """
        # Stub: Return a few popular symbols for testing
        return {
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
            'BRK.B', 'JPM', 'JNJ', 'V', 'PG', 'UNH', 'MA', 'HD',
            'XOM', 'CVX', 'PFE', 'KO', 'PEP', 'ABBV', 'COST', 'WMT',
            'DIS', 'NFLX', 'ADBE', 'CRM', 'CSCO', 'INTC', 'AMD',
        }
    
    def _get_nasdaq100_symbols(self) -> Set[str]:
        """Get NASDAQ 100 symbols (stub)."""
        return {'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA'}
    
    def _filter_universe(self, symbols: Set[str]) -> Set[str]:
        """
        Apply basic filters to universe.
        
        TODO: Implement real filtering with market data
        """
        # Stub: Just return as-is for now
        return symbols
    
    def _passes_filters(self, symbol: str, data: Dict) -> bool:
        """
        Check if symbol passes daily filters.
        """
        # Custom symbols always pass
        if symbol in self.custom_symbols:
            return True
        
        # Volume filter
        volume_ratio = data['volume'] / data['avg_volume_20d']
        if volume_ratio < self.filters.min_volume_ratio:
            return False
        
        # Spread filter
        if data.get('spread_pct', 0) > self.filters.max_spread_pct:
            return False
        
        # Earnings filter
        if self.filters.avoid_earnings_days > 0:
            days_to_earnings = data.get('days_to_earnings')
            if days_to_earnings is not None:
                if abs(days_to_earnings) <= self.filters.avoid_earnings_days:
                    return False
        
        # Options filter
        if self.filters.require_options:
            if not data.get('options_available', False):
                return False
        
        return True
    
    def _apply_sector_limits(
        self,
        entries: List[WatchlistEntry],
        max_symbols: int
    ) -> List[WatchlistEntry]:
        """
        Apply sector concentration limits.
        """
        sector_counts: Dict[str, int] = {}
        filtered = []
        
        max_tech = int(max_symbols * self.universe_config.max_tech_pct)
        max_financial = int(max_symbols * self.universe_config.max_financial_pct)
        max_energy = int(max_symbols * self.universe_config.max_energy_pct)
        
        for entry in entries:
            sector = entry.sector
            count = sector_counts.get(sector, 0)
            
            # Check sector limits
            if sector == 'Technology' and count >= max_tech:
                continue
            elif sector == 'Financial' and count >= max_financial:
                continue
            elif sector == 'Energy' and count >= max_energy:
                continue
            
            filtered.append(entry)
            sector_counts[sector] = count + 1
        
        return filtered
