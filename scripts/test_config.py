#!/usr/bin/env python3
"""
Test configuration loading independently.
Does NOT require OpenD to be running.
"""
import sys
import os

# Add parent directory to path so we can import daemon modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Test config loading and display results."""
    print("=" * 60)
    print("Testing Configuration Loading")
    print("=" * 60)
    
    try:
        from daemon.config import ConfigLoader
        
        print("\n1. Loading config.yaml...")
        loader = ConfigLoader("./config/config.yaml")
        config = loader.load()
        print("   ✅ Config loaded successfully")
        
        print("\n2. Configuration Details:")
        print(f"   Execution mode: {config.execution_mode.value}")
        print(f"   Paper trading: {config.paper_trading}")
        print(f"   OpenD connection: {config.opend_host}:{config.opend_port}")
        
        print("\n3. Risk Settings:")
        print(f"   Max risk per trade: {config.risk.max_risk_per_trade_pct}%")
        print(f"   Max open positions: {config.risk.max_open_positions}")
        print(f"   Max sector exposure: {config.risk.max_sector_exposure_pct}%")
        print(f"   Min liquidity (avg volume): {config.risk.min_liquidity_avg_volume:,} shares/day")
        
        print("\n4. Position Sizing:")
        print(f"   Min notional per trade: ${config.sizing.min_notional_per_trade}")
        print(f"   Max notional per trade: ${config.sizing.max_notional_per_trade}")
        print(f"   Fractional shares: {config.sizing.fractional_shares}")
        print(f"   Min R:R ratio: {config.sizing.min_rr_ratio}")
        
        print("\n5. Loading environment variables...")
        secrets = ConfigLoader.load_secrets()
        
        if secrets.get("moomoo_user_id"):
            user_id = secrets["moomoo_user_id"]
            masked = user_id[:4] + "*" * (len(user_id) - 4) if len(user_id) > 4 else "****"
            print(f"   ✅ MOOMOO_USER_ID: {masked}")
        else:
            print("   ⚠️  MOOMOO_USER_ID not set in .env")
        
        if secrets.get("moomoo_password"):
            print(f"   ✅ MOOMOO_PASSWORD: ********")
        else:
            print("   ⚠️  MOOMOO_PASSWORD not set in .env")
        
        print(f"   Security firm: {secrets.get('moomoo_security_firm', 'FUTU')}")
        
        print("\n6. Validating secrets...")
        try:
            ConfigLoader.validate_secrets(secrets)
            print("   ✅ All required secrets present")
        except ValueError as e:
            print(f"   ❌ Validation failed: {e}")
            print("\n   Please edit .env file with your moomoo credentials")
            return 1
        
        print("\n" + "=" * 60)
        print("✅ Configuration is valid and ready to use!")
        print("=" * 60)
        
        print("\nNext step: Run the daemon (requires OpenD running):")
        print("  python -m daemon.main")
        
        return 0
    
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you're running this from the algomoomoo directory:")
        print("  cd algomoomoo")
        print("  python scripts/test_config.py")
        return 1
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
