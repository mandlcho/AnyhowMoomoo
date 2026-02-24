"""
Risk constraints for position sizing.

Implements hard caps and portfolio-level risk management to prevent
overleveraging and ensure proper diversification.
"""

from typing import Dict, Optional
from loguru import logger


class RiskConstraints:
    """
    Apply risk constraints to position sizing recommendations.
    
    Constraints:
        1. Max position size (20% default)
        2. Min position size (2% default)
        3. Max portfolio risk (10% default)
        4. Max sector exposure (30% default)
        5. Max correlated positions
    """
    
    def __init__(
        self,
        max_position_pct: float = 20.0,
        min_position_pct: float = 2.0,
        max_portfolio_risk_pct: float = 10.0,
        max_sector_exposure_pct: float = 30.0,
        max_leverage: float = 1.0
    ):
        """
        Initialize risk constraints.
        
        Args:
            max_position_pct: Maximum % of account in single position
            min_position_pct: Minimum viable position size %
            max_portfolio_risk_pct: Maximum total portfolio risk %
            max_sector_exposure_pct: Maximum exposure to single sector %
            max_leverage: Maximum leverage allowed (1.0 = no leverage)
        """
        if not 0 < min_position_pct < max_position_pct <= 100:
            raise ValueError(
                f"Invalid position limits: min={min_position_pct}, max={max_position_pct}"
            )
        
        self.max_position = max_position_pct / 100
        self.min_position = min_position_pct / 100
        self.max_portfolio_risk = max_portfolio_risk_pct / 100
        self.max_sector_exposure = max_sector_exposure_pct / 100
        self.max_leverage = max_leverage
        
        logger.info(
            f"RiskConstraints initialized: "
            f"position={min_position_pct}-{max_position_pct}%, "
            f"portfolio_risk={max_portfolio_risk_pct}%, "
            f"sector={max_sector_exposure_pct}%"
        )
    
    def apply_constraints(
        self,
        kelly_fraction: float,
        account_balance: float,
        current_price: float,
        portfolio_state: Optional[Dict] = None
    ) -> float:
        """
        Apply all risk constraints to Kelly recommendation.
        
        Args:
            kelly_fraction: Recommended Kelly fraction (0-1)
            account_balance: Total account balance
            current_price: Stock price
            portfolio_state: Current portfolio positions (optional)
            
        Returns:
            Constrained position fraction
            
        Example:
            # Kelly recommends 25%, but max is 20%
            constrained = constraints.apply_constraints(
                kelly_fraction=0.25,
                account_balance=10000,
                current_price=100,
                portfolio_state={'total_risk': 0.05, 'sector_tech': 0.15}
            )
            # Result: 0.20 (capped at max)
        """
        original_fraction = kelly_fraction
        
        # Constraint 1: Max position size
        if kelly_fraction > self.max_position:
            logger.warning(
                f"Kelly fraction ({kelly_fraction:.1%}) exceeds max position "
                f"({self.max_position:.1%}), capping"
            )
            kelly_fraction = self.max_position
        
        # Constraint 2: Min position size (or don't trade)
        if 0 < kelly_fraction < self.min_position:
            logger.warning(
                f"Kelly fraction ({kelly_fraction:.1%}) below min position "
                f"({self.min_position:.1%}), skipping trade"
            )
            return 0.0
        
        # Constraint 3: Portfolio risk budget
        if portfolio_state:
            current_risk = portfolio_state.get('total_risk', 0)
            remaining_risk = self.max_portfolio_risk - current_risk
            
            if remaining_risk <= 0:
                logger.warning(
                    f"Portfolio risk budget exhausted "
                    f"({current_risk:.1%}/{self.max_portfolio_risk:.1%})"
                )
                return 0.0
            
            # Calculate risk of this position (assumes 1% risk per trade)
            position_risk = kelly_fraction * 0.01  # Simplified
            
            if position_risk > remaining_risk:
                # Scale down to fit within risk budget
                kelly_fraction = kelly_fraction * (remaining_risk / position_risk)
                logger.info(
                    f"Scaled position to fit portfolio risk budget: "
                    f"{kelly_fraction:.1%}"
                )
        
        # Constraint 4: Leverage check
        if portfolio_state:
            total_exposure = portfolio_state.get('total_exposure', 0)
            new_exposure = total_exposure + kelly_fraction
            
            if new_exposure > self.max_leverage:
                excess = new_exposure - self.max_leverage
                kelly_fraction = max(0, kelly_fraction - excess)
                logger.warning(
                    f"Reduced position to stay within leverage limit: "
                    f"{kelly_fraction:.1%}"
                )
        
        if kelly_fraction != original_fraction:
            logger.debug(
                f"Applied constraints: {original_fraction:.1%} → {kelly_fraction:.1%}"
            )
        
        return kelly_fraction
    
    def check_sector_exposure(
        self,
        sector: str,
        new_position_fraction: float,
        portfolio_state: Optional[Dict] = None
    ) -> bool:
        """
        Check if adding position would violate sector exposure limits.
        
        Args:
            sector: Sector name (e.g., 'Technology', 'Healthcare')
            new_position_fraction: Size of new position (0-1)
            portfolio_state: Current portfolio with sector exposures
            
        Returns:
            True if within limits, False if would violate
        """
        if not portfolio_state:
            return True  # No portfolio state, allow trade
        
        sector_key = f'sector_{sector.lower()}'
        current_sector_exposure = portfolio_state.get(sector_key, 0)
        new_sector_exposure = current_sector_exposure + new_position_fraction
        
        if new_sector_exposure > self.max_sector_exposure:
            logger.warning(
                f"Sector exposure limit violated: {sector} would be "
                f"{new_sector_exposure:.1%} (max {self.max_sector_exposure:.1%})"
            )
            return False
        
        return True
    
    def get_max_additional_position(
        self,
        portfolio_state: Optional[Dict] = None
    ) -> float:
        """
        Calculate maximum additional position size given current portfolio.
        
        Args:
            portfolio_state: Current portfolio state
            
        Returns:
            Maximum additional position fraction (0-1)
        """
        if not portfolio_state:
            return self.max_position
        
        # Check leverage constraint
        total_exposure = portfolio_state.get('total_exposure', 0)
        remaining_leverage = self.max_leverage - total_exposure
        
        # Return minimum of max position size and remaining leverage
        return min(self.max_position, remaining_leverage)
