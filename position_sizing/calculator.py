"""
Position size calculator combining Kelly, ATR, and risk constraints.

This is the final calculator that integrates:
1. Modified Kelly Criterion (optimal sizing based on edge)
2. ATR-based stop placement (volatility-adjusted risk)
3. Risk constraints (hard caps and portfolio limits)
"""

from typing import Optional, Dict
from dataclasses import dataclass
from loguru import logger

from .kelly import ModifiedKellyCalculator, KellyFraction
from .constraints import RiskConstraints


@dataclass
class PositionSize:
    """
    Complete position sizing recommendation.
    """
    shares: float
    position_value: float
    position_fraction: float
    kelly_fraction: float
    constrained_fraction: float
    entry_price: float
    stop_price: float
    stop_distance: float
    max_loss: float
    risk_pct: float
    
    def __str__(self):
        return (
            f"Position Size Recommendation:\n"
            f"  Shares: {self.shares:.2f}\n"
            f"  Position Value: ${self.position_value:.2f}\n"
            f"  Position %: {self.position_fraction:.1%}\n"
            f"  Entry: ${self.entry_price:.2f}\n"
            f"  Stop: ${self.stop_price:.2f} (-{self.stop_distance:.2f})\n"
            f"  Max Loss: ${self.max_loss:.2f} ({self.risk_pct:.1%} of account)\n"
            f"  Kelly: {self.kelly_fraction:.1%} → {self.constrained_fraction:.1%} (after constraints)"
        )


class PositionSizeCalculator:
    """
    Calculate final position size combining Kelly, ATR, and constraints.
    
    Two-step process:
        1. Kelly determines optimal position size based on edge
        2. ATR determines actual shares based on risk limits
        
    Final position = minimum of Kelly-based and ATR-based sizing.
    """
    
    def __init__(
        self,
        kelly_calculator: Optional[ModifiedKellyCalculator] = None,
        risk_constraints: Optional[RiskConstraints] = None
    ):
        """
        Initialize position size calculator.
        
        Args:
            kelly_calculator: Modified Kelly calculator (creates default if None)
            risk_constraints: Risk constraints (creates default if None)
        """
        self.kelly = kelly_calculator or ModifiedKellyCalculator(
            fractional_multiplier=0.5,
            default_confidence=0.5
        )
        self.constraints = risk_constraints or RiskConstraints()
        
        logger.info("PositionSizeCalculator initialized")
    
    def calculate(
        self,
        account_balance: float,
        current_price: float,
        atr: float,
        kelly_fraction: float,
        risk_per_trade_pct: float = 1.0,
        stop_multiplier: float = 2.0,
        portfolio_state: Optional[Dict] = None
    ) -> PositionSize:
        """
        Calculate final position size.
        
        Args:
            account_balance: Total account balance
            current_price: Current stock price
            atr: Average True Range (volatility measure)
            kelly_fraction: Recommended Kelly fraction from ModifiedKellyCalculator
            risk_per_trade_pct: Max % of account to risk (default 1%)
            stop_multiplier: ATR multiplier for stop distance (default 2.0)
            portfolio_state: Current portfolio state for constraints
            
        Returns:
            PositionSize object with complete recommendation
            
        Example:
            size = calculator.calculate(
                account_balance=10000,
                current_price=150,
                atr=3.0,
                kelly_fraction=0.15,  # 15% from Kelly
                risk_per_trade_pct=1.0  # Risk 1% per trade
            )
            # Result: Shares based on min(Kelly-based, ATR-based)
        """
        # Step 1: Apply risk constraints to Kelly fraction
        constrained_fraction = self.constraints.apply_constraints(
            kelly_fraction=kelly_fraction,
            account_balance=account_balance,
            current_price=current_price,
            portfolio_state=portfolio_state
        )
        
        if constrained_fraction == 0:
            logger.warning("Position size constrained to zero, skipping trade")
            return PositionSize(
                shares=0,
                position_value=0,
                position_fraction=0,
                kelly_fraction=kelly_fraction,
                constrained_fraction=0,
                entry_price=current_price,
                stop_price=current_price,
                stop_distance=0,
                max_loss=0,
                risk_pct=0
            )
        
        # Step 2: Calculate Kelly-based position
        kelly_position_value = account_balance * constrained_fraction
        kelly_shares = kelly_position_value / current_price
        
        # Step 3: Calculate ATR-based position (risk-limited)
        stop_distance = atr * stop_multiplier
        stop_price = current_price - stop_distance
        max_loss = account_balance * (risk_per_trade_pct / 100)
        atr_shares = max_loss / stop_distance
        
        # Step 4: Take minimum (most conservative)
        final_shares = min(kelly_shares, atr_shares)
        final_position_value = final_shares * current_price
        final_fraction = final_position_value / account_balance
        
        # Calculate actual risk
        actual_max_loss = final_shares * stop_distance
        actual_risk_pct = actual_max_loss / account_balance
        
        result = PositionSize(
            shares=final_shares,
            position_value=final_position_value,
            position_fraction=final_fraction,
            kelly_fraction=kelly_fraction,
            constrained_fraction=constrained_fraction,
            entry_price=current_price,
            stop_price=stop_price,
            stop_distance=stop_distance,
            max_loss=actual_max_loss,
            risk_pct=actual_risk_pct
        )
        
        logger.info(
            f"Position calculated: {final_shares:.2f} shares "
            f"({final_fraction:.1%} of account), "
            f"risk=${actual_max_loss:.2f} ({actual_risk_pct:.1%})"
        )
        
        # Log which constraint was binding
        if final_shares == kelly_shares:
            logger.debug("Kelly-based sizing is binding (less conservative than ATR)")
        else:
            logger.debug("ATR-based sizing is binding (more conservative than Kelly)")
        
        return result
    
    def calculate_from_kelly_result(
        self,
        account_balance: float,
        current_price: float,
        atr: float,
        kelly_result: KellyFraction,
        risk_per_trade_pct: float = 1.0,
        stop_multiplier: float = 2.0,
        portfolio_state: Optional[Dict] = None
    ) -> PositionSize:
        """
        Convenience method that accepts KellyFraction directly.
        
        Args:
            account_balance: Total account balance
            current_price: Current stock price
            atr: Average True Range
            kelly_result: KellyFraction from ModifiedKellyCalculator
            risk_per_trade_pct: Max % of account to risk
            stop_multiplier: ATR multiplier for stop distance
            portfolio_state: Current portfolio state
            
        Returns:
            PositionSize object
        """
        return self.calculate(
            account_balance=account_balance,
            current_price=current_price,
            atr=atr,
            kelly_fraction=kelly_result.adjusted_kelly,
            risk_per_trade_pct=risk_per_trade_pct,
            stop_multiplier=stop_multiplier,
            portfolio_state=portfolio_state
        )
