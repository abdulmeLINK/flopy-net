FROM python:3.9-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY docker/requirements/collector-requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the source code and configuration files
COPY src /app/src
COPY config /app/config

# Copy entrypoint script
COPY docker/entrypoint-collector.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create directories for logs and results
RUN mkdir -p /app/logs /app/results

# Environment variables
ENV SERVICE_TYPE=collector \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8082

ENTRYPOINT ["/app/entrypoint.sh"] 