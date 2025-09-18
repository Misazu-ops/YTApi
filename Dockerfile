
FROM python:3.13.2

# Set working directory
WORKDIR /app

# Install system dependencies including Tor
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    tor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create Tor configuration for frequent IP rotation
RUN echo "SocksPort 9050" > /etc/tor/torrc && \
    echo "MaxCircuitDirtiness 1" >> /etc/tor/torrc && \
    echo "NewCircuitPeriod 1" >> /etc/tor/torrc && \
    echo "CircuitBuildTimeout 5" >> /etc/tor/torrc && \
    echo "LearnCircuitBuildTimeout 0" >> /etc/tor/torrc && \
    echo "DisableAllSwap 1" >> /etc/tor/torrc && \
    echo "HardwareAccel 0" >> /etc/tor/torrc

# Copy application code
COPY . .

# Expose port (FastAPI runs on port 8000 based on main.py)
EXPOSE 8000

# Health check for FastAPI endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Environment variables for the application
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create startup script that runs Tor and the application
RUN echo '#!/bin/bash\n\
# Start Tor in background with frequent IP rotation\n\
echo "Starting Tor with 1-second IP rotation..."\n\
tor --runasdaemon 1 --SocksPort 9050 --MaxCircuitDirtiness 1 --NewCircuitPeriod 1 &\n\
\n\
# Wait for Tor to initialize\n\
sleep 3\n\
\n\
# Start IP rotation loop in background\n\
(\n\
  while true; do\n\
    sleep 1\n\
    # Send NEWNYM signal to get new IP\n\
    kill -HUP $(pgrep tor) 2>/dev/null || true\n\
  done\n\
) &\n\
\n\
# Check if git directory exists and pull updates\n\
if [ -d ".git" ]; then\n\
  echo "Pulling latest changes..."\n\
  git pull\n\
fi\n\
\n\
echo "Starting application..."\n\
python3 main.py' > start.sh && \
    chmod +x start.sh

# Default command
CMD ["./start.sh"]
