# ============= MULTI-STAGE BUILD FOR OPTIMAL CACHING ============= #

# Stage 1: Base image with system dependencies
FROM python:3.11-slim as base

# Install system dependencies (cached unless system packages change)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Stage 2: Dependencies layer (heavily cached)
FROM base as dependencies

WORKDIR /app

# Copy ONLY requirements first (this layer is cached unless requirements.txt changes)
COPY requirements.txt .

# Install Python dependencies
# Using --no-cache-dir to reduce image size
# Using pip cache mount for faster rebuilds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Stage 3: Final application layer
FROM dependencies as final

WORKDIR /app

# Copy application code (this changes frequently, so it's last)
COPY app/ ./app/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Expose FastAPI port
EXPOSE 8000

# Use exec form for proper signal handling
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
