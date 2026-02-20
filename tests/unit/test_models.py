"""
Unit tests for Pydantic data models.
"""
import pytest
from decimal import Decimal
from datetime import datetime
from data.models import (
    OHLCV, MarketDataInterval, OrderRequest, OrderSide, OrderType,
    TradePlan, Position, PositionSide
)


def test_ohlcv_creation():
    """Test OHLCV model creation and validation."""
    bar = OHLCV(
        symbol="AAPL",
        timestamp=datetime.now(),
        open=Decimal("150.00"),
        high=Decimal("151.00"),
        low=Decimal("149.50"),
        close=Decimal("150.75"),
        volume=1000000,
        interval=MarketDataInterval.DAY_1,
    )
    assert bar.symbol == "AAPL"
    assert bar.close == Decimal("150.75")


def test_order_request_validation():
    """Test that OrderRequest validates quantity > 0."""
    with pytest.raises(ValueError):
        OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("-1"),  # Should fail
        )


def test_trade_plan_creation():
    """Test TradePlan model creation."""
    plan = TradePlan(
        plan_id="test-123",
        symbol="TSLA",
        direction=OrderSide.BUY,
        rationale="Test trade",
        timeframe="swing",
        entry_price=Decimal("200.00"),
        stop_price=Decimal("195.00"),
        target_prices=[Decimal("210.00")],
        allocation_risk_pct=Decimal("1.5"),
        created_at=datetime.now(),
    )
    assert plan.symbol == "TSLA"
    assert len(plan.target_prices) == 1
