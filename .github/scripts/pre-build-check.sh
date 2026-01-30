#!/bin/bash
# Pre-build check for GitHub Actions
set -e

echo "🔍 Pre-build environment check..."

# Check required tools
echo "Checking required tools..."
for tool in curl unzip jq; do
    if command -v $tool >/dev/null 2>&1; then
        echo "✅ $tool available"
    else
        echo "❌ $tool not found"
        exit 1
    fi
done

# Check architecture
ARCH=$(uname -m)
echo "🏗️ Architecture: $ARCH"

# Check network connectivity
if curl -s --connect-timeout 5 --max-time 10 https://api.github.com >/dev/null 2>&1; then
    echo "✅ GitHub API accessible"
else
    echo "❌ GitHub API not accessible"
    exit 1
fi

echo "✅ Pre-build check passed"