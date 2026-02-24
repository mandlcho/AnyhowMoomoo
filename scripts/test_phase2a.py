"""
Test script for Phase 2A: Storage + Data Fetching

This script demonstrates:
1. Database initialization
2. yfinance data fetching (fallback source)
3. Storage layer operations
4. Basic data validation

Usage:
    python scripts/test_phase2a.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from data.storage import DataStore
from data.fetcher import YFinanceDataSource, HybridDataFetcher, RateLimiter
from data.models import MarketDataInterval


async def main():
    """Main test function"""
    
    print("=" * 70)
    print("Phase 2A Test: Storage + Data Fetching")
    print("=" * 70)
    print()
    
    # Step 1: Initialize storage
    print("Step 1: Initializing database...")
    db_path = "data_cache/test_market_data.db"
    store = DataStore(db_path)
    print(f"✓ Database initialized at {db_path}")
    print()
    
    # Step 2: Check initial stats
    print("Step 2: Checking initial database stats...")
    stats = store.get_stats()
    print(f"  bars: {stats['bars']}")
    print(f"  quotes: {stats['quotes']}")
    print(f"  indicators: {stats['indicators']}")
    print(f"  trade_history: {stats['trade_history']}")
    print()
    
    # Step 3: Initialize data fetcher (yfinance only for now)
    print("Step 3: Initializing data fetcher (yfinance)...")
    rate_limiter = RateLimiter(requests_per_minute=60)
    yf_source = YFinanceDataSource(rate_limiter)
    fetcher = HybridDataFetcher(
        primary=None,  # No moomoo for this test
        fallback=yf_source,
        storage=store
    )
    print("✓ Data fetcher initialized")
    print()
    
    # Step 4: Fetch daily data for AAPL
    print("Step 4: Fetching 30 days of AAPL daily data...")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    try:
        bars = await fetcher.fetch_daily_bars(
            symbol="AAPL",
            start_date=start_date,
            end_date=end_date,
            force_fallback=True  # Use yfinance
        )
        
        print(f"✓ Fetched {len(bars)} daily bars")
        print(f"  Date range: {bars[0].timestamp.date()} to {bars[-1].timestamp.date()}")
        print(f"  Latest close: ${bars[-1].close}")
        print(f"  Latest volume: {bars[-1].volume:,}")
        print()
        
    except Exception as e:
        print(f"✗ Failed to fetch data: {e}")
        return
    
    # Step 5: Verify data was stored
    print("Step 5: Verifying data was stored in database...")
    retrieved = store.get_bars("AAPL", "1day", limit=5)
    print(f"✓ Retrieved {len(retrieved)} bars from database")
    
    if retrieved:
        latest = retrieved[-1]
        print(f"  Latest bar: {latest.timestamp.date()}")
        print(f"    O: ${latest.open}, H: ${latest.high}, L: ${latest.low}, C: ${latest.close}")
        print(f"    Volume: {latest.volume:,}")
    print()
    
    # Step 6: Fetch intraday data (5-minute bars)
    print("Step 6: Fetching 5 days of AAPL 5-minute bars...")
    try:
        intraday_bars = await fetcher.fetch_intraday_bars(
            symbol="AAPL",
            interval=MarketDataInterval.MIN_5,
            lookback_days=5,
            force_fallback=True
        )
        
        print(f"✓ Fetched {len(intraday_bars)} 5-minute bars")
        if intraday_bars:
            print(f"  Time range: {intraday_bars[0].timestamp} to {intraday_bars[-1].timestamp}")
        print()
        
    except Exception as e:
        print(f"✗ Failed to fetch intraday data: {e}")
        print()
    
    # Step 7: Final database stats
    print("Step 7: Final database stats...")
    stats = store.get_stats()
    print(f"  bars: {stats['bars']}")
    print(f"  quotes: {stats['quotes']}")
    print(f"  indicators: {stats['indicators']}")
    print(f"  trade_history: {stats['trade_history']}")
    print()
    
    print("=" * 70)
    print("✓ Phase 2A test complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  - Install dependencies: pip install -r requirements.txt")
    print("  - Run this test again to verify yfinance works")
    print("  - Move on to Phase 2B (indicators)")


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}",
        level="INFO"
    )
    
    # Run async main
    asyncio.run(main())
