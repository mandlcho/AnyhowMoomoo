"""
Integration tests for OpenD connection.
Requires OpenD running locally.
"""
import pytest
from connectors.opend import OpenDConnection


@pytest.mark.integration
@pytest.mark.skip(reason="Requires OpenD running on localhost:11111")
def test_quote_connection():
    """Test quote context connection."""
    conn = OpenDConnection(host="127.0.0.1", port=11111)
    
    try:
        quote_ctx = conn.connect_quote()
        assert quote_ctx is not None
        
        # Try a simple query (requires valid OpenD)
        # ret, data = quote_ctx.get_market_state(['US.AAPL'])
        # assert ret == 0
        
    finally:
        conn.disconnect()


@pytest.mark.integration
@pytest.mark.skip(reason="Requires valid credentials")
def test_trade_connection():
    """Test trade context connection and unlock."""
    # This would use test credentials from env
    pass


@pytest.mark.integration
def test_health_check():
    """Test basic health check."""
    conn = OpenDConnection()
    health = conn.health_check()
    
    assert "quote_connected" in health
    assert "trade_connected" in health
