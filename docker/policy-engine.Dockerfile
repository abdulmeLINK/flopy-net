FROM python:3.10-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy only the necessary files
COPY policy_engine/ policy_engine/

# Create data directory for SQLite
RUN mkdir -p /data

# Expose the port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "policy_engine.app:app", "--host", "0.0.0.0", "--port", "8000"] 