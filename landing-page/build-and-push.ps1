# Option 1: Using Docker directly
# Build the landing page Docker image
docker build -t abdulmelink/flopynet-landing-page:latest .

# Push to Docker Hub (uncomment when ready to push)
docker push abdulmelink/flopynet-landing-page:latest

# Option 2: Using Docker Compose
# Build and run with Docker Compose
# docker-compose up -d --build

# To just build without running
# docker-compose build
