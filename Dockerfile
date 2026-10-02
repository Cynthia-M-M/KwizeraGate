# ── KwizeraGate Dockerfile ───────────────────────────────────────────────────
# Author: Cynthia Moraa · Modus Chora Studio
# Base: python:3.11-slim (minimal attack surface for a security-focused service)
#
# Build & run:
#   docker build -t kwizeragate .
#   docker run -p 8000:8000 --env-file .env kwizeragate

FROM python:3.11-slim

# Metadata labels
LABEL maintainer="Cynthia Moraa <cynthiamogaka49>"
LABEL org.opencontainers.image.title="KwizeraGate"
LABEL org.opencontainers.image.description="Zero-Trust Payment Entry Middleware — BurundiPay"
LABEL org.opencontainers.image.version="1.0.0"

# Set working directory
WORKDIR /app

# Copy requirements first — separate layer so it is cached between code-only rebuilds
COPY requirements.txt requirements-docker.txt ./

# Install Python dependencies without pip cache (keeps image smaller).
# requirements-docker.txt pulls in requirements.txt + psycopg2-binary for Postgres.
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy application source
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Health check — calls /health every 30s
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
