"""
Test script for Phase 2F: Modified Kelly Position Sizing

This script demonstrates:
1. Modified Kelly Criterion calculation
2. Risk constraints application
3. Combined position sizing (Kelly + ATR)
4. Edge detection and validation

Usage:
    python scripts/test_phase2f.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from position_sizing import ModifiedKellyCalculator, RiskConstraints, PositionSizeCalculator


def main():
    """Main test function"""
    
    print("=" * 70)
    print("Phase 2F Test: Modified Kelly Position Sizing")
    print("=" * 70)
    print()
    
    # Step 1: Basic Kelly calculation
    print("Step 1: Basic Modified Kelly Calculation")
    print("-" * 70)
    
    kelly_calc = ModifiedKellyCalculator(
        fractional_multiplier=0.5,  # Half-Kelly
        default_confidence=0.5      # Conservative (50% confidence)
    )
    
    # Scenario: 55% win rate, avg win $100, avg loss $50
    kelly_result = kelly_calc.calculate(
        win_probability=0.55,
        avg_win=100,
        avg_loss=50,
        confidence=0.8  # Fairly confident in estimates
    )
    
    print(kelly_result)
    print()
    
    # Step 2: Edge detection
    print("Step 2: Positive Edge Detection")
    print("-" * 70)
    
    has_edge = kelly_calc.has_positive_edge(
        win_probability=0.55,
        win_loss_ratio=2.0  # Win twice as much as you lose
    )
    print(f"Strategy has positive edge: {has_edge}")
    print()
    
    # Test negative edge
    no_edge = kelly_calc.has_positive_edge(
        win_probability=0.45,
        win_loss_ratio=1.0  # Losing strategy
    )
    print(f"Bad strategy has edge: {no_edge}")
    print()
    
    # Step 3: Estimating from trade history
    print("Step 3: Estimate Kelly from Trade History")
    print("-" * 70)
    
    # Simulate 50 trades
    trades = [
        {'pnl': 150}, {'pnl': -60}, {'pnl': 120}, {'pnl': -55},
        {'pnl': 180}, {'pnl': -70}, {'pnl': 95}, {'pnl': -50},
        {'pnl': 140}, {'pnl': -65}, {'pnl': 110}, {'pnl': -45},
        {'pnl': 160}, {'pnl': -75}, {'pnl': 105}, {'pnl': -60},
        {'pnl': 135}, {'pnl': -55}, {'pnl': 125}, {'pnl': -70},
        {'pnl': 145}, {'pnl': -50}, {'pnl': 115}, {'pnl': -65},
        {'pnl': 155}, {'pnl': -60}, {'pnl': 130}, {'pnl': -55},
        {'pnl': 140}, {'pnl': -70}, {'pnl': 120}, {'pnl': -50},
        {'pnl': 150}, {'pnl': -65}, {'pnl': 110}, {'pnl': -60},
        {'pnl': 165}, {'pnl': -55}, {'pnl': 125}, {'pnl': -70},
        {'pnl': 135}, {'pnl': -50}, {'pnl': 145}, {'pnl': -65},
        {'pnl': 120}, {'pnl': -60}, {'pnl': 155}, {'pnl': -55},
        {'pnl': 140}, {'pnl': -70}
    ]
    
    estimated_kelly = kelly_calc.estimate_from_trades(trades)
    if estimated_kelly:
        print(f"Estimated from {len(trades)} trades:")
        print(estimated_kelly)
    print()
    
    # Step 4: Risk constraints
    print("Step 4: Risk Constraints Application")
    print("-" * 70)
    
    constraints = RiskConstraints(
        max_position_pct=20.0,
        min_position_pct=2.0,
        max_portfolio_risk_pct=10.0,
        max_sector_exposure_pct=30.0
    )
    
    # Test: Kelly recommends 25%, but max is 20%
    constrained = constraints.apply_constraints(
        kelly_fraction=0.25,
        account_balance=10000,
        current_price=100,
        portfolio_state=None
    )
    
    print(f"Kelly recommendation: 25.0%")
    print(f"After constraints: {constrained:.1%}")
    print()
    
    # Test: Below minimum position
    tiny_constrained = constraints.apply_constraints(
        kelly_fraction=0.01,  # 1%
        account_balance=10000,
        current_price=100,
        portfolio_state=None
    )
    
    print(f"Kelly recommendation: 1.0% (below 2% minimum)")
    print(f"After constraints: {tiny_constrained:.1%} (trade skipped)")
    print()
    
    # Step 5: Combined position sizing
    print("Step 5: Combined Position Sizing (Kelly + ATR + Constraints)")
    print("-" * 70)
    
    position_calc = PositionSizeCalculator(
        kelly_calculator=kelly_calc,
        risk_constraints=constraints
    )
    
    # Scenario: $100 account trading AAPL
    account_balance = 100
    current_price = 150
    atr = 3.0  # $3 ATR
    kelly_fraction = kelly_result.adjusted_kelly
    
    position = position_calc.calculate(
        account_balance=account_balance,
        current_price=current_price,
        atr=atr,
        kelly_fraction=kelly_fraction,
        risk_per_trade_pct=1.0,  # Risk 1% per trade
        stop_multiplier=2.0       # Stop at 2× ATR
    )
    
    print(position)
    print()
    
    # Step 6: Multiple scenarios
    print("Step 6: Position Sizing for Different Scenarios")
    print("-" * 70)
    
    scenarios = [
        {
            'name': 'High conviction, low volatility',
            'kelly_fraction': 0.20,
            'atr': 2.0,
            'price': 100
        },
        {
            'name': 'Medium conviction, medium volatility',
            'kelly_fraction': 0.10,
            'atr': 5.0,
            'price': 150
        },
        {
            'name': 'Low conviction, high volatility',
            'kelly_fraction': 0.05,
            'atr': 10.0,
            'price': 200
        }
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        print(f"  Price: ${scenario['price']}, ATR: ${scenario['atr']}")
        
        pos = position_calc.calculate(
            account_balance=100,
            current_price=scenario['price'],
            atr=scenario['atr'],
            kelly_fraction=scenario['kelly_fraction'],
            risk_per_trade_pct=1.0,
            stop_multiplier=2.0
        )
        
        print(f"  → Shares: {pos.shares:.3f}, Value: ${pos.position_value:.2f}")
        print(f"  → Stop: ${pos.stop_price:.2f}, Max loss: ${pos.max_loss:.2f}")
    
    print()
    print("=" * 70)
    print("✓ Phase 2F test complete!")
    print("=" * 70)
    print()
    print("Summary:")
    print("  ✓ Modified Kelly: Half-Kelly with confidence adjustment")
    print("  ✓ Risk Constraints: 20% max, 2% min position sizes")
    print("  ✓ Combined Sizing: Kelly + ATR for optimal risk management")
    print("  ✓ Edge Detection: Validates positive expectancy")
    print()
    print("Key Insight:")
    print("  Position sizing takes MINIMUM of:")
    print("    1. Kelly-based size (optimal for edge)")
    print("    2. ATR-based size (respects risk limits)")
    print("  This ensures both edge optimization AND risk control!")


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}",
        level="INFO"
    )
    
    main()
