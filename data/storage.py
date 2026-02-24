"""
SQLite storage layer for market data, quotes, indicators, and trade history.

This module provides:
- Database connection management
- Schema migrations
- CRUD operations for all tables
- Batch insert optimization
- Query helpers for common operations
"""

import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from contextlib import contextmanager
from loguru import logger

from datetime import datetime
from decimal import Decimal

from data.models import OHLCV, Quote, MarketDataInterval


class DatabaseError(Exception):
    """Raised when database operations fail"""
    pass


class DataStore:
    """
    SQLite data store for market data with migration support.
    
    Features:
    - Automatic schema migrations
    - Connection pooling with context managers
    - Batch insert optimization
    - Query result caching
    - Data validation
    """
    
    def __init__(self, db_path: str = "data_cache/market_data.db"):
        """
        Initialize data store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database with schema
        self._init_db()
        logger.info(f"DataStore initialized: {self.db_path}")
    
    def _init_db(self):
        """Initialize database with schema migrations"""
        try:
            with self.get_connection() as conn:
                # Run initial migration
                migration_path = Path(__file__).parent / "migrations" / "001_initial.sql"
                
                if not migration_path.exists():
                    raise DatabaseError(f"Migration file not found: {migration_path}")
                
                migration_sql = migration_path.read_text()
                conn.executescript(migration_sql)
                conn.commit()
                
                # Check migration status
                cursor = conn.execute(
                    "SELECT version, name, applied_at FROM schema_migrations ORDER BY version"
                )
                migrations = cursor.fetchall()
                
                logger.info(f"Database initialized with {len(migrations)} migration(s)")
                for version, name, applied_at in migrations:
                    logger.debug(f"  Migration {version}: {name} (applied at {applied_at})")
                    
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database: {e}") from e
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
            
        Example:
            with store.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM bars")
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database error: {e}") from e
        finally:
            if conn:
                conn.close()
    
    # ========================================================================
    # BARS (OHLCV) Operations
    # ========================================================================
    
    def insert_bars(self, bars: List[OHLCV], timeframe: Optional[str] = None) -> int:
        """
        Insert multiple OHLCV bars (batch insert for performance).
        
        Args:
            bars: List of OHLCV objects
            timeframe: Timeframe string ('1d', '1h', '5m', etc.). If None, uses bar.interval
            
        Returns:
            Number of rows inserted
            
        Note:
            Uses INSERT OR IGNORE to skip duplicates
        """
        if not bars:
            return 0
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Batch insert with OR IGNORE for duplicates
                cursor.executemany(
                    """
                    INSERT OR IGNORE INTO bars 
                    (symbol, timestamp, timeframe, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            bar.symbol,
                            int(bar.timestamp.timestamp()),  # Convert datetime to unix timestamp
                            timeframe or bar.interval.value,  # Use provided or default to bar's interval
                            float(bar.open),  # Convert Decimal to float
                            float(bar.high),
                            float(bar.low),
                            float(bar.close),
                            bar.volume
                        )
                        for bar in bars
                    ]
                )
                
                conn.commit()
                inserted = cursor.rowcount
                
                logger.debug(
                    f"Inserted {inserted}/{len(bars)} bars for "
                    f"{bars[0].symbol if bars else 'unknown'} ({timeframe or 'auto'})"
                )
                
                return inserted
                
        except Exception as e:
            raise DatabaseError(f"Failed to insert bars: {e}") from e
    
    def get_bars(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[OHLCV]:
        """
        Retrieve OHLCV bars for a symbol.
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe string
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
            limit: Maximum number of bars to return
            
        Returns:
            List of OHLCV objects, sorted by timestamp ascending
        """
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT symbol, timestamp, open, high, low, close, volume
                    FROM bars
                    WHERE symbol = ? AND timeframe = ?
                """
                params: List[Any] = [symbol, timeframe]
                
                if start_time is not None:
                    query += " AND timestamp >= ?"
                    params.append(start_time)
                
                if end_time is not None:
                    query += " AND timestamp <= ?"
                    params.append(end_time)
                
                query += " ORDER BY timestamp ASC"
                
                if limit is not None:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                bars = [
                    OHLCV(
                        symbol=row["symbol"],
                        timestamp=datetime.fromtimestamp(row["timestamp"]),
                        open=Decimal(str(row["open"])),
                        high=Decimal(str(row["high"])),
                        low=Decimal(str(row["low"])),
                        close=Decimal(str(row["close"])),
                        volume=row["volume"],
                        interval=MarketDataInterval(timeframe) if timeframe in ["1min", "5min", "15min", "30min", "1hour", "1day"] else MarketDataInterval.DAY_1
                    )
                    for row in rows
                ]
                
                logger.debug(f"Retrieved {len(bars)} bars for {symbol} ({timeframe})")
                return bars
                
        except Exception as e:
            raise DatabaseError(f"Failed to get bars: {e}") from e
    
    def get_latest_bar(self, symbol: str, timeframe: str = "1d") -> Optional[OHLCV]:
        """
        Get the most recent bar for a symbol.
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe string
            
        Returns:
            Latest OHLCV bar or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT symbol, timestamp, open, high, low, close, volume
                    FROM bars
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (symbol, timeframe)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return OHLCV(
                    symbol=row["symbol"],
                    timestamp=datetime.fromtimestamp(row["timestamp"]),
                    open=Decimal(str(row["open"])),
                    high=Decimal(str(row["high"])),
                    low=Decimal(str(row["low"])),
                    close=Decimal(str(row["close"])),
                    volume=row["volume"],
                    interval=MarketDataInterval(timeframe) if timeframe in ["1min", "5min", "15min", "30min", "1hour", "1day"] else MarketDataInterval.DAY_1
                )
                
        except Exception as e:
            raise DatabaseError(f"Failed to get latest bar: {e}") from e
    
    # ========================================================================
    # QUOTES Operations
    # ========================================================================
    
    def insert_quote(self, quote: Quote) -> Optional[int]:
        """
        Insert a single quote.
        
        Args:
            quote: Quote object
            
        Returns:
            Row ID of inserted quote (or None if replace occurred)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT OR REPLACE INTO quotes
                    (symbol, timestamp, bid, ask, last, bid_size, ask_size, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        quote.symbol,
                        int(quote.timestamp.timestamp()),
                        float(quote.bid),
                        float(quote.ask),
                        float(quote.last),
                        quote.bid_size,
                        quote.ask_size,
                        quote.volume
                    )
                )
                conn.commit()
                
                logger.debug(f"Inserted quote for {quote.symbol} at {quote.timestamp}")
                return cursor.lastrowid
                
        except Exception as e:
            raise DatabaseError(f"Failed to insert quote: {e}") from e
    
    def get_latest_quote(self, symbol: str) -> Optional[Quote]:
        """
        Get the most recent quote for a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Latest Quote or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT symbol, timestamp, bid, ask, last, bid_size, ask_size, volume
                    FROM quotes
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (symbol,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return Quote(
                    symbol=row["symbol"],
                    timestamp=datetime.fromtimestamp(row["timestamp"]),
                    bid=Decimal(str(row["bid"])),
                    ask=Decimal(str(row["ask"])),
                    last=Decimal(str(row["last"])),
                    bid_size=row["bid_size"],
                    ask_size=row["ask_size"],
                    volume=row["volume"]
                )
                
        except Exception as e:
            raise DatabaseError(f"Failed to get latest quote: {e}") from e
    
    # ========================================================================
    # INDICATORS Operations
    # ========================================================================
    
    def insert_indicator(
        self,
        symbol: str,
        timestamp: int,
        timeframe: str,
        indicator_name: str,
        value: float,
        metadata: Optional[str] = None
    ) -> Optional[int]:
        """
        Insert or update an indicator value.
        
        Args:
            symbol: Stock symbol
            timestamp: Unix timestamp
            timeframe: Timeframe string
            indicator_name: Name of indicator ('vwap', 'rsi', 'atr')
            value: Indicator value
            metadata: Optional JSON metadata
            
        Returns:
            Row ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT OR REPLACE INTO indicators
                    (symbol, timestamp, timeframe, indicator_name, value, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (symbol, timestamp, timeframe, indicator_name, value, metadata)
                )
                conn.commit()
                
                logger.debug(
                    f"Inserted {indicator_name}={value} for {symbol} at {timestamp}"
                )
                return cursor.lastrowid
                
        except Exception as e:
            raise DatabaseError(f"Failed to insert indicator: {e}") from e
    
    def get_indicator(
        self,
        symbol: str,
        indicator_name: str,
        timeframe: str = "1d",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Tuple[int, float, Optional[str]]]:
        """
        Retrieve indicator values for a symbol.
        
        Args:
            symbol: Stock symbol
            indicator_name: Name of indicator
            timeframe: Timeframe string
            start_time: Start timestamp
            end_time: End timestamp
            
        Returns:
            List of (timestamp, value, metadata) tuples
        """
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT timestamp, value, metadata
                    FROM indicators
                    WHERE symbol = ? AND indicator_name = ? AND timeframe = ?
                """
                params: List[Any] = [symbol, indicator_name, timeframe]
                
                if start_time is not None:
                    query += " AND timestamp >= ?"
                    params.append(start_time)
                
                if end_time is not None:
                    query += " AND timestamp <= ?"
                    params.append(end_time)
                
                query += " ORDER BY timestamp ASC"
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [(row["timestamp"], row["value"], row["metadata"]) for row in rows]
                
        except Exception as e:
            raise DatabaseError(f"Failed to get indicator: {e}") from e
    
    # ========================================================================
    # TRADE_HISTORY Operations
    # ========================================================================
    
    def insert_trade(
        self,
        symbol: str,
        entry_time: int,
        entry_price: float,
        quantity: float,
        side: str,
        strategy: Optional[str] = None
    ) -> Optional[int]:
        """
        Insert a new trade (status='open').
        
        Args:
            symbol: Stock symbol
            entry_time: Entry timestamp
            entry_price: Entry price
            quantity: Number of shares
            side: 'long' or 'short'
            strategy: Strategy name
            
        Returns:
            Trade ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO trade_history
                    (symbol, entry_time, entry_price, quantity, side, status, strategy)
                    VALUES (?, ?, ?, ?, ?, 'open', ?)
                    """,
                    (symbol, entry_time, entry_price, quantity, side, strategy)
                )
                conn.commit()
                
                logger.info(
                    f"Trade opened: {side} {quantity} {symbol} @ {entry_price} "
                    f"(strategy: {strategy})"
                )
                return cursor.lastrowid
                
        except Exception as e:
            raise DatabaseError(f"Failed to insert trade: {e}") from e
    
    def close_trade(
        self,
        trade_id: int,
        exit_time: int,
        exit_price: float,
        notes: Optional[str] = None
    ):
        """
        Close a trade and calculate PnL.
        
        Args:
            trade_id: Trade ID
            exit_time: Exit timestamp
            exit_price: Exit price
            notes: Optional notes
        """
        try:
            with self.get_connection() as conn:
                # Get entry info
                cursor = conn.execute(
                    "SELECT entry_price, quantity, side FROM trade_history WHERE id = ?",
                    (trade_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    raise DatabaseError(f"Trade {trade_id} not found")
                
                entry_price = row["entry_price"]
                quantity = row["quantity"]
                side = row["side"]
                
                # Calculate PnL
                if side == "long":
                    pnl = (exit_price - entry_price) * quantity
                else:  # short
                    pnl = (entry_price - exit_price) * quantity
                
                pnl_percent = (pnl / (entry_price * quantity)) * 100
                
                # Update trade
                conn.execute(
                    """
                    UPDATE trade_history
                    SET exit_time = ?, exit_price = ?, pnl = ?, pnl_percent = ?,
                        status = 'closed', notes = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (exit_time, exit_price, pnl, pnl_percent, notes, int(time.time()), trade_id)
                )
                conn.commit()
                
                logger.info(
                    f"Trade {trade_id} closed: PnL=${pnl:.2f} ({pnl_percent:.2f}%)"
                )
                
        except Exception as e:
            raise DatabaseError(f"Failed to close trade: {e}") from e
    
    def get_trade_history(
        self,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve trade history with filters.
        
        Args:
            symbol: Filter by symbol
            status: Filter by status ('open', 'closed', 'cancelled')
            strategy: Filter by strategy name
            limit: Maximum number of trades
            
        Returns:
            List of trade dictionaries
        """
        try:
            with self.get_connection() as conn:
                query = "SELECT * FROM trade_history WHERE 1=1"
                params: List[Any] = []
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                if status:
                    query += " AND status = ?"
                    params.append(status)
                
                if strategy:
                    query += " AND strategy = ?"
                    params.append(strategy)
                
                query += " ORDER BY entry_time DESC"
                
                if limit:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            raise DatabaseError(f"Failed to get trade history: {e}") from e
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with table row counts
        """
        try:
            with self.get_connection() as conn:
                stats = {}
                
                for table in ["bars", "quotes", "indicators", "trade_history"]:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[table] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            raise DatabaseError(f"Failed to get stats: {e}") from e
    
    def vacuum(self):
        """Optimize database (reclaim space, rebuild indexes)"""
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("Database vacuumed successfully")
        except Exception as e:
            raise DatabaseError(f"Failed to vacuum database: {e}") from e
