"""
Unit tests for data storage layer.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from decimal import Decimal

from data.storage import DataStore, DatabaseError
from data.models import OHLCV, Quote, MarketDataInterval


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = DataStore(str(db_path))
        yield store


@pytest.fixture
def sample_bars():
    """Sample OHLCV data"""
    return [
        OHLCV(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 1, 9, 30),
            open=Decimal("150.00"),
            high=Decimal("152.00"),
            low=Decimal("149.50"),
            close=Decimal("151.50"),
            volume=1000000,
            interval=MarketDataInterval.DAY_1
        ),
        OHLCV(
            symbol="AAPL",
            timestamp=datetime(2024, 1, 2, 9, 30),
            open=Decimal("151.50"),
            high=Decimal("153.00"),
            low=Decimal("151.00"),
            close=Decimal("152.50"),
            volume=1100000,
            interval=MarketDataInterval.DAY_1
        ),
    ]


@pytest.fixture
def sample_quote():
    """Sample quote data"""
    return Quote(
        symbol="AAPL",
        timestamp=datetime(2024, 1, 1, 10, 0),
        bid=Decimal("150.90"),
        ask=Decimal("151.00"),
        last=Decimal("150.95"),
        bid_size=100,
        ask_size=200,
        volume=50000
    )


class TestDataStore:
    """Test DataStore class"""
    
    def test_init_creates_database(self, temp_db):
        """Test database initialization"""
        assert temp_db.db_path.exists()
        
        # Check schema migrations
        with temp_db.get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row["name"] for row in cursor.fetchall()}
            
            expected_tables = {"bars", "quotes", "indicators", "trade_history", "schema_migrations"}
            assert expected_tables.issubset(tables)
    
    def test_insert_bars(self, temp_db, sample_bars):
        """Test inserting OHLCV bars"""
        inserted = temp_db.insert_bars(sample_bars)
        assert inserted == 2
        
        # Verify retrieval
        retrieved = temp_db.get_bars("AAPL", "1day")
        assert len(retrieved) == 2
        assert retrieved[0].symbol == "AAPL"
        assert retrieved[0].open == Decimal("150.00")
        assert retrieved[1].close == Decimal("152.50")
    
    def test_insert_bars_duplicate_ignored(self, temp_db, sample_bars):
        """Test that duplicate bars are ignored"""
        temp_db.insert_bars(sample_bars)
        inserted = temp_db.insert_bars(sample_bars)  # Insert again
        
        # Should insert 0 (duplicates ignored)
        assert inserted == 0
        
        # Should still only have 2 bars
        retrieved = temp_db.get_bars("AAPL", "1day")
        assert len(retrieved) == 2
    
    def test_get_bars_with_time_filter(self, temp_db, sample_bars):
        """Test retrieving bars with time range filter"""
        temp_db.insert_bars(sample_bars)
        
        # Get only first bar
        start_time = int(datetime(2024, 1, 1, 9, 30).timestamp())
        end_time = int(datetime(2024, 1, 1, 23, 59).timestamp())
        
        retrieved = temp_db.get_bars("AAPL", "1day", start_time=start_time, end_time=end_time)
        assert len(retrieved) == 1
        assert retrieved[0].timestamp.date() == datetime(2024, 1, 1).date()
    
    def test_get_bars_with_limit(self, temp_db, sample_bars):
        """Test retrieving bars with limit"""
        temp_db.insert_bars(sample_bars)
        
        retrieved = temp_db.get_bars("AAPL", "1day", limit=1)
        assert len(retrieved) == 1
    
    def test_get_latest_bar(self, temp_db, sample_bars):
        """Test getting latest bar"""
        temp_db.insert_bars(sample_bars)
        
        latest = temp_db.get_latest_bar("AAPL", "1day")
        assert latest is not None
        assert latest.timestamp.date() == datetime(2024, 1, 2).date()
        assert latest.close == Decimal("152.50")
    
    def test_insert_quote(self, temp_db, sample_quote):
        """Test inserting quote"""
        row_id = temp_db.insert_quote(sample_quote)
        assert row_id is not None
        
        # Retrieve and verify
        retrieved = temp_db.get_latest_quote("AAPL")
        assert retrieved is not None
        assert retrieved.symbol == "AAPL"
        assert retrieved.bid == Decimal("150.90")
        assert retrieved.ask == Decimal("151.00")
        assert retrieved.volume == 50000
    
    def test_get_latest_quote_not_found(self, temp_db):
        """Test getting quote for non-existent symbol"""
        quote = temp_db.get_latest_quote("NONEXISTENT")
        assert quote is None
    
    def test_insert_indicator(self, temp_db):
        """Test inserting indicator values"""
        timestamp = int(datetime(2024, 1, 1, 10, 0).timestamp())
        
        row_id = temp_db.insert_indicator(
            symbol="AAPL",
            timestamp=timestamp,
            timeframe="1day",
            indicator_name="rsi",
            value=65.5,
            metadata='{"period": 14}'
        )
        
        assert row_id is not None
        
        # Retrieve and verify
        indicators = temp_db.get_indicator("AAPL", "rsi", "1day")
        assert len(indicators) == 1
        assert indicators[0][1] == 65.5  # value
        assert indicators[0][2] == '{"period": 14}'  # metadata
    
    def test_insert_trade(self, temp_db):
        """Test inserting and closing a trade"""
        entry_time = int(datetime(2024, 1, 1, 10, 0).timestamp())
        
        # Insert trade
        trade_id = temp_db.insert_trade(
            symbol="AAPL",
            entry_time=entry_time,
            entry_price=150.00,
            quantity=10.0,
            side="long",
            strategy="test_strategy"
        )
        
        assert trade_id is not None
        
        # Close trade
        exit_time = int(datetime(2024, 1, 1, 15, 0).timestamp())
        temp_db.close_trade(
            trade_id=trade_id,
            exit_time=exit_time,
            exit_price=155.00,
            notes="Test trade"
        )
        
        # Retrieve and verify PnL
        trades = temp_db.get_trade_history(symbol="AAPL", status="closed")
        assert len(trades) == 1
        
        trade = trades[0]
        assert trade["symbol"] == "AAPL"
        assert trade["entry_price"] == 150.00
        assert trade["exit_price"] == 155.00
        assert trade["pnl"] == 50.0  # (155 - 150) * 10
        assert abs(trade["pnl_percent"] - 3.33) < 0.01  # ~3.33%
        assert trade["status"] == "closed"
    
    def test_get_trade_history_filters(self, temp_db):
        """Test trade history filtering"""
        entry_time = int(datetime(2024, 1, 1, 10, 0).timestamp())
        
        # Insert multiple trades
        temp_db.insert_trade("AAPL", entry_time, 150.00, 10.0, "long", "strategy1")
        temp_db.insert_trade("MSFT", entry_time, 300.00, 5.0, "long", "strategy2")
        temp_db.insert_trade("AAPL", entry_time + 3600, 151.00, 8.0, "short", "strategy1")
        
        # Test symbol filter
        aapl_trades = temp_db.get_trade_history(symbol="AAPL")
        assert len(aapl_trades) == 2
        
        # Test status filter
        open_trades = temp_db.get_trade_history(status="open")
        assert len(open_trades) == 3
        
        # Test strategy filter
        strat1_trades = temp_db.get_trade_history(strategy="strategy1")
        assert len(strat1_trades) == 2
        
        # Test limit
        limited = temp_db.get_trade_history(limit=1)
        assert len(limited) == 1
    
    def test_get_stats(self, temp_db, sample_bars, sample_quote):
        """Test database statistics"""
        temp_db.insert_bars(sample_bars)
        temp_db.insert_quote(sample_quote)
        
        stats = temp_db.get_stats()
        assert stats["bars"] == 2
        assert stats["quotes"] == 1
        assert stats["indicators"] == 0
        assert stats["trade_history"] == 0
    
    def test_vacuum(self, temp_db):
        """Test database vacuum operation"""
        # Just verify it doesn't raise an error
        temp_db.vacuum()
