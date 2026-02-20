"""
Trading daemon entry point.
Phase 1: Basic scaffolding, OpenD connection, health checks.
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logging(log_dir: str, level: str = "INFO"):
    """Configure loguru with rotation and separate trade audit log."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    logger.remove()
    
    # Console
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    
    # File (all logs)
    logger.add(
        log_path / "daemon.log",
        level=level,
        rotation="1 day",
        retention="30 days",
        compression="gz",
    )
    
    # Trade audit trail (for future)
    logger.add(
        log_path / "trades.log",
        level="INFO",
        filter=lambda r: "TRADE" in r["extra"],
        rotation="1 week",
        retention="1 year",
    )


def run_startup_checks():
    """Run basic startup checks before proceeding."""
    import os
    
    checks_passed = True
    
    # Check required files exist
    required_files = [
        "config/config.yaml",
        "data/models.py",
        "daemon/config.py",
        "connectors/opend.py",
    ]
    
    for filepath in required_files:
        if not os.path.exists(filepath):
            print(f"❌ Missing required file: {filepath}")
            checks_passed = False
    
    if not checks_passed:
        print("\n⚠️  Startup checks failed!")
        print("\nRun this to diagnose the issue:")
        print("  python scripts/verify_setup.py")
        return False
    
    return True


def main():
    """Main daemon loop."""
    # Quick startup checks
    print("Running startup checks...")
    if not run_startup_checks():
        return 1
    print("✅ Startup checks passed\n")
    
    from daemon.config import ConfigLoader
    from connectors.opend import OpenDConnection
    
    # Load configuration
    config_loader = ConfigLoader()
    config = config_loader.load()
    secrets = ConfigLoader.load_secrets()
    ConfigLoader.validate_secrets(secrets)
    
    # Setup logging
    setup_logging(config.log_dir)
    
    logger.info("=" * 60)
    logger.info("Trading Daemon Starting - Phase 1")
    logger.info("=" * 60)
    logger.info(f"Execution mode: {config.execution_mode.value}")
    logger.info(f"Paper trading: {config.paper_trading}")
    logger.info(f"Max risk per trade: {config.risk.max_risk_per_trade_pct}%")
    
    # Test OpenD connection
    logger.info("Testing OpenD connection...")
    
    try:
        with OpenDConnection(
            host=config.opend_host,
            port=config.opend_port,
            paper_trading=config.paper_trading,
        ) as conn:
            # Connect to quote context
            quote_ctx = conn.connect_quote()
            logger.info("✓ Quote context connected")
            
            # Connect to trade context
            trade_ctx = conn.connect_trade(
                user_id=secrets["moomoo_user_id"],
                password=secrets["moomoo_password"],
                security_firm=secrets["moomoo_security_firm"],
            )
            logger.info("✓ Trade context connected and unlocked")
            
            # Health check
            health = conn.health_check()
            logger.info(f"Health check: {health}")
            
            # TODO: Phase 2 - Start data fetcher
            # TODO: Phase 3 - Start strategy loop
            # TODO: Phase 5 - Start UI server
            
            logger.info("Daemon ready. Press Ctrl+C to stop.")
            
            # Simple keepalive loop
            import time
            while True:
                time.sleep(10)
                logger.debug("Heartbeat")
                
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1
    finally:
        logger.info("=" * 60)
        logger.info("Trading Daemon Stopped")
        logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
