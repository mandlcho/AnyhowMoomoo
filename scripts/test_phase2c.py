"""
Test Phase 2C: Market Snapshots & Watchlist

Demonstrates:
1. MarketSnapshotBuilder aggregating all indicators
2. TickerSnapshot with complete technical analysis
3. MarketSnapshot for Claude consumption
4. Watchlist generation
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import pandas as pd
import asyncio
from loguru import logger

from data.storage import DataStore
from data.fetcher import HybridDataFetcher, YFinanceDataSource, RateLimiter
from market.snapshot import MarketSnapshotBuilder
from market.watchlist import WatchlistManager

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")


async def main():
    print("=" * 70)
    print("Phase 2C Test: Market Snapshots & Watchlist")
    print("=" * 70)
    print()
    
    # Initialize components
    store = DataStore()
    rate_limiter = RateLimiter(requests_per_minute=60)
    yfinance_source = YFinanceDataSource(rate_limiter=rate_limiter)
    fetcher = HybridDataFetcher(fallback=yfinance_source, storage=store)
    snapshot_builder = MarketSnapshotBuilder()
    watchlist_manager = WatchlistManager(custom_symbols=['AAPL', 'MSFT', 'NVDA'])
    
    # Test symbols
    symbols = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META']
    
    print("Step 1: Fetch recent data for multiple symbols")
    print("-" * 70)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    ticker_data = {}
    for symbol in symbols:
        print(f"Fetching {symbol}...")
        bars = await fetcher.fetch_daily_bars(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if not bars:
            print(f"  ⚠ No data for {symbol}, skipping")
            continue
        
        # Convert to DataFrame (convert Decimal to float)
        df = pd.DataFrame([
            {
                'timestamp': b.timestamp,
                'open': float(b.open),
                'high': float(b.high),
                'low': float(b.low),
                'close': float(b.close),
                'volume': b.volume,
            }
            for b in bars
        ])
        
        ticker_data[symbol] = df
        print(f"  ✓ Got {len(df)} bars")
    
    print()
    print("Step 2: Build individual ticker snapshots")
    print("-" * 70)
    
    account_balance = 100.0  # $100 account
    
    for symbol, df in ticker_data.items():
        print(f"\n{symbol}:")
        snapshot = snapshot_builder.build_ticker_snapshot(
            symbol=symbol,
            df=df,
            account_balance=account_balance,
            kelly_fraction=0.13,  # 13% from Kelly calculator
            risk_per_trade_pct=1.0
        )
        
        print(snapshot.to_claude_text())
    
    print()
    print("Step 3: Build complete market snapshot")
    print("-" * 70)
    
    # Simulate Kelly fractions for each ticker
    kelly_fractions = {
        'AAPL': 0.13,
        'MSFT': 0.10,
        'NVDA': 0.15,
        'GOOGL': 0.08,
        'META': 0.12,
    }
    
    market_snapshot = snapshot_builder.build_market_snapshot(
        ticker_data=ticker_data,
        account_balance=account_balance,
        available_cash=account_balance,
        current_positions=0,
        total_exposure_pct=0.0,
        kelly_fractions=kelly_fractions,
        risk_per_trade_pct=1.0
    )
    
    # Display full snapshot
    print(market_snapshot.to_claude_text())
    
    print()
    print("Step 4: Get top opportunities")
    print("-" * 70)
    
    top_opportunities = market_snapshot.get_top_opportunities(limit=3)
    print(f"\nTop 3 trading opportunities:")
    for i, ticker in enumerate(top_opportunities, 1):
        print(f"\n{i}. {ticker.symbol} - {ticker.entry_quality.upper()} entry")
        print(f"   Price: ${ticker.current_price:.2f}")
        print(f"   VWAP: {ticker.vwap_signal}")
        print(f"   RSI: {ticker.rsi_signal}")
        print(f"   Position: ${ticker.position_value:.2f} ({ticker.position_pct:.1%})")
        print(f"   Risk: ${ticker.max_loss:.2f} ({ticker.risk_pct:.1%})")
    
    print()
    print("Step 5: Watchlist management")
    print("-" * 70)
    
    # Get universe
    universe = watchlist_manager.get_universe()
    print(f"\nStock universe: {len(universe)} symbols")
    print(f"Sample: {list(universe)[:10]}")
    
    # Simulate market data for watchlist filtering
    market_data = {}
    for symbol in universe:
        # Simplified mock data
        market_data[symbol] = {
            'name': symbol,
            'sector': 'Technology',
            'price': 150.0,
            'volume': 50_000_000,
            'avg_volume_20d': 30_000_000,
            'spread_pct': 0.001,
            'atr_pct': 0.025,
        }
    
    watchlist = watchlist_manager.generate_watchlist(
        market_data=market_data,
        max_symbols=10
    )
    
    print(f"\nDaily watchlist: {len(watchlist)} symbols")
    print("\nSymbol | Price    | Volume    | Spread | ATR")
    print("-" * 70)
    for entry in watchlist:
        print(entry)
    
    print()
    print("=" * 70)
    print("✓ Phase 2C test complete!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  ✓ Built snapshots for {len(ticker_data)} tickers")
    print(f"  ✓ Market condition: {market_snapshot.market_condition}")
    print(f"  ✓ Volatility regime: {market_snapshot.volatility_regime}")
    print(f"  ✓ Top opportunity: {top_opportunities[0].symbol if top_opportunities else 'None'}")
    print(f"  ✓ Universe: {len(universe)} symbols")
    print(f"  ✓ Watchlist: {len(watchlist)} symbols")
    print()
    print("Next: Phase 2E (Backtesting Engine)")


if __name__ == '__main__':
    asyncio.run(main())
