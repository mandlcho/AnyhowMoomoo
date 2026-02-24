"""
Backtesting engine for strategy validation.

Features:
- Realistic fill simulation (VWAP-based fills)
- Commission and slippage modeling
- Position tracking with P&L
- Performance metrics calculation
"""

from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class Order:
    """Represents a trading order."""
    symbol: str
    side: OrderSide
    shares: float
    timestamp: datetime
    limit_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    fill_price: Optional[float] = None
    fill_timestamp: Optional[datetime] = None
    commission: float = 0.0
    
    @property
    def total_cost(self) -> float:
        """Total cost including commission."""
        if self.fill_price is None:
            return 0.0
        base_cost = self.shares * self.fill_price
        return base_cost + self.commission if self.side == OrderSide.BUY else base_cost - self.commission


@dataclass
class Position:
    """Represents an open position."""
    symbol: str
    shares: float
    entry_price: float
    entry_timestamp: datetime
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    
    def pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L."""
        return (current_price - self.entry_price) * self.shares
    
    def pnl_pct(self, current_price: float) -> float:
        """Calculate unrealized P&L %."""
        return (current_price - self.entry_price) / self.entry_price


@dataclass
class Trade:
    """Completed trade with entry and exit."""
    symbol: str
    entry_price: float
    exit_price: float
    shares: float
    entry_timestamp: datetime
    exit_timestamp: datetime
    pnl: float
    pnl_pct: float
    commission: float
    hold_days: int
    
    @property
    def is_winner(self) -> bool:
        return self.pnl > 0


@dataclass
class BacktestConfig:
    """Backtesting configuration."""
    initial_capital: float = 10000.0
    commission_per_share: float = 0.0  # $0 for moomoo
    commission_min: float = 0.0
    slippage_pct: float = 0.001  # 0.1% slippage
    use_vwap_fills: bool = True  # Use VWAP as fill price
    

@dataclass
class BacktestMetrics:
    """Performance metrics from backtest."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    win_loss_ratio: float
    total_pnl: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    profit_factor: float
    avg_hold_days: float
    
    def __str__(self):
        return f"""
Backtest Performance Metrics:
==============================
Total Trades:     {self.total_trades}
Winning Trades:   {self.winning_trades}
Losing Trades:    {self.losing_trades}
Win Rate:         {self.win_rate:.1%}

Average Win:      ${self.avg_win:.2f}
Average Loss:     ${self.avg_loss:.2f}
Win/Loss Ratio:   {self.win_loss_ratio:.2f}

Total P&L:        ${self.total_pnl:.2f}
Total Return:     {self.total_return_pct:.1%}
Sharpe Ratio:     {self.sharpe_ratio:.2f}

Max Drawdown:     ${self.max_drawdown:.2f} ({self.max_drawdown_pct:.1%})
Profit Factor:    {self.profit_factor:.2f}
Avg Hold Days:    {self.avg_hold_days:.1f}
"""


