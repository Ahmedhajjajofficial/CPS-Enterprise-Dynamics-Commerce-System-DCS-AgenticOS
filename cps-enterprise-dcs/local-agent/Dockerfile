# ═══════════════════════════════════════════════════════════════════════════════
# Local Agent Dockerfile
# Python 3.11 with gRPC support
# ═══════════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ═══════════════════════════════════════════════════════════════════════════════

FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create app directory
WORKDIR /app

# Copy application code
COPY src/ ./src/

# Create data directory
RUN mkdir -p /data

# Expose gRPC port
EXPOSE 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; print('healthy')" || exit 1

# Run the agent
CMD ["python", "-m", "src.main", "--branch-id", "${DCS_BRANCH_ID}", "--region-id", "${DCS_REGION_ID}"]
