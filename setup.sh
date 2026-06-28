#!/bin/bash
# Setup script for BetterCode

set -e

echo "=================================="
echo "BetterSupport Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed"
    exit 1
fi

# Check if ripgrep is installed
echo ""
echo "Checking for ripgrep..."
if ! command -v rg &> /dev/null; then
    echo "Warning: ripgrep is not installed"
    echo "Please install it:"
    echo "  macOS:    brew install ripgrep"
    echo "  Ubuntu:   sudo apt-get install ripgrep"
    echo "  Windows:  choco install ripgrep"
    echo ""
    read -p "Press Enter to continue anyway or Ctrl+C to exit..."
else
    echo "ripgrep is installed ✓"
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Create projects directory
echo ""
echo "Creating projects directory..."
mkdir -p projects

# Check for environment variables
echo ""
echo "Checking environment variables..."

missing_vars=()

if [ -z "$SLACK_SIGNING_SECRET" ]; then
    missing_vars+=("SLACK_SIGNING_SECRET")
fi

if [ -z "$BETTERSUPPORT_SLACK_BOT_TOKEN" ]; then
    missing_vars+=("BETTERSUPPORT_SLACK_BOT_TOKEN")
fi

if [ -z "$BETTERSUPPORT_LLM_OPENAI_API_KEY" ]; then
    missing_vars+=("BETTERSUPPORT_LLM_OPENAI_API_KEY")
fi

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo ""
    echo "⚠️  Missing environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Set them before running the server:"
    echo ""
    echo "  export SLACK_SIGNING_SECRET=..."
    echo "  export BETTERSUPPORT_SLACK_BOT_TOKEN=..."
    echo "  export BETTERSUPPORT_LLM_OPENAI_API_KEY=..."
    echo ""
else
    echo "All required environment variables are set ✓"
fi

# Setup complete
echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your projects in config.yaml"
echo ""
echo "2. Test without Slack:"
echo "   BETTERSUPPORT_LLM_OPENAI_API_KEY=sk-... python test_agent.py"
echo ""
echo "3. Run local server:"
echo "   SLACK_SIGNING_SECRET=... \\"
echo "   BETTERSUPPORT_SLACK_BOT_TOKEN=... \\"
echo "   BETTERSUPPORT_LLM_OPENAI_API_KEY=... \\"
echo "   python local-server.py"
echo ""
echo "4. Setup ngrok:"
echo "   ngrok http 3000"
echo ""
echo "5. Configure Slack app with ngrok URL"
echo ""