class BacktestEngine:
    """
    Backtesting engine with realistic fill simulation.
    """
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        """
        Initialize backtest engine.
        
        Args:
            config: Backtest configuration
        """
        self.config = config or BacktestConfig()
        
        # State
        self.cash = self.config.initial_capital
        self.equity = self.config.initial_capital
        self.positions: Dict[str, Position] = {}
        self.pending_orders: List[Order] = []
        self.filled_orders: List[Order] = []
        self.trades: List[Trade] = []
        
        # Equity curve for metrics
        self.equity_curve: List[float] = [self.config.initial_capital]
        self.equity_dates: List[datetime] = []
        
        logger.info(f"BacktestEngine initialized: ${self.config.initial_capital:.2f} capital")
    
    def reset(self):
        """Reset backtest state."""
        self.cash = self.config.initial_capital
        self.equity = self.config.initial_capital
        self.positions.clear()
        self.pending_orders.clear()
        self.filled_orders.clear()
        self.trades.clear()
        self.equity_curve = [self.config.initial_capital]
        self.equity_dates.clear()
        logger.debug("Backtest state reset")
    
    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        shares: float,
        timestamp: datetime,
        limit_price: Optional[float] = None
    ) -> Order:
        """
        Submit a new order.
        
        Args:
            symbol: Stock symbol
            side: Buy or sell
            shares: Number of shares
            timestamp: Order timestamp
            limit_price: Limit price (None = market order)
            
        Returns:
            Order object
        """
        order = Order(
            symbol=symbol,
            side=side,
            shares=shares,
            timestamp=timestamp,
            limit_price=limit_price
        )
        self.pending_orders.append(order)
        logger.debug(f"Order submitted: {side.value} {shares} {symbol} @ {timestamp}")
        return order
    
    def process_bar(
        self,
        symbol: str,
        timestamp: datetime,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        vwap: Optional[float] = None
    ):
        """
        Process a single bar and fill pending orders.
        
        Args:
            symbol: Stock symbol
            timestamp: Bar timestamp
            open_price: Open price
            high: High price
            low: Low price
            close: Close price
            volume: Volume
            vwap: VWAP (optional, used for fills if use_vwap_fills=True)
        """
        # Fill pending orders for this symbol
        filled = []
        for order in self.pending_orders:
            if order.symbol != symbol:
                continue
            
            # Determine fill price
            if self.config.use_vwap_fills and vwap is not None:
                # Use VWAP with slippage
                slippage = vwap * self.config.slippage_pct
                fill_price = vwap + slippage if order.side == OrderSide.BUY else vwap - slippage
            else:
                # Use open price with slippage
                slippage = open_price * self.config.slippage_pct
                fill_price = open_price + slippage if order.side == OrderSide.BUY else open_price - slippage
            
            # Check if limit order would fill
            if order.limit_price is not None:
                if order.side == OrderSide.BUY and fill_price > order.limit_price:
                    continue  # Buy limit not met
                if order.side == OrderSide.SELL and fill_price < order.limit_price:
                    continue  # Sell limit not met
            
            # Check if price within bar range
            if fill_price < low or fill_price > high:
                fill_price = np.clip(fill_price, low, high)
            
            # Calculate commission
            commission = max(
                self.config.commission_min,
                order.shares * self.config.commission_per_share
            )
            
            # Execute fill
            order.fill_price = fill_price
            order.fill_timestamp = timestamp
            order.commission = commission
            order.status = OrderStatus.FILLED
            
            # Update positions and cash
            if order.side == OrderSide.BUY:
                self._open_position(order)
            else:
                self._close_position(order)
            
            filled.append(order)
            self.filled_orders.append(order)
        
        # Remove filled orders
        for order in filled:
            self.pending_orders.remove(order)
        
        # Update equity curve
        self._update_equity(timestamp, {symbol: close})
    
    def _open_position(self, order: Order):
        """Open a new position from filled buy order."""
        cost = order.total_cost
        
        if cost > self.cash:
            logger.warning(f"Insufficient cash: need ${cost:.2f}, have ${self.cash:.2f}")
            return
        
        self.cash -= cost
        
        position = Position(
            symbol=order.symbol,
            shares=order.shares,
            entry_price=order.fill_price,
            entry_timestamp=order.fill_timestamp
        )
        self.positions[order.symbol] = position
        
        logger.debug(
            f"Position opened: {order.shares} {order.symbol} @ ${order.fill_price:.2f}"
        )
    
    def _close_position(self, order: Order):
        """Close position from filled sell order."""
        if order.symbol not in self.positions:
            logger.warning(f"No position to close for {order.symbol}")
            return
        
        position = self.positions[order.symbol]
        proceeds = order.shares * order.fill_price - order.commission
        self.cash += proceeds
        
        # Record trade
        pnl = (order.fill_price - position.entry_price) * order.shares - order.commission
        pnl_pct = (order.fill_price - position.entry_price) / position.entry_price
        hold_days = (order.fill_timestamp - position.entry_timestamp).days
        
        trade = Trade(
            symbol=order.symbol,
            entry_price=position.entry_price,
            exit_price=order.fill_price,
            shares=order.shares,
            entry_timestamp=position.entry_timestamp,
            exit_timestamp=order.fill_timestamp,
            pnl=pnl,
            pnl_pct=pnl_pct,
            commission=order.commission,
            hold_days=hold_days
        )
        self.trades.append(trade)
        
        # Remove position
        del self.positions[order.symbol]
        
        logger.debug(
            f"Position closed: {order.symbol} P&L=${pnl:.2f} ({pnl_pct:.1%})"
        )
    
    def _update_equity(self, timestamp: datetime, prices: Dict[str, float]):
        """Update equity curve."""
        position_value = sum(
            pos.shares * prices.get(pos.symbol, pos.entry_price)
            for pos in self.positions.values()
        )
        self.equity = self.cash + position_value
        self.equity_curve.append(self.equity)
        self.equity_dates.append(timestamp)
    
    def calculate_metrics(self) -> BacktestMetrics:
        """
        Calculate performance metrics.
        
        Returns:
            BacktestMetrics object
        """
        if not self.trades:
            return BacktestMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_win=0.0,
                avg_loss=0.0,
                win_loss_ratio=0.0,
                total_pnl=0.0,
                total_return_pct=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                max_drawdown_pct=0.0,
                profit_factor=0.0,
                avg_hold_days=0.0
            )
        
        # Basic stats
        total_trades = len(self.trades)
        winners = [t for t in self.trades if t.is_winner]
        losers = [t for t in self.trades if not t.is_winner]
        
        winning_trades = len(winners)
        losing_trades = len(losers)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        avg_win = np.mean([t.pnl for t in winners]) if winners else 0.0
        avg_loss = np.mean([t.pnl for t in losers]) if losers else 0.0
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
        
        # Returns
        total_pnl = sum(t.pnl for t in self.trades)
        total_return_pct = total_pnl / self.config.initial_capital
        
        # Sharpe ratio (assuming daily returns)
        if len(self.equity_curve) > 1:
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = running_max - equity_array
        max_drawdown = np.max(drawdown)
        max_drawdown_pct = max_drawdown / np.max(running_max) if np.max(running_max) > 0 else 0.0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # Hold time
        avg_hold_days = np.mean([t.hold_days for t in self.trades])
        
        return BacktestMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            win_loss_ratio=win_loss_ratio,
            total_pnl=total_pnl,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            profit_factor=profit_factor,
            avg_hold_days=avg_hold_days
        )
    
    def get_equity_curve_df(self) -> pd.DataFrame:
        """Get equity curve as DataFrame."""
        return pd.DataFrame({
            'timestamp': self.equity_dates,
            'equity': self.equity_curve[1:]  # Skip initial capital
        })
    
    def get_trades_df(self) -> pd.DataFrame:
        """Get all trades as DataFrame."""
        if not self.trades:
            return pd.DataFrame()
        
        return pd.DataFrame([
            {
                'symbol': t.symbol,
                'entry_date': t.entry_timestamp,
                'exit_date': t.exit_timestamp,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'shares': t.shares,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'hold_days': t.hold_days,
                'win': t.is_winner
            }
            for t in self.trades
        ])
