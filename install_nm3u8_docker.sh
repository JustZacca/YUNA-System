#!/bin/bash
# N_m3u8DL-RE Installation Script for Docker Build
# Fallback installation approach

set -e

echo "🚀 Installing N_m3u8DL-RE..."

# Detect architecture
ARCH=$(case $(uname -m) in 
    x86_64) echo "x64" ;; 
    aarch64) echo "arm64" ;; 
    armv7l) echo "arm" ;; 
    *) echo "x64" ;; 
esac)

echo "📦 Detected architecture: ${ARCH}"

# Try multiple approaches to get the latest version
echo "🔍 Getting latest version..."

# Method 1: GitHub API with jq
if command -v jq >/dev/null 2>&1; then
    VERSION=$(curl -s https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest | jq -r '.tag_name' 2>/dev/null || true)
fi

# Method 2: GitHub API with grep/sed (fallback)
if [ -z "$VERSION" ]; then
    VERSION=$(curl -s https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest | grep '"tag_name"' | cut -d '"' -f 4 2>/dev/null || true)
fi

# Method 3: Use a known recent version if API fails
if [ -z "$VERSION" ]; then
    echo "⚠️ Could not fetch latest version from GitHub API, using fallback version"
    VERSION="v20241201"
fi

echo "📥 Downloading version: ${VERSION}"

# Construct download URL
DOWNLOAD_URL="https://github.com/nilaoda/N_m3u8DL-RE/releases/download/${VERSION}/N_m3u8DL-RE_linux-${ARCH}_net.zip"

# Download the file
echo "⬇️ Downloading from: ${DOWNLOAD_URL}"
curl -L -o N_m3u8DL-RE.zip "${DOWNLOAD_URL}"

# Extract and install
echo "📂 Extracting..."
unzip -q N_m3u8DL-RE.zip

if [ -f "N_m3u8DL-RE" ]; then
    chmod +x N_m3u8DL-RE
    mv N_m3u8DL-RE /usr/local/bin/
    rm N_m3u8DL-RE.zip
    echo "✅ N_m3u8DL-RE ${VERSION} installed successfully"
    
    # Test installation
    if /usr/local/bin/N_m3u8DL-RE --version >/dev/null 2>&1; then
        echo "🧪 Installation test passed"
    else
        echo "⚠️ Installation test failed, but binary is present"
    fi
else
    echo "❌ N_m3u8DL-RE binary not found in archive"
    rm -f N_m3u8DL-RE.zip
    exit 1
fi