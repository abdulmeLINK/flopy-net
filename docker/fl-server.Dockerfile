FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy only the necessary files
COPY fl/ fl/

# Create data directory
RUN mkdir -p /data

# Expose the port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "fl.server"] 