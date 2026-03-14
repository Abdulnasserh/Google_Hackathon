# AI PC Live Technician — Backend Dockerfile
# Optimized for Google Cloud Run (Linux/Debian Slim)

# Use official lightweight Python image
FROM python:3.12-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Port configuration (Cloud Run provides the $PORT env var)
ENV PORT=8080

# Environment variables for Agent configuration
# These can also be set in the Cloud Run Console/Secrets Manager
ENV PYTHONPATH=/server

# Create and set working directory
WORKDIR /server

# Install core networking tools (needed by the agent's diagnostics)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
    dnsutils \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
# We copy app/ and bidi_streaming_agent/ to the working directory
COPY app/ ./app/
COPY bidi_streaming_agent/ ./bidi_streaming_agent/

# Expose port (Documentation only, Cloud Run ignores this and uses $PORT)
EXPOSE 8080

# Run uvicorn on container startup
# --workers 1 is recommended for single-session bidi-streaming agents
# --proxy-headers is important for Cloud Run/LB to detect client IPs correctly
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers
