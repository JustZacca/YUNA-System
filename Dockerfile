# YUNA-System Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install N_m3u8DL-RE
RUN echo "Installing N_m3u8DL-RE..." && \
    ARCH=$(case $(uname -m) in x86_64) echo "x64" ;; aarch64) echo "arm64" ;; *) echo "x64" ;; esac) && \
    VERSION=$(curl -s https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest | grep '"tag_name"' | cut -d '"' -f 4 | sed 's/v//') && \
    curl -L -o N_m3u8DL-RE.zip "https://github.com/nilaoda/N_m3u8DL-RE/releases/download/v${VERSION}/N_m3u8DL-RE_linux-${ARCH}_net.zip" && \
    unzip N_m3u8DL-RE.zip && \
    chmod +x N_m3u8DL-RE && \
    mv N_m3u8DL-RE /usr/local/bin/ && \
    rm N_m3u8DL-RE.zip && \
    echo "✅ N_m3u8DL-RE v${VERSION} installed successfully"

# Copy application code
COPY src/ ./src/
COPY main.py .

# Add src to Python path
ENV PYTHONPATH=/app/src

# Create directories for mounted volumes
RUN mkdir -p /data /downloads

# Test N_m3u8DL-RE installation
RUN N_m3u8DL-RE --version

# Default command
CMD ["python", "main.py"]
