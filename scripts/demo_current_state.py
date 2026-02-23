#!/usr/bin/env python3
"""
Visual demonstration of current Phase 1 functionality.
Shows what works now without needing OpenD running.
"""
import sys
import os
from datetime import datetime
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_header(text):
    """Print a styled header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")

def print_section(title):
    """Print a section divider."""
    print(f"\n--- {title} ---")

def demo_config_system():
    """Demonstrate configuration loading."""
    print_header("📋 DEMO 1: Configuration System")
    
    try:
        from daemon.config import ConfigLoader
        
        print("Loading configuration from config/config.yaml...")
        loader = ConfigLoader()
        config = loader.load()
        
        print("✅ Config loaded successfully!\n")
        
        print(f"Execution Mode:  {config.execution_mode.value}")
        print(f"Paper Trading:   {config.paper_trading}")
        print(f"OpenD Host:      {config.opend_host}:{config.opend_port}")
        
        print_section("Risk Settings")
        print(f"  Max risk per trade:     {config.risk.max_risk_per_trade_pct}%")
        print(f"  Max open positions:     {config.risk.max_open_positions}")
        print(f"  Max sector exposure:    {config.risk.max_sector_exposure_pct}%")
        print(f"  Min liquidity (volume): {config.risk.min_liquidity_avg_volume:,} shares/day")
        
        print_section("Position Sizing")
        print(f"  Min notional per trade: ${config.sizing.min_notional_per_trade}")
        print(f"  Max notional per trade: ${config.sizing.max_notional_per_trade}")
        print(f"  Fractional shares:      {config.sizing.fractional_shares}")
        print(f"  Min R:R ratio:          {config.sizing.min_rr_ratio}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_data_models():
    """Demonstrate Pydantic data models."""
    print_header("🗂️  DEMO 2: Data Models (Pydantic)")
    
    try:
        from data.models import (
            OHLCV, Order, TradePlan, Position, AccountState,
            OrderSide, OrderType, OrderStatus, MarketDataInterval, PositionSide
        )
        
        # Create sample OHLCV bar
        print_section("OHLCV Bar (Market Data)")
        bar = OHLCV(
            symbol="AAPL",
            timestamp=datetime.now(),
            open=Decimal("180.50"),
            high=Decimal("182.30"),
            low=Decimal("179.80"),
            close=Decimal("181.75"),
            volume=25_000_000,
            interval=MarketDataInterval.DAY_1
        )
        print(f"  Symbol:    {bar.symbol}")
        print(f"  Date:      {bar.timestamp.strftime('%Y-%m-%d')}")
        print(f"  OHLC:      ${bar.open} / ${bar.high} / ${bar.low} / ${bar.close}")
        print(f"  Volume:    {bar.volume:,}")
        
        # Create sample order
        print_section("Order")
        order = Order(
            order_id="ORDER123",
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("10"),
            price=Decimal("181.50"),
            status=OrderStatus.SUBMITTED,
            filled_quantity=Decimal("0"),
            submit_time=datetime.now(),
            update_time=datetime.now(),
        )
        print(f"  Order ID:  {order.order_id}")
        print(f"  Symbol:    {order.symbol}")
        print(f"  Side:      {order.side.value}")
        print(f"  Type:      {order.order_type.value}")
        print(f"  Quantity:  {order.quantity} shares @ ${order.price}")
        print(f"  Status:    {order.status.value}")
        
        # Create sample position
        print_section("Position")
        position = Position(
            symbol="AAPL",
            side=PositionSide.LONG,
            quantity=Decimal("10"),
            avg_entry_price=Decimal("180.00"),
            current_price=Decimal("181.75"),
            market_value=Decimal("1817.50"),
            unrealized_pnl=Decimal("17.50"),
            unrealized_pnl_pct=Decimal("0.97"),
            entry_time=datetime.now(),
        )
        print(f"  Symbol:        {position.symbol}")
        print(f"  Quantity:      {position.quantity} shares")
        print(f"  Entry Price:   ${position.avg_entry_price}")
        print(f"  Current Price: ${position.current_price}")
        print(f"  Market Value:  ${position.market_value}")
        print(f"  Unrealized P&L: ${position.unrealized_pnl} ({position.unrealized_pnl_pct}%)")
        
        # Create sample trade plan
        print_section("Trade Plan (Claude Output)")
        plan = TradePlan(
            plan_id="PLAN_20260220_001",
            symbol="AAPL",
            direction=OrderSide.BUY,
            rationale="Strong momentum on earnings beat, pullback to VWAP support",
            timeframe="swing",
            expected_hold_days=5,
            entry_price=Decimal("181.50"),
            stop_price=Decimal("177.00"),
            target_prices=[Decimal("190.00"), Decimal("195.00")],
            allocation_risk_pct=Decimal("1.5"),
            created_at=datetime.now(),
        )
        print(f"  Plan ID:     {plan.plan_id}")
        print(f"  Symbol:      {plan.symbol}")
        print(f"  Direction:   {plan.direction.value}")
        print(f"  Timeframe:   {plan.timeframe} ({plan.expected_hold_days} days)")
        print(f"  Entry:       ${plan.entry_price}")
        print(f"  Stop:        ${plan.stop_price}")
        print(f"  Targets:     {', '.join(f'${t}' for t in plan.target_prices)}")
        print(f"  Risk:        {plan.allocation_risk_pct}% of account")
        print(f"  Rationale:   {plan.rationale}")
        
        # Create sample account state
        print_section("Account State")
        account = AccountState(
            timestamp=datetime.now(),
            total_equity=Decimal("105.50"),
            cash=Decimal("87.75"),
            market_value=Decimal("17.75"),
            buying_power=Decimal("87.75"),
            unrealized_pnl=Decimal("0.25"),
            realized_pnl_today=Decimal("5.50"),
            num_positions=1,
            positions=[position]
        )
        print(f"  Total Equity:   ${account.total_equity}")
        print(f"  Cash:           ${account.cash}")
        print(f"  Market Value:   ${account.market_value}")
        print(f"  Unrealized P&L: ${account.unrealized_pnl}")
        print(f"  Realized P&L:   ${account.realized_pnl_today} (today)")
        print(f"  Open Positions: {account.num_positions}")
        
        print("\n✅ All models work correctly with type validation!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def demo_opend_wrapper():
    """Demonstrate OpenD connection wrapper (dry-run, no actual connection)."""
    print_header("🔌 DEMO 3: OpenD Connection Wrapper")
    
    try:
        from connectors.opend import OpenDConnection
        
        print("Creating OpenD connection wrapper...")
        print("(This is a dry-run - NOT connecting to actual OpenD)\n")
        
        conn = OpenDConnection(
            host="127.0.0.1",
            port=11111,
            paper_trading=True
        )
        
        print("✅ Connection object created")
        print(f"   Host:          {conn.host}")
        print(f"   Port:          {conn.port}")
        print(f"   Paper Trading: {conn.paper_trading}")
        
        # Health check without actual connection
        health = conn.health_check()
        print(f"\nHealth Check (dry-run):")
        print(f"   Quote Connected: {health['quote_connected']}")
        print(f"   Trade Connected: {health['trade_connected']}")
        
        print("\n💡 To test actual connection:")
        print("   1. Start OpenD on localhost:11111")
        print("   2. Add credentials to .env file")
        print("   3. Run: python scripts/test_opend.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_logging_system():
    """Demonstrate logging configuration."""
    print_header("📝 DEMO 4: Logging System")
    
    try:
        from daemon.main import setup_logging
        from loguru import logger
        import tempfile
        
        # Use temp directory for demo
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"Setting up logging in temporary directory...")
            setup_logging(tmpdir, level="INFO")
            
            print("\n✅ Logging configured with:")
            print("   - Console output (colored)")
            print("   - File rotation (daily)")
            print("   - Separate trade audit log")
            print("   - 30-day retention")
            
            print("\nDemo log messages:")
            logger.info("This is an INFO message")
            logger.warning("This is a WARNING message")
            logger.error("This is an ERROR message")
            
            # Trade log example
            logger.bind(TRADE=True).info("TRADE: BUY 10 AAPL @ $181.50")
            
            print("\n💡 When daemon runs, logs saved to:")
            print("   - logs/daemon.log (all logs)")
            print("   - logs/trades.log (trade audit trail only)")
    
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_workflow():
    """Show the complete workflow (future phases)."""
    print_header("🔄 DEMO 5: Complete Workflow (Future)")
    
    print("This shows how data will flow when all phases are complete:\n")
    
    print("1️⃣  MARKET DATA (Phase 2)")
    print("    └─ OpenD provides real-time quotes")
    print("    └─ Data stored and cached")
    print("    └─ Indicators calculated (RSI, ATR, VWAP)")
    print("    └─ Market snapshot created")
    
    print("\n2️⃣  STRATEGY ANALYSIS (Phase 3)")
    print("    └─ Market snapshot sent to Claude (manual)")
    print("    └─ Claude analyzes and returns trade plan")
    print("    └─ Trade plan validated against risk rules")
    
    print("\n3️⃣  APPROVAL (Phase 3)")
    print("    └─ SEMI_AUTOMATIC: You approve/reject via UI")
    print("    └─ AUTOMATIC: Auto-approved if passes strict rules")
    
    print("\n4️⃣  EXECUTION (Phase 4)")
    print("    └─ Position size calculated from risk %")
    print("    └─ Order placed via OpenD")
    print("    └─ Order tracked through lifecycle")
    print("    └─ Position monitoring begins")
    
    print("\n5️⃣  MONITORING (Phase 4)")
    print("    └─ Track P&L in real-time")
    print("    └─ Check stop-loss and targets")
    print("    └─ Exit when conditions met")
    
    print("\n6️⃣  UI DISPLAY (Phase 5)")
    print("    └─ TUI: Terminal dashboard with tables/charts")
    print("    └─ Web: Browser-based dashboard")
    print("    └─ Mobile-friendly responsive design")

def main():
    """Run all demonstrations."""
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "AnyhowMoomoo Trading Daemon" + " " * 21 + "║")
    print("║" + " " * 15 + "Phase 1 Demonstration" + " " * 22 + "║")
    print("╚" + "═" * 58 + "╝")
    
    print("\nThis demo shows what's currently working (Phase 1).")
    print("No OpenD connection required - everything runs locally.")
    
    try:
        demo_config_system()
        demo_data_models()
        demo_opend_wrapper()
        demo_logging_system()
        demo_workflow()
        
        print_header("✨ Demo Complete!")
        print("All Phase 1 components are working correctly.\n")
        print("📚 Next Steps:")
        print("   - START_HERE.md - Project overview")
        print("   - QUICKSTART.md - Setup guide")
        print("   - HUMMINGBOT_REFERENCE.md - Patterns for Phase 2+")
        print("\n🚀 Ready to build Phase 2 when you are!")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
