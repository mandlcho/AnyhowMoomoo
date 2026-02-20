"""
Unit tests for configuration loading.
"""
import pytest
from decimal import Decimal
from daemon.config import ConfigLoader
from data.models import ExecutionMode


def test_config_loads():
    """Test that config loads without errors."""
    loader = ConfigLoader("./config/config.yaml")
    config = loader.load()
    
    assert config.execution_mode in [ExecutionMode.SEMI_AUTOMATIC, ExecutionMode.AUTOMATIC]
    assert config.risk.max_risk_per_trade_pct > 0
    assert config.sizing.min_notional_per_trade > 0
    assert config.paper_trading is True  # Default should be paper trading


def test_automatic_mode_applies_overrides():
    """Test that AUTOMATIC mode uses stricter limits."""
    # This test requires a fixture or test config
    # TODO: Implement with test fixtures
    pass


@pytest.mark.skip(reason="Requires .env file")
def test_secrets_validation():
    """Test that missing secrets raise error."""
    secrets = {"moomoo_user_id": None}
    with pytest.raises(ValueError):
        ConfigLoader.validate_secrets(secrets)
