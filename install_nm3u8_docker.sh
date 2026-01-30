#!/bin/bash
# N_m3u8DL-RE Installation Script for Docker Build
# Fetches the correct download URL from GitHub API

set -euo pipefail

echo "🚀 Installing N_m3u8DL-RE..."

# Detect architecture
ARCH=$(case $(uname -m) in
    x86_64) echo "linux-x64" ;;
    aarch64) echo "linux-arm64" ;;
    armv7l) echo "linux-arm" ;;
    *) echo "linux-x64" ;;
esac)

echo "📦 Detected architecture: ${ARCH}"

# Get download URL from GitHub API
echo "🔍 Fetching latest release info..."

DOWNLOAD_URL=""

if command -v jq >/dev/null 2>&1; then
    # Use jq to find the correct asset URL
    DOWNLOAD_URL=$(curl -s --connect-timeout 15 --max-time 60 \
        "https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest" \
        | jq -r ".assets[] | select(.name | contains(\"${ARCH}\") and (contains(\".tar.gz\") or contains(\".zip\"))) | .browser_download_url" \
        | head -1)
fi

# Fallback: grep if jq failed
if [ -z "$DOWNLOAD_URL" ]; then
    echo "⚠️ jq method failed, trying grep..."
    # Use Perl regex if available, otherwise basic grep
    if grep -P "" /dev/null 2>/dev/null; then
        DOWNLOAD_URL=$(curl -s --connect-timeout 15 --max-time 60 \
            "https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest" \
            | grep -oP '"browser_download_url": "\K[^"]*'"${ARCH}"'[^"]*\.tar\.gz' \
            | grep -v musl | head -1 || true)
    else
        DOWNLOAD_URL=$(curl -s --connect-timeout 15 --max-time 60 \
            "https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest" \
            | grep "${ARCH}" | grep "browser_download_url" | grep -v musl \
            | sed 's/.*"browser_download_url": "\([^"]*\)".*/\1/' \
            | head -1 || true)
    fi
fi

# Last resort: hardcoded known working URL
if [ -z "$DOWNLOAD_URL" ]; then
    echo "⚠️ Could not fetch from API, using fallback URL"
    DOWNLOAD_URL="https://github.com/nilaoda/N_m3u8DL-RE/releases/download/v0.5.1-beta/N_m3u8DL-RE_v0.5.1-beta_linux-x64_20251029.tar.gz"
fi

echo "🌐 Download URL: ${DOWNLOAD_URL}"

# Download with retry
download_file() {
    local url="$1"
    local output="$2"
    local max_retries=3
    local retry_count=0

    while [ $retry_count -lt $max_retries ]; do
        echo "📥 Attempting download (attempt $((retry_count + 1))/$max_retries)..."

        if curl -L --connect-timeout 30 --max-time 300 --retry 2 \
           --fail --show-error --silent "$url" -o "$output"; then
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

# Determine file extension and download
FILENAME=$(basename "$DOWNLOAD_URL")

if ! download_file "$DOWNLOAD_URL" "$FILENAME"; then
    echo "❌ Failed to download N_m3u8DL-RE"
    exit 1
fi

# Extract based on file type
echo "📂 Extracting..."
if [[ "$FILENAME" == *.tar.gz ]]; then
    tar -xzf "$FILENAME"
elif [[ "$FILENAME" == *.zip ]]; then
    unzip -q "$FILENAME"
else
    echo "❌ Unknown archive format: $FILENAME"
    exit 1
fi

# Find and install the binary
BINARY=$(find . -maxdepth 1 -name "N_m3u8DL-RE" -type f 2>/dev/null | head -1)

if [ -z "$BINARY" ] || [ ! -f "$BINARY" ]; then
    echo "❌ N_m3u8DL-RE binary not found in archive"
    echo "Contents:"
    ls -la
    exit 1
fi

echo "🔧 Installing..."
chmod +x "$BINARY"
mv "$BINARY" /usr/local/bin/N_m3u8DL-RE

# Clean up
rm -f "$FILENAME"
rm -f *.md *.txt 2>/dev/null || true

# Verify installation
echo "🧪 Verifying installation..."
if [ -f "/usr/local/bin/N_m3u8DL-RE" ]; then
    echo "✅ N_m3u8DL-RE installed successfully"

    # Test execution (non-fatal)
    if timeout 10 /usr/local/bin/N_m3u8DL-RE --version >/dev/null 2>&1; then
        echo "🎯 Installation test passed"
        /usr/local/bin/N_m3u8DL-RE --version 2>/dev/null || true
    else
        echo "⚠️ Binary present but test execution failed (may need runtime deps)"
    fi
else
    echo "❌ Installation failed - binary not found"
    exit 1
fi
