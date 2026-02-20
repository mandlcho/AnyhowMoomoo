#!/usr/bin/env python3
"""
Setup verification script.
Checks that all dependencies are installed and importable.
Does NOT require OpenD to be running.
"""
import sys
import os

def check_python_version():
    """Check Python version is 3.10+."""
    print("Checking Python version...")
    version = sys.version_info
    print(f"  Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("  ❌ FAIL: Python 3.10+ required")
        return False
    
    print("  ✅ PASS")
    return True


def check_imports():
    """Check that all required packages can be imported."""
    print("\nChecking package imports...")
    
    packages = [
        ("pydantic", "Pydantic"),
        ("yaml", "PyYAML"),
        ("dotenv", "python-dotenv"),
        ("loguru", "Loguru"),
        ("futu", "futu-api"),
        ("pytest", "pytest"),
    ]
    
    all_ok = True
    for module_name, package_name in packages:
        try:
            __import__(module_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name} - run: pip install {package_name}")
            all_ok = False
    
    return all_ok


def check_project_structure():
    """Check that key files and directories exist."""
    print("\nChecking project structure...")
    
    required_paths = [
        "config/config.yaml",
        "daemon/main.py",
        "daemon/config.py",
        "data/models.py",
        "connectors/opend.py",
        "requirements.txt",
        ".env.example",
        ".gitignore",
    ]
    
    all_ok = True
    for path in required_paths:
        if os.path.exists(path):
            print(f"  ✅ {path}")
        else:
            print(f"  ❌ {path} - missing!")
            all_ok = False
    
    return all_ok


def check_env_file():
    """Check if .env file exists and has required fields."""
    print("\nChecking environment configuration...")
    
    if not os.path.exists(".env"):
        print("  ⚠️  .env file not found")
        print("     Run: cp .env.example .env")
        print("     Then edit .env with your credentials")
        return False
    
    print("  ✅ .env file exists")
    
    # Check if it has required keys (without reading actual values)
    with open(".env") as f:
        content = f.read()
    
    required_keys = ["MOOMOO_USER_ID", "MOOMOO_PASSWORD"]
    missing = []
    
    for key in required_keys:
        if key not in content:
            missing.append(key)
    
    if missing:
        print(f"  ⚠️  Missing keys in .env: {', '.join(missing)}")
        return False
    
    # Check if they're still placeholder values
    if "your_user_id" in content or "your_password" in content:
        print("  ⚠️  .env still has placeholder values")
        print("     Edit .env with your actual moomoo credentials")
        return False
    
    print("  ✅ .env appears configured")
    return True


def check_config_yaml():
    """Check if config.yaml is valid."""
    print("\nChecking config.yaml...")
    
    try:
        import yaml
        with open("config/config.yaml") as f:
            config = yaml.safe_load(f)
        
        print("  ✅ config.yaml is valid YAML")
        
        # Check key sections exist
        sections = ["execution", "opend", "account", "risk", "sizing"]
        for section in sections:
            if section in config:
                print(f"  ✅ Section '{section}' found")
            else:
                print(f"  ❌ Section '{section}' missing")
                return False
        
        return True
    
    except Exception as e:
        print(f"  ❌ Error reading config.yaml: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("AnyhowMoomoo Setup Verification")
    print("=" * 60)
    
    # Change to project root if we're in scripts/
    if os.path.basename(os.getcwd()) == "scripts":
        os.chdir("..")
    
    results = {
        "Python version": check_python_version(),
        "Package imports": check_imports(),
        "Project structure": check_project_structure(),
        "config.yaml": check_config_yaml(),
        ".env file": check_env_file(),
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check}")
    
    print("=" * 60)
    
    if all(results.values()):
        print("\n🎉 All checks passed! You're ready to go.")
        print("\nNext steps:")
        print("  1. If OpenD is installed and running:")
        print("     python -m daemon.main")
        print("\n  2. Or run unit tests (no OpenD required):")
        print("     pytest tests/unit/ -v")
        return 0
    else:
        print("\n⚠️  Some checks failed. See above for details.")
        print("\nRefer to SETUP.md for troubleshooting.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
