"""
Multi-source data fetching with automatic fallback.

Supports:
- moomoo OpenAPI (primary, requires credentials)
- yfinance (fallback, free historical data)
- Automatic fallback on errors
- Rate limiting
- Retry logic with exponential backoff
"""

import time
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger

try:
    import yfinance as yf
except ImportError:
    yf = None
    logger.warning("yfinance not installed - fallback data source unavailable")

from data.models import OHLCV, Quote, MarketDataInterval
from data.storage import DataStore
from decimal import Decimal

try:
    from connectors.opend import OpenDConnection
except ImportError:
    OpenDConnection = None  # Optional - only needed if using moomoo


class RateLimiter:
    """
    Token bucket rate limiter.
    
    Ensures we don't exceed API rate limits (e.g., 60 requests/minute)
    """
    
    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.capacity = requests_per_minute
        self.tokens = requests_per_minute
        self.refill_rate = requests_per_minute / 60.0  # Tokens per second
        self.last_refill = time.time()
    
    async def acquire(self):
        """Wait until a token is available, then consume it"""
        while self.tokens < 1:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.refill_rate
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        self.tokens -= 1


class DataSource(ABC):
    """Abstract base class for data sources"""
    
    @abstractmethod
    async def fetch_daily_bars(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[OHLCV]:
        """
        Fetch daily OHLCV bars.
        
        Args:
            symbol: Stock symbol
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of OHLCV bars
        """
        pass
    
    @abstractmethod
    async def fetch_intraday_bars(
        self,
        symbol: str,
        interval: MarketDataInterval,
        lookback_days: int = 5
    ) -> List[OHLCV]:
        """
        Fetch intraday OHLCV bars.
        
        Args:
            symbol: Stock symbol
            interval: Bar interval (1min, 5min, etc.)
            lookback_days: Number of days to look back
            
        Returns:
            List of OHLCV bars
        """
        pass
    
    @abstractmethod
    async def get_latest_quote(self, symbol: str) -> Optional[Quote]:
        """
        Get current real-time quote.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Latest quote or None if unavailable
        """
        pass


class MoomooDataSource(DataSource):
    """
    Primary data source using moomoo OpenAPI.
    
    Features:
    - Real-time quotes
    - Historical daily and intraday data
    - Requires valid credentials
    """
    
    def __init__(self, opend_connection: "OpenDConnection", rate_limiter: RateLimiter):
        """
        Initialize moomoo data source.
        
        Args:
            opend_wrapper: Configured OpenD connection
            rate_limiter: Rate limiter instance
        """
        self.opend = opend_connection
        self.rate_limiter = rate_limiter
        logger.info("MoomooDataSource initialized")
    
    async def fetch_daily_bars(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[OHLCV]:
        """Fetch daily bars from moomoo API"""
        await self.rate_limiter.acquire()
        
        # TODO: Implement actual moomoo API call
        # For now, return empty list (will be implemented when testing with real API)
        logger.warning(f"moomoo fetch_daily_bars not yet implemented for {symbol}")
        raise NotImplementedError("moomoo daily bars fetch coming in next iteration")
    
    async def fetch_intraday_bars(
        self,
        symbol: str,
        interval: MarketDataInterval,
        lookback_days: int = 5
    ) -> List[OHLCV]:
        """Fetch intraday bars from moomoo API"""
        await self.rate_limiter.acquire()
        
        # TODO: Implement actual moomoo API call
        logger.warning(f"moomoo fetch_intraday_bars not yet implemented for {symbol}")
        raise NotImplementedError("moomoo intraday bars fetch coming in next iteration")
    
    async def get_latest_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote from moomoo"""
        await self.rate_limiter.acquire()
        
        # TODO: Implement actual moomoo API call
        logger.warning(f"moomoo get_latest_quote not yet implemented for {symbol}")
        raise NotImplementedError("moomoo quote fetch coming in next iteration")


class YFinanceDataSource(DataSource):
    """
    Fallback data source using yfinance (free Yahoo Finance data).
    
    Features:
    - Free historical data
    - No API key required
    - Limited to historical data (no real-time quotes)
    - Good for backtesting
    """
    
    def __init__(self, rate_limiter: RateLimiter):
        """
        Initialize yfinance data source.
        
        Args:
            rate_limiter: Rate limiter instance
        """
        if yf is None:
            raise RuntimeError("yfinance not installed - run: pip install yfinance")
        
        self.rate_limiter = rate_limiter
        logger.info("YFinanceDataSource initialized")
    
    async def fetch_daily_bars(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[OHLCV]:
        """
        Fetch daily bars from Yahoo Finance.
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            List of OHLCV bars
        """
        await self.rate_limiter.acquire()
        
        try:
            logger.debug(f"Fetching {symbol} daily bars from yfinance: {start_date} to {end_date}")
            
            # Download data using yfinance
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date,
                end=end_date + timedelta(days=1),  # yfinance end is exclusive
                interval="1d"
            )
            
            if df.empty:
                logger.warning(f"No data returned from yfinance for {symbol}")
                return []
            
            # Convert to OHLCV objects
            bars = []
            for timestamp, row in df.iterrows():
                bars.append(
                    OHLCV(
                        symbol=symbol,
                        timestamp=timestamp.to_pydatetime(),
                        open=Decimal(str(row["Open"])),
                        high=Decimal(str(row["High"])),
                        low=Decimal(str(row["Low"])),
                        close=Decimal(str(row["Close"])),
                        volume=int(row["Volume"]),
                        interval=MarketDataInterval.DAY_1
                    )
                )
            
            logger.info(f"Fetched {len(bars)} daily bars for {symbol} from yfinance")
            return bars
            
        except Exception as e:
            logger.error(f"yfinance fetch_daily_bars failed for {symbol}: {e}")
            raise
    
    async def fetch_intraday_bars(
        self,
        symbol: str,
        interval: MarketDataInterval,
        lookback_days: int = 5
    ) -> List[OHLCV]:
        """
        Fetch intraday bars from Yahoo Finance.
        
        Args:
            symbol: Stock symbol
            interval: Bar interval
            lookback_days: Number of days to look back
            
        Returns:
            List of OHLCV bars
            
        Note:
            yfinance intraday data is limited to last 60 days
        """
        await self.rate_limiter.acquire()
        
        try:
            # Map our interval to yfinance interval
            interval_map = {
                MarketDataInterval.MIN_1: "1m",
                MarketDataInterval.MIN_5: "5m",
                MarketDataInterval.MIN_15: "15m",
                MarketDataInterval.MIN_30: "30m",
                MarketDataInterval.HOUR_1: "1h",
            }
            
            yf_interval = interval_map.get(interval)
            if not yf_interval:
                raise ValueError(f"Unsupported intraday interval: {interval}")
            
            # yfinance limits intraday data to last 60 days
            lookback_days = min(lookback_days, 60)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)
            
            logger.debug(
                f"Fetching {symbol} {yf_interval} bars from yfinance: "
                f"{start_date} to {end_date}"
            )
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=yf_interval
            )
            
            if df.empty:
                logger.warning(f"No intraday data returned from yfinance for {symbol}")
                return []
            
            # Convert to OHLCV objects
            bars = []
            for timestamp, row in df.iterrows():
                bars.append(
                    OHLCV(
                        symbol=symbol,
                        timestamp=timestamp.to_pydatetime(),
                        open=Decimal(str(row["Open"])),
                        high=Decimal(str(row["High"])),
                        low=Decimal(str(row["Low"])),
                        close=Decimal(str(row["Close"])),
                        volume=int(row["Volume"]),
                        interval=interval
                    )
                )
            
            logger.info(
                f"Fetched {len(bars)} {interval.value} bars for {symbol} from yfinance"
            )
            return bars
            
        except Exception as e:
            logger.error(f"yfinance fetch_intraday_bars failed for {symbol}: {e}")
            raise
    
    async def get_latest_quote(self, symbol: str) -> Optional[Quote]:
        """
        Get latest quote from Yahoo Finance.
        
        Note:
            yfinance doesn't provide real-time quotes. This returns
            the latest available price, which may be delayed 15-20 minutes.
        """
        await self.rate_limiter.acquire()
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                return None
            
            # yfinance provides delayed quotes, not real-time
            return Quote(
                symbol=symbol,
                timestamp=datetime.now(),  # Approximate
                bid=Decimal(str(info.get("bid", 0))),
                ask=Decimal(str(info.get("ask", 0))),
                last=Decimal(str(info.get("currentPrice", info.get("regularMarketPrice", 0)))),
                bid_size=info.get("bidSize", 0),
                ask_size=info.get("askSize", 0),
                volume=info.get("volume", 0)
            )
            
        except Exception as e:
            logger.error(f"yfinance get_latest_quote failed for {symbol}: {e}")
            return None


class HybridDataFetcher:
    """
    Multi-source data fetcher with automatic fallback.
    
    Tries primary source (moomoo) first, falls back to yfinance on failure.
    """
    
    def __init__(
        self,
        primary: Optional[DataSource] = None,
        fallback: Optional[DataSource] = None,
        storage: Optional[DataStore] = None,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 2.0
    ):
        """
        Initialize hybrid fetcher.
        
        Args:
            primary: Primary data source (moomoo)
            fallback: Fallback data source (yfinance)
            storage: DataStore for caching
            retry_attempts: Number of retry attempts
            retry_backoff_seconds: Base backoff delay (exponential)
        """
        self.primary = primary
        self.fallback = fallback
        self.storage = storage
        self.retry_attempts = retry_attempts
        self.retry_backoff = retry_backoff_seconds
        
        logger.info(
            f"HybridDataFetcher initialized: "
            f"primary={'moomoo' if primary else 'none'}, "
            f"fallback={'yfinance' if fallback else 'none'}"
        )
    
    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    raise  # Last attempt, re-raise
                
                wait_time = self.retry_backoff * (2 ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1}/{self.retry_attempts} failed: {e}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
    
    async def fetch_daily_bars(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        force_fallback: bool = False
    ) -> List[OHLCV]:
        """
        Fetch daily bars with automatic fallback.
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            force_fallback: Skip primary and use fallback
            
        Returns:
            List of OHLCV bars
        """
        # Try primary source first (unless forced)
        if self.primary and not force_fallback:
            try:
                bars = await self._retry_with_backoff(
                    self.primary.fetch_daily_bars,
                    symbol, start_date, end_date
                )
                
                # Store in database if available
                if self.storage and bars:
                    self.storage.insert_bars(bars, "1day")
                
                logger.info(f"Fetched {len(bars)} daily bars from primary source")
                return bars
                
            except Exception as e:
                logger.warning(f"Primary source failed: {e}")
                if not self.fallback:
                    raise
                logger.info("Trying fallback source...")
        
        # Try fallback source
        if self.fallback:
            try:
                bars = await self._retry_with_backoff(
                    self.fallback.fetch_daily_bars,
                    symbol, start_date, end_date
                )
                
                # Store in database if available
                if self.storage and bars:
                    self.storage.insert_bars(bars, "1day")
                
                logger.info(f"Fetched {len(bars)} daily bars from fallback source")
                return bars
                
            except Exception as e:
                logger.error(f"Fallback source also failed: {e}")
                raise
        
        raise RuntimeError("No data sources available")
    
    async def fetch_intraday_bars(
        self,
        symbol: str,
        interval: MarketDataInterval,
        lookback_days: int = 5,
        force_fallback: bool = False
    ) -> List[OHLCV]:
        """
        Fetch intraday bars with automatic fallback.
        
        Args:
            symbol: Stock symbol
            interval: Bar interval
            lookback_days: Days to look back
            force_fallback: Skip primary and use fallback
            
        Returns:
            List of OHLCV bars
        """
        # Try primary source first
        if self.primary and not force_fallback:
            try:
                bars = await self._retry_with_backoff(
                    self.primary.fetch_intraday_bars,
                    symbol, interval, lookback_days
                )
                
                # Store in database
                if self.storage and bars:
                    self.storage.insert_bars(bars, interval.value)
                
                logger.info(f"Fetched {len(bars)} {interval.value} bars from primary source")
                return bars
                
            except Exception as e:
                logger.warning(f"Primary source failed: {e}")
                if not self.fallback:
                    raise
                logger.info("Trying fallback source...")
        
        # Try fallback source
        if self.fallback:
            try:
                bars = await self._retry_with_backoff(
                    self.fallback.fetch_intraday_bars,
                    symbol, interval, lookback_days
                )
                
                # Store in database
                if self.storage and bars:
                    self.storage.insert_bars(bars, interval.value)
                
                logger.info(f"Fetched {len(bars)} {interval.value} bars from fallback source")
                return bars
                
            except Exception as e:
                logger.error(f"Fallback source also failed: {e}")
                raise
        
        raise RuntimeError("No data sources available")
    
    async def get_latest_quote(self, symbol: str) -> Optional[Quote]:
        """
        Get latest quote (primary only, no fallback for real-time).
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Latest quote or None
        """
        if not self.primary:
            logger.warning("No primary source available for real-time quotes")
            return None
        
        try:
            quote = await self._retry_with_backoff(
                self.primary.get_latest_quote,
                symbol
            )
            
            # Store in database
            if self.storage and quote:
                self.storage.insert_quote(quote)
            
            return quote
            
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
