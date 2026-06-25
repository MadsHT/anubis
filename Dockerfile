FROM python:3.11-alpine AS builder

FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    libxcb1 \
    libx11-6 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY anubis/ ./anubis/
COPY config.yaml .
COPY entrypoint.sh .

# Create necessary directories
RUN mkdir -p /documents /app/logs /app/data && chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the entrypoint script which handles pgvector setup and starts the server
ENTRYPOINT ["/app/entrypoint.sh"]
