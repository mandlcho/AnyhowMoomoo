# ⚠️ START HERE ⚠️

## First Time Setup

**Before doing ANYTHING else, run:**

```bash
python scripts/verify_setup.py
```

This will:
- ✅ Check your Python version
- ✅ Verify all packages are installed
- ✅ Confirm project structure is intact
- ✅ Validate configuration files

## Why This Matters

The verification script catches 90% of common issues:
- Wrong Python version
- Missing dependencies
- Corrupted files
- Misconfigured environment

**It saves you time by finding problems early!**

## Quick Commands

```bash
# 1. ALWAYS RUN THIS FIRST
python scripts/verify_setup.py

# 2. If verification passes, configure credentials
cp .env.example .env
# Edit .env with your moomoo credentials

# 3. Test config (no OpenD needed)
python scripts/test_config.py

# 4. Run unit tests (no OpenD needed)
pytest tests/unit/ -v

# 5. Run the daemon (requires OpenD)
python -m daemon.main
```

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute express setup
- **[SETUP.md](SETUP.md)** - Detailed troubleshooting guide
- **[README.md](README.md)** - Project overview and architecture

## Need Help?

1. Run `python scripts/verify_setup.py` - it will tell you what's wrong
2. Check [SETUP.md](SETUP.md) for troubleshooting
3. Review error messages - they're designed to be helpful!

---

**Remember: Always run `verify_setup.py` after:**
- ✅ First clone
- ✅ Updating dependencies
- ✅ Pulling new changes
- ✅ Switching Python versions
- ✅ When something breaks
