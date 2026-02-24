"""
COMPREHENSIVE PHASE 2 DEMO - Full End-to-End Backtest

Demonstrates all Phase 2 components working together:
1. Data fetching (multi-source with fallback)
2. Technical indicators (VWAP, RSI, ATR)
3. Position sizing (Modified Kelly)
4. Market snapshots
5. Backtesting engine
6. VWAP mean-reversion strategy
7. Performance analysis

This is a complete working example of swing trading with AnyhowMoomoo.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from data.storage import DataStore
from data.fetcher import HybridDataFetcher, YFinanceDataSource, RateLimiter
from backtest.engine import BacktestEngine, BacktestConfig
from strategies.vwap_mean_reversion import VWAPMeanReversionStrategy
from position_sizing.kelly import ModifiedKellyCalculator

# Configure logging
logger.remove()
logger.add(sys.stderr, level="WARNING")  # Only warnings/errors during backtest
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")


def print_banner(text):
    """Print a fancy banner."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


async def main():
    print_banner("ANYHOWMOOMOO - PHASE 2 COMPREHENSIVE DEMO")
    print("Demonstrating all components: Data → Indicators → Sizing → Backtest → Analysis")
    print()
    
    # Configuration
    SYMBOL = "AAPL"
    INITIAL_CAPITAL = 10000.0
    BACKTEST_DAYS = 180  # 6 months
    
    print(f"Configuration:")
    print(f"  Symbol: {SYMBOL}")
    print(f"  Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print(f"  Backtest Period: {BACKTEST_DAYS} days (~6 months)")
    print()
    
    # =========================================================================
    # STEP 1: Initialize Components
    # =========================================================================
    print_banner("STEP 1: Initialize All Components")
    
    print("Initializing data infrastructure...")
    store = DataStore()
    rate_limiter = RateLimiter(requests_per_minute=60)
    yfinance_source = YFinanceDataSource(rate_limiter=rate_limiter)
    fetcher = HybridDataFetcher(fallback=yfinance_source, storage=store)
    print("  ✓ DataStore + HybridDataFetcher ready")
    
    print("\nInitializing strategy components...")
    strategy = VWAPMeanReversionStrategy(
        kelly_fraction=0.10,  # Conservative 10%
        risk_per_trade_pct=1.0  # Risk 1% per trade
    )
    print("  ✓ VWAP Mean-Reversion Strategy ready")
    print(f"    - Entry: Price < VWAP -2σ AND RSI < 30")
    print(f"    - Exit: Price > VWAP OR RSI > 70")
    print(f"    - Stop: 2x ATR below entry")
    
    print("\nInitializing backtest engine...")
    config = BacktestConfig(
        initial_capital=INITIAL_CAPITAL,
        commission_per_share=0.0,  # moomoo has $0 commissions
        slippage_pct=0.001,  # 0.1% slippage
        use_vwap_fills=True  # Use VWAP for realistic fills
    )
    engine = BacktestEngine(config=config)
    print("  ✓ BacktestEngine ready")
    print(f"    - VWAP-based fills enabled")
    print(f"    - Slippage: {config.slippage_pct:.1%}")
    
    # =========================================================================
    # STEP 2: Fetch Historical Data
    # =========================================================================
    print_banner("STEP 2: Fetch Historical Market Data")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=BACKTEST_DAYS)
    
    print(f"Fetching {SYMBOL} daily bars from {start_date.date()} to {end_date.date()}...")
    print("(Using yfinance as data source with automatic fallback)")
    
    bars = await fetcher.fetch_daily_bars(
        symbol=SYMBOL,
        start_date=start_date,
        end_date=end_date
    )
    
    if not bars:
        print("❌ Failed to fetch data!")
        return
    
    print(f"  ✓ Fetched {len(bars)} bars")
    
    # Convert to DataFrame
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
    
    print(f"  ✓ Data range: {df['timestamp'].min().date()} to {df['timestamp'].max().date()}")
    print(f"  ✓ Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    print(f"  ✓ Avg daily volume: {df['volume'].mean()/1e6:.1f}M shares")
    
    # =========================================================================
    # STEP 3: Calculate Technical Indicators
    # =========================================================================
    print_banner("STEP 3: Calculate Technical Indicators")
    
    print("Calculating VWAP, RSI, ATR...")
    signals_df = strategy.generate_signals(df)
    
    print("  ✓ VWAP calculated (session-based with 2σ bands)")
    print("  ✓ RSI calculated (14-period Wilder's smoothing)")
    print("  ✓ ATR calculated (14-period normalized)")
    print()
    
    # Show sample of indicators
    latest = signals_df.iloc[-1]
    print("Latest indicator values:")
    print(f"  Price: ${latest['close']:.2f}")
    print(f"  VWAP: ${latest['vwap']:.2f}")
    print(f"  VWAP Lower 2σ: ${latest['vwap_lower_2std']:.2f}")
    print(f"  VWAP Upper 2σ: ${latest['vwap_upper_2std']:.2f}")
    print(f"  RSI: {latest['rsi']:.1f}")
    print(f"  ATR: ${latest['atr']:.2f}")
    print(f"  Signal: {latest['signal']}")
    
    # Count signals
    buy_signals = (signals_df['signal'] == 'buy').sum()
    sell_signals = (signals_df['signal'] == 'sell').sum()
    print(f"\nSignal distribution over {len(signals_df)} bars:")
    print(f"  BUY signals: {buy_signals}")
    print(f"  SELL signals: {sell_signals}")
    print(f"  HOLD: {len(signals_df) - buy_signals - sell_signals}")
    
    # =========================================================================
    # STEP 4: Run Backtest
    # =========================================================================
    print_banner("STEP 4: Run Backtest with VWAP Mean-Reversion Strategy")
    
    print(f"Running backtest on {len(signals_df)} bars...")
    print("(This may take a moment...)")
    print()
    
    logger.remove()  # Silence debug logs during backtest
    logger.add(sys.stderr, level="ERROR")
    
    results = strategy.backtest(
        symbol=SYMBOL,
        df=signals_df,
        engine=engine
    )
    
    logger.remove()
    logger.add(sys.stderr, level="WARNING")
    logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    metrics = results['metrics']
    trades_df = results['trades']
    equity_curve = results['equity_curve']
    
    print("  ✓ Backtest complete!")
    
    # =========================================================================
    # STEP 5: Analyze Performance
    # =========================================================================
    print_banner("STEP 5: Performance Analysis")
    
    print(metrics)
    
    # Additional analysis
    if len(trades_df) > 0:
        print("\nTrade Distribution:")
        print(f"  Winners: {metrics.winning_trades} trades ({metrics.win_rate:.1%})")
        print(f"  Losers: {metrics.losing_trades} trades")
        print(f"  Avg Winner: ${metrics.avg_win:.2f}")
        print(f"  Avg Loser: ${metrics.avg_loss:.2f}")
        print(f"  Profit Factor: {metrics.profit_factor:.2f}")
        
        print("\nHolding Periods:")
        print(f"  Avg Hold: {metrics.avg_hold_days:.1f} days")
        print(f"  Min Hold: {trades_df['hold_days'].min()} days")
        print(f"  Max Hold: {trades_df['hold_days'].max()} days")
        
        print("\nRisk Metrics:")
        print(f"  Max Drawdown: ${metrics.max_drawdown:.2f} ({metrics.max_drawdown_pct:.1%})")
        print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        
        # Show best and worst trades
        trades_df_sorted = trades_df.sort_values('pnl', ascending=False)
        
        print("\nBest Trade:")
        best = trades_df_sorted.iloc[0]
        print(f"  {best['entry_date'].date()} → {best['exit_date'].date()}")
        print(f"  Entry: ${best['entry_price']:.2f} → Exit: ${best['exit_price']:.2f}")
        print(f"  P&L: ${best['pnl']:.2f} ({best['pnl_pct']:.1%}) in {best['hold_days']} days")
        
        print("\nWorst Trade:")
        worst = trades_df_sorted.iloc[-1]
        print(f"  {worst['entry_date'].date()} → {worst['exit_date'].date()}")
        print(f"  Entry: ${worst['entry_price']:.2f} → Exit: ${worst['exit_price']:.2f}")
        print(f"  P&L: ${worst['pnl']:.2f} ({worst['pnl_pct']:.1%}) in {worst['hold_days']} days")
        
        # Equity curve stats
        print("\nEquity Curve:")
        final_equity = equity_curve['equity'].iloc[-1]
        max_equity = equity_curve['equity'].max()
        min_equity = equity_curve['equity'].min()
        print(f"  Starting: ${INITIAL_CAPITAL:,.2f}")
        print(f"  Final: ${final_equity:,.2f}")
        print(f"  Peak: ${max_equity:,.2f}")
        print(f"  Trough: ${min_equity:,.2f}")
        
    else:
        print("⚠ No trades executed!")
        print("Strategy conditions were not met during backtest period.")
    
    # =========================================================================
    # STEP 6: Kelly Parameter Estimation
    # =========================================================================
    print_banner("STEP 6: Kelly Parameter Estimation from Backtest")
    
    if len(trades_df) > 0:
        kelly_calc = ModifiedKellyCalculator()
        
        # Estimate Kelly from trade history
        kelly_result = kelly_calc.estimate_from_trades(
            win_loss_records=trades_df[['pnl', 'win']].values.tolist()
        )
        
        print("Estimated Kelly Fraction from backtest results:")
        print(kelly_result)
        
        print("\nInterpretation:")
        if kelly_result.has_edge:
            print("  ✓ Strategy shows positive edge")
            print(f"  → Recommended position size: {kelly_result.adjusted_kelly:.1%}")
            print(f"  → Full Kelly would be: {kelly_result.full_kelly:.1%} (too aggressive)")
            print(f"  → Half Kelly: {kelly_result.fractional_kelly:.1%}")
            if kelly_result.adjusted_kelly < 0.05:
                print("  ⚠ Edge is small - consider refining strategy")
            elif kelly_result.adjusted_kelly > 0.15:
                print("  ✓ Strong edge detected!")
        else:
            print("  ❌ No positive edge detected")
            print("  → Strategy needs improvement before live trading")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print_banner("DEMO COMPLETE - All Phase 2 Components Working!")
    
    print("Successfully demonstrated:")
    print("  ✅ Multi-source data fetching with yfinance fallback")
    print("  ✅ High-performance technical indicators (VWAP, RSI, ATR)")
    print("  ✅ Modified Kelly Criterion position sizing")
    print("  ✅ Realistic backtesting with VWAP fills")
    print("  ✅ VWAP mean-reversion strategy execution")
    print("  ✅ Comprehensive performance analysis")
    print("  ✅ Kelly parameter estimation from results")
    print()
    
    if len(trades_df) > 0:
        print(f"Final Results:")
        print(f"  Total Return: {metrics.total_return_pct:.1%}")
        print(f"  Win Rate: {metrics.win_rate:.1%}")
        print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"  Total Trades: {metrics.total_trades}")
        
        if metrics.total_return_pct > 0:
            print(f"\n  🎉 PROFITABLE STRATEGY!")
        else:
            print(f"\n  ⚠ Strategy needs optimization")
    
    print()
    print("Ready for Phase 3: Claude Integration & Live Trading!")
    print()


if __name__ == '__main__':
    asyncio.run(main())
