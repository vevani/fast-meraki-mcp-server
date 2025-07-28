# syntax=docker/dockerfile:1

# Use Python 3.12 slim image for better performance and security
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

# Set working directory
WORKDIR /app

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged user with proper home directory
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/bin/bash" \
    --uid "${UID}" \
    appuser

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the MCP server code (files are in the same directory as Dockerfile)
COPY meraki_mcp_server.py /app/
COPY health_check.py /app/
COPY __init__.py /app/
COPY .env.example /app/
COPY openapi/ /app/openapi/

# Create logs directory with proper permissions
RUN mkdir -p /app/logs /home/appuser && \
    chown -R appuser:appuser /app /home/appuser

# Switch to the non-privileged user
USER appuser

# Expose port
EXPOSE 8000

# Health check for MCP server
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -m health_check || exit 1

# Run the MCP server
CMD ["python", "meraki_mcp_server.py"] 
