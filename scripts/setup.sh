#!/bin/bash
# Setup script for OKR-Jira analysis system

set -e

echo "Setting up OKR-Jira Analysis System..."
echo "======================================"

# Check if we're in the project root
if [ ! -f "requirements.txt" ]; then
    echo "Error: Please run this script from the project root directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f "config/.env" ]; then
    echo "Creating config/.env file..."
    cp config/.env.example config/.env
    echo ""
    echo "⚠️  IMPORTANT: Please edit config/.env and add your API keys:"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - SLACK_WEBHOOK_URL (optional)"
    echo ""
fi

# Create output directories
mkdir -p output/reports
mkdir -p output/data

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit config/.env with your API keys"
echo "  2. Ensure acli is installed and authenticated:"
echo "     - Install: brew install atlassian-cli"
echo "     - Login: acli auth login"
echo "  3. Run: python -m src.main"
