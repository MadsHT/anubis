FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for PDF parsing with Docling + OpenCV
# These are needed by:
# - docling-parse (PDF extraction with pypdfium2)
# - rapidocr (optical character recognition via OpenCV)
# - Pillow (image processing)
# - OpenGL support for document layout analysis
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    libglib2.0-0t64 \
    libx11-6 \
    libxcb1 \
    libxau6 \
    libxdmcp6 \
    libdrm2 \
    libgcc-s1 \
    libstdc++6 \
    libpcre2-8-0 \
    libpng16-16t64 \
    libz1 \
    libglvnd0 \
    libglx0 \
    libgldispatch0 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements (production only, no test deps)
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
