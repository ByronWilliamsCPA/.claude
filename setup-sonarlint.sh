#!/bin/bash
# SonarLint Java Setup Script
# This script helps set up Java for SonarLint in VSCode

set -e

echo "=== SonarLint Java Setup ==="
echo ""

# Check current Java installation
echo "1. Checking for existing Java installation..."
if command -v java &> /dev/null; then
    echo "   ✓ Java found:"
    java -version
    echo ""
    echo "   SonarLint requires Java 17+. If your version is lower, continue with installation."
else
    echo "   ✗ Java not found"
fi

echo ""
echo "2. Installation options:"
echo ""
echo "   OPTION A: System-wide installation (recommended)"
echo "   Run: sudo apt update && sudo apt install -y openjdk-17-jre"
echo ""
echo "   OPTION B: Let SonarLint download Java automatically"
echo "   1. Open VSCode Command Palette (Ctrl+Shift+P)"
echo "   2. Search: 'SonarLint'"
echo "   3. Extension should prompt to download Java - click Allow/Download"
echo ""
echo "   OPTION C: Manual download (if sudo not available)"
echo "   1. Download from: https://adoptium.net/temurin/releases/?version=17"
echo "   2. Extract to: ~/.local/jdk-17"
echo "   3. Add to VSCode settings.json:"
echo '      "sonarlint.ls.javaHome": "~/.local/jdk-17"'
echo ""

# Offer to configure VSCode settings
echo "3. After Java is installed, reload VSCode:"
echo "   Ctrl+Shift+P → 'Developer: Reload Window'"
echo ""

# Create VSCode settings snippet
echo "4. Optional: VSCode settings for SonarLint (add to .vscode/settings.json):"
cat << 'EOF'
{
  "sonarlint.rules": {
    "python:S1192": {
      "level": "on"
    }
  },
  "sonarlint.output.showAnalyzerLogs": true
}
EOF
