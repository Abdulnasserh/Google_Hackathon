# --- Stage 1: Build the React Frontend ---
FROM node:20-slim AS build-frontend
WORKDIR /frontend

# Install pnpm
RUN npm install -g pnpm

# Copy frontend source
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install

COPY frontend/ .
# Build the production assets
RUN pnpm run build

# --- Stage 2: Build the FastAPI Backend Agent ---
FROM python:3.12-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Port configuration (Cloud Run provides the $PORT env var)
ENV PORT=8080
ENV PYTHONPATH=/server

WORKDIR /server

# Install core networking tools (needed by the agent's diagnostics)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
    dnsutils \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Copy backend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY app/ ./app/
COPY bidi_streaming_agent/ ./bidi_streaming_agent/

# --- Stage 3: Bundle Frontend Assets ---
# Copy the built frontend from Stage 1 into the backend's directory
COPY --from=build-frontend /frontend/dist ./dist

# Run uvicorn on container startup
# --workers 1 is recommended for single-session bidi-streaming agents
CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers
