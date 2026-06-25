FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build dependencies (only in builder stage)
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    python3-dev \
    py3-setuptools

# Copy requirements
COPY requirements.txt .

# Install Python dependencies to a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


FROM python:3.11-alpine

WORKDIR /app

# Install only runtime dependencies
RUN apk add --no-cache \
    curl \
    postgresql-client

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

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
