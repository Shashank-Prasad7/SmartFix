# Multi-stage Dockerfile for Samsung PRISM Hackathon Theme 2
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for efficient caching
COPY theme2/requirements.txt /app/theme2/requirements.txt
RUN pip install --no-cache-dir -r /app/theme2/requirements.txt

# Copy application source code and data
COPY theme2/ /app/theme2/

ENV PYTHONPATH=/app
ENV PORT=8000
ENV HOST=0.0.0.0

EXPOSE 8000

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start server
CMD ["python", "-m", "uvicorn", "theme2.src.api:app", "--host", "0.0.0.0", "--port", "8000"]
