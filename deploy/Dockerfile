# Multi-stage Dockerfile for Cloud Run deployment
# Stage 1: Build React frontend
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies - use npm ci if package-lock.json exists, otherwise npm install
RUN if [ -f "package-lock.json" ]; then \
        npm ci; \
    else \
        npm install; \
    fi

# Copy frontend source
COPY frontend/ ./

# Create production environment file
RUN echo 'VITE_API_BASE=' > .env.production && \
    echo 'VITE_APP_NAME=trends_and_insights_agent' >> .env.production

# Build the frontend (skip TypeScript type checking for deployment speed)
RUN npx vite build

# Stage 2: Python runtime with all services
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nginx \
    supervisor \
    curl \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python requirements and install
COPY trends_and_insights_agent/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Ensure websockets is installed for voice server
RUN pip install --no-cache-dir websockets

# Copy the ADK agent package
COPY trends_and_insights_agent/ ./trends_and_insights_agent/

# Copy voice server
COPY voice_server.py ./

# Copy installation scripts (in case they're needed)
COPY installation_scripts/ ./installation_scripts/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy nginx configuration
COPY deploy/nginx.conf /etc/nginx/nginx.conf

# Copy supervisord configuration
COPY deploy/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create necessary directories
RUN mkdir -p /var/log/nginx /var/log/supervisor

# Expose port 8080 (Cloud Run's $PORT)
EXPOSE 8080

# Start supervisord to manage all processes
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]