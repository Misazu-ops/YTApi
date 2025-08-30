
FROM python:3.13.2-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Chrome for cookie support
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY tools.py .
COPY plugins/ ./plugins/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (FastAPI runs on port 8000 based on main.py)
EXPOSE 8000

# Health check for FastAPI endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Environment variables for the application
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Run the application (both FastAPI and Telegram bot)
CMD ["python3", "main.py"]
