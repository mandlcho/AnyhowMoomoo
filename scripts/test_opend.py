#!/usr/bin/env python3
"""
Test OpenD connection.
REQUIRES OpenD to be running on localhost:11111.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Test OpenD connection."""
    print("=" * 60)
    print("Testing OpenD Connection")
    print("=" * 60)
    
    print("\n⚠️  This test requires:")
    print("  - OpenD installed and running on localhost:11111")
    print("  - Valid moomoo credentials in .env file")
    print()
    
    try:
        from daemon.config import ConfigLoader
        from connectors.opend import OpenDConnection
        
        # Load config and secrets
        print("1. Loading configuration...")
        config_loader = ConfigLoader()
        config = config_loader.load()
        secrets = ConfigLoader.load_secrets()
        ConfigLoader.validate_secrets(secrets)
        print("   ✅ Config loaded")
        
        # Create connection
        print(f"\n2. Connecting to OpenD at {config.opend_host}:{config.opend_port}...")
        conn = OpenDConnection(
            host=config.opend_host,
            port=config.opend_port,
            paper_trading=config.paper_trading,
        )
        
        try:
            # Test quote context
            print("\n3. Testing quote context...")
            quote_ctx = conn.connect_quote()
            print("   ✅ Quote context connected")
            
            # Test trade context
            print("\n4. Testing trade context...")
            trade_ctx = conn.connect_trade(
                user_id=secrets["moomoo_user_id"],
                password=secrets["moomoo_password"],
                security_firm=secrets["moomoo_security_firm"],
            )
            print("   ✅ Trade context connected and unlocked")
            
            # Health check
            print("\n5. Running health check...")
            health = conn.health_check()
            print(f"   Quote connected: {health['quote_connected']}")
            print(f"   Trade connected: {health['trade_connected']}")
            
            if all(health.values()):
                print("   ✅ Health check passed")
            else:
                print("   ⚠️  Some connections failed")
            
            print("\n" + "=" * 60)
            print("✅ OpenD connection test successful!")
            print("=" * 60)
            
            print("\nYou're ready to run the daemon:")
            print("  python -m daemon.main")
            
        finally:
            print("\n6. Disconnecting...")
            conn.disconnect()
            print("   ✅ Disconnected cleanly")
        
        return 0
    
    except ConnectionError as e:
        print(f"\n❌ Connection error: {e}")
        print("\nTroubleshooting:")
        print("  1. Check OpenD is running:")
        print("     netstat -an | findstr 11111  (Windows)")
        print("     lsof -i :11111               (Mac/Linux)")
        print("\n  2. Verify OpenD is listening on localhost:11111")
        print("\n  3. Check your credentials in .env file")
        print("\n  4. Review OpenD logs for errors")
        return 1
    
    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        print("\nMake sure you're in the algomoomoo directory:")
        print("  cd algomoomoo")
        print("  python scripts/test_opend.py")
        return 1
    
    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nCheck your .env file has valid credentials")
        return 1
    
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("\nDid you install dependencies?")
        print("  pip install -r requirements.txt")
        return 1
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
