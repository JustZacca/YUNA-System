#!/bin/bash
# Enhanced N_m3u8DL-RE Installation Script for Docker Build
# More robust error handling and fallbacks

set -euo pipefail

echo "🚀 Installing N_m3u8DL-RE..."

# Detect architecture
ARCH=$(case $(uname -m) in 
    x86_64) echo "x64" ;; 
    aarch64) echo "arm64" ;; 
    armv7l) echo "arm" ;; 
    *) echo "x64" ;; 
esac)

echo "📦 Detected architecture: ${ARCH}"

# Function to try downloading with different methods
download_with_retry() {
    local url="$1"
    local max_retries="${2:-3}"
    local retry_count=0
    
    while [ $retry_count -lt $max_retries ]; do
        echo "📥 Attempting download (attempt $((retry_count + 1))/$max_retries)..."
        
        if curl -L --connect-timeout 30 --max-time 300 --retry 2 --retry-delay 5 \
           --fail --show-error --silent --location "$url" -o N_m3u8DL-RE.zip; then
            echo "✅ Download successful"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        echo "⚠️ Download attempt $retry_count failed"
        sleep 2
    done
    
    echo "❌ All download attempts failed"
    return 1
}

# Function to get version with multiple fallbacks
get_version() {
    echo "🔍 Getting latest version..."
    
    # Method 1: GitHub API with jq (preferred)
    if command -v jq >/dev/null 2>&1; then
        VERSION=$(curl -s --connect-timeout 10 --max-time 30 \
                   "https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest" \
                   2>/dev/null | jq -r '.tag_name' 2>/dev/null || true)
    fi
    
    # Method 2: GitHub API with grep/sed (fallback)
    if [ -z "$VERSION" ]; then
        VERSION=$(curl -s --connect-timeout 10 --max-time 30 \
                   "https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest" \
                   2>/dev/null | grep '"tag_name"' | cut -d '"' -f 4 2>/dev/null || true)
    fi
    
    # Method 3: Known recent version (last resort)
    if [ -z "$VERSION" ]; then
        echo "⚠️ Could not fetch version from GitHub API, using fallback"
        VERSION="v20241201"
    fi
    
    echo "📦 Using version: ${VERSION}"
    echo "$VERSION"
}

# Get version
VERSION=$(get_version)

# Construct download URL
DOWNLOAD_URL="https://github.com/nilaoda/N_m3u8DL-RE/releases/download/${VERSION}/N_m3u8DL-RE_linux-${ARCH}_net.zip"

echo "🌐 Download URL: ${DOWNLOAD_URL}"

# Download with retry
if ! download_with_retry "$DOWNLOAD_URL"; then
    echo "❌ Failed to download N_m3u8DL-RE"
    exit 1
fi

# Extract and install
echo "📂 Extracting..."
unzip -q N_m3u8DL-RE.zip

if [ ! -f "N_m3u8DL-RE" ]; then
    echo "❌ N_m3u8DL-RE binary not found in archive"
    ls -la
    exit 1
fi

echo "🔧 Installing..."
chmod +x N_m3u8DL-RE
mv N_m3u8DL-RE /usr/local/bin/

# Clean up
rm -f N_m3u8DL-RE.zip

# Verify installation
echo "🧪 Verifying installation..."
if [ -f "/usr/local/bin/N_m3u8DL-RE" ]; then
    echo "✅ N_m3u8DL-RE ${VERSION} installed successfully"
    
    # Test if it works (non-fatal)
    if timeout 10 /usr/local/bin/N_m3u8DL-RE --version >/dev/null 2>&1; then
        echo "🎯 Installation test passed"
        VERSION_OUTPUT=$(/usr/local/bin/N_m3u8DL-RE --version 2>/dev/null || echo "Unknown")
        echo "📋 Version: ${VERSION_OUTPUT}"
    else
        echo "⚠️ Installation test failed, but binary is present"
    fi
else
    echo "❌ Installation failed - binary not found at /usr/local/bin/N_m3u8DL-RE"
    exit 1
fi