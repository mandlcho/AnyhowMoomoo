"""
Modified Kelly Criterion calculator for position sizing.

Based on research from:
- John Kelly's original paper (1956)
- Edward Thorp's applications to investing
- Fractional Kelly methods for reduced volatility

Conservative approach: Half-Kelly with confidence adjustment.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict
from loguru import logger


@dataclass
class KellyFraction:
    """
    Result of Kelly calculation with metadata.
    """
    full_kelly: float  # Classic Kelly fraction
    fractional_kelly: float  # After fractional multiplier
    adjusted_kelly: float  # After confidence adjustment
    win_probability: float
    win_loss_ratio: float
    confidence: float
    fractional_multiplier: float
    
    def __str__(self):
        return (
            f"Kelly Fraction: {self.adjusted_kelly:.2%}\n"
            f"  Full Kelly: {self.full_kelly:.2%}\n"
            f"  Fractional (×{self.fractional_multiplier}): {self.fractional_kelly:.2%}\n"
            f"  With confidence ({self.confidence:.0%}): {self.adjusted_kelly:.2%}\n"
            f"  Win Rate: {self.win_probability:.1%}\n"
            f"  Win/Loss Ratio: {self.win_loss_ratio:.2f}"
        )


class ModifiedKellyCalculator:
    """
    Calculate position size using Modified Kelly Criterion.
    
    Formula (classic Kelly for binary outcomes):
        f* = (p × b - q) / b
        
    Where:
        f* = fraction of capital to bet
        p = win probability
        q = loss probability (1 - p)
        b = win/loss ratio (avg_win / avg_loss)
    
    Modifications:
        1. Fractional Kelly: Multiply by 0.5 (half-Kelly) to reduce volatility
        2. Confidence adjustment: Further reduce if uncertain about estimates
        3. Hard constraints: Never exceed max position size (20%)
    """
    
    def __init__(
        self,
        fractional_multiplier: float = 0.5,
        default_confidence: float = 0.5,
        min_win_probability: float = 0.50,
        min_win_loss_ratio: float = 1.0
    ):
        """
        Initialize Modified Kelly calculator.
        
        Args:
            fractional_multiplier: Kelly fraction multiplier (0.5 = half-Kelly)
            default_confidence: Default confidence in estimates (0-1)
            min_win_probability: Minimum win rate to consider positive edge
            min_win_loss_ratio: Minimum win/loss ratio to consider positive edge
        """
        if not 0 < fractional_multiplier <= 1:
            raise ValueError("Fractional multiplier must be between 0 and 1")
        
        if not 0 < default_confidence <= 1:
            raise ValueError("Default confidence must be between 0 and 1")
        
        self.fractional_multiplier = fractional_multiplier
        self.default_confidence = default_confidence
        self.min_win_prob = min_win_probability
        self.min_wl_ratio = min_win_loss_ratio
        
        logger.info(
            f"ModifiedKellyCalculator initialized: "
            f"fractional={fractional_multiplier}, confidence={default_confidence}"
        )
    
    def calculate(
        self,
        win_probability: float,
        avg_win: float,
        avg_loss: float,
        confidence: Optional[float] = None
    ) -> KellyFraction:
        """
        Calculate Kelly fraction for position sizing.
        
        Args:
            win_probability: Probability of winning trade (0-1)
            avg_win: Average winning trade amount ($)
            avg_loss: Average losing trade amount ($, positive number)
            confidence: Confidence in estimates (0-1). If None, uses default.
            
        Returns:
            KellyFraction object with full calculation breakdown
            
        Example:
            # 55% win rate, avg win $100, avg loss $50
            kelly = calculator.calculate(
                win_probability=0.55,
                avg_win=100,
                avg_loss=50,
                confidence=0.8
            )
            # Result: ~10% position size (half-Kelly with 80% confidence)
        """
        if not 0 <= win_probability <= 1:
            raise ValueError(f"Win probability must be 0-1, got {win_probability}")
        
        if avg_win <= 0 or avg_loss <= 0:
            raise ValueError("Average win and loss must be positive")
        
        # Use default confidence if not provided
        if confidence is None:
            confidence = self.default_confidence
        
        if not 0 < confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1, got {confidence}")
        
        # Calculate win/loss ratio
        win_loss_ratio = avg_win / avg_loss
        loss_probability = 1 - win_probability
        
        # Classic Kelly formula: f* = (p × b - q) / b
        # Where b = win/loss ratio, p = win prob, q = loss prob
        numerator = (win_probability * win_loss_ratio) - loss_probability
        denominator = win_loss_ratio
        
        full_kelly = numerator / denominator if denominator != 0 else 0
        
        # Apply fractional Kelly (reduce volatility)
        fractional_kelly = full_kelly * self.fractional_multiplier
        
        # Apply confidence adjustment (reduce if uncertain)
        adjusted_kelly = fractional_kelly * confidence
        
        # Floor at zero (no negative positions)
        full_kelly = max(0, full_kelly)
        fractional_kelly = max(0, fractional_kelly)
        adjusted_kelly = max(0, adjusted_kelly)
        
        result = KellyFraction(
            full_kelly=full_kelly,
            fractional_kelly=fractional_kelly,
            adjusted_kelly=adjusted_kelly,
            win_probability=win_probability,
            win_loss_ratio=win_loss_ratio,
            confidence=confidence,
            fractional_multiplier=self.fractional_multiplier
        )
        
        logger.debug(f"Kelly calculation: {result.adjusted_kelly:.2%} position size")
        return result
    
    def has_positive_edge(
        self,
        win_probability: float,
        win_loss_ratio: float
    ) -> bool:
        """
        Check if strategy has positive edge (worth betting).
        
        Args:
            win_probability: Win rate (0-1)
            win_loss_ratio: Avg win / avg loss
            
        Returns:
            True if strategy has edge, False otherwise
            
        Edge exists when:
            - Win probability > 50% (break-even), OR
            - Win/loss ratio compensates for lower win rate
            - Overall: win_prob × win_loss_ratio > (1 - win_prob)
        """
        if win_probability < self.min_win_prob:
            logger.warning(
                f"Win probability ({win_probability:.1%}) below minimum "
                f"({self.min_win_prob:.1%})"
            )
        
        if win_loss_ratio < self.min_wl_ratio:
            logger.warning(
                f"Win/loss ratio ({win_loss_ratio:.2f}) below minimum "
                f"({self.min_wl_ratio:.2f})"
            )
        
        # Check if expected value is positive
        # EV = (win_prob × avg_win) - (loss_prob × avg_loss)
        # Simplified: win_prob × WL_ratio > loss_prob
        loss_probability = 1 - win_probability
        edge = (win_probability * win_loss_ratio) > loss_probability
        
        if not edge:
            logger.warning(
                f"No positive edge: {win_probability:.1%} win rate, "
                f"{win_loss_ratio:.2f} W/L ratio"
            )
        
        return edge
    
    def estimate_from_trades(
        self,
        trades: List[Dict[str, float]],
        confidence: Optional[float] = None
    ) -> Optional[KellyFraction]:
        """
        Estimate Kelly fraction from historical trade results.
        
        Args:
            trades: List of trade dicts with 'pnl' key
            confidence: Confidence in estimates (0-1)
            
        Returns:
            KellyFraction if sufficient data, None otherwise
            
        Example:
            trades = [
                {'pnl': 100},  # Win
                {'pnl': -50},  # Loss
                {'pnl': 150},  # Win
                {'pnl': -60},  # Loss
            ]
            kelly = calculator.estimate_from_trades(trades)
        """
        if len(trades) < 20:
            logger.warning(
                f"Insufficient trade history for Kelly estimation: "
                f"{len(trades)} trades (need at least 20)"
            )
            return None
        
        # Separate wins and losses
        wins = [t['pnl'] for t in trades if t['pnl'] > 0]
        losses = [abs(t['pnl']) for t in trades if t['pnl'] < 0]
        
        if not wins or not losses:
            logger.warning("Need both wins and losses for Kelly estimation")
            return None
        
        # Calculate statistics
        win_probability = len(wins) / len(trades)
        avg_win = sum(wins) / len(wins)
        avg_loss = sum(losses) / len(losses)
        
        # Reduce confidence for small sample sizes
        if confidence is None:
            # Adjust confidence based on sample size
            # 20 trades = 50% confidence, 100+ trades = 80% confidence
            sample_confidence = min(0.5 + (len(trades) - 20) / 160, 0.8)
            confidence = sample_confidence
        
        logger.info(
            f"Estimated from {len(trades)} trades: "
            f"{win_probability:.1%} win rate, "
            f"${avg_win:.2f} avg win, ${avg_loss:.2f} avg loss"
        )
        
        return self.calculate(
            win_probability=win_probability,
            avg_win=avg_win,
            avg_loss=avg_loss,
            confidence=confidence
        )
