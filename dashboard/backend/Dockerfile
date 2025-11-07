FROM python:3.10-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy and install requirements first (for better caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app /app/app

# Create a directory for src
RUN mkdir -p /app/src

# Note: The src directory will be mounted from the host via docker-compose
# This entry ensures the directory exists in the image

# Set PYTHONPATH so /app/app and /app/src are importable
ENV PYTHONPATH=/app

# Port for FastAPI (using 8001 to avoid conflict with collector)
EXPOSE 8001

# Add health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8001/api/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]