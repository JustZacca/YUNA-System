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
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY main.py .

# Add src to Python path
ENV PYTHONPATH=/app/src

# Copy N_m3u8DL-RE installation script
COPY install_nm3u8_docker.sh .

# Install N_m3u8DL-RE
RUN chmod +x install_nm3u8_docker.sh && \
    ./install_nm3u8_docker.sh

# Create directories for mounted volumes
RUN mkdir -p /data /downloads

# Test N_m3u8DL-RE installation
RUN N_m3u8DL-RE --version || echo "⚠️ N_m3u8DL-RE installation test failed, will use ffmpeg fallback"

# Copy startup script
COPY start.sh .
RUN chmod +x start.sh

# Expose API port
EXPOSE 8000

# Start both API and bot
CMD ["./start.sh"]
