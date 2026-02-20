#!/bin/bash
# One-command setup script for AnyhowMoomoo
# Usage: bash setup.sh

set -e  # Exit on error

echo "=========================================="
echo "AnyhowMoomoo - Automated Setup"
echo "=========================================="
echo ""

# Check Python version
echo "1. Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found: Python $python_version"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "   ❌ ERROR: Python 3.10+ required"
    exit 1
fi
echo "   ✅ Python version OK"
echo ""

# Install dependencies
echo "2. Installing dependencies..."
pip install -r requirements.txt --quiet
echo "   ✅ Dependencies installed"
echo ""

# Create .env from template if it doesn't exist
echo "3. Setting up environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "   ✅ .env file created from template"
    echo "   ⚠️  IMPORTANT: Edit .env with your moomoo credentials!"
else
    echo "   ℹ️  .env file already exists, skipping"
fi
echo ""

# Run verification
echo "4. Running setup verification..."
echo ""
python scripts/verify_setup.py
echo ""

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your moomoo credentials"
echo "2. Run: python scripts/test_config.py"
echo "3. Run: python -m daemon.main (when OpenD is running)"
echo ""
echo "Documentation:"
echo "- START_HERE.md    - Quick overview"
echo "- QUICKSTART.md    - 5-minute guide"
echo "- SETUP.md         - Detailed troubleshooting"
echo ""
