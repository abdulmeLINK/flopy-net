FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Expose the API port
EXPOSE 5000

# Run the federated learning server
CMD ["python", "-m", "src.main", "--mode", "server", "--host", "0.0.0.0", "--port", "5000"] 