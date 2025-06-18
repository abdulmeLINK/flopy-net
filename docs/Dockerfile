# Multi-stage Dockerfile for Docusaurus Documentation
# Stage 1: Build the documentation
FROM node:18-alpine AS builder

# Set build arguments
ARG NODE_ENV=production
ARG DOCUSAURUS_VERSION=v1.0.0-alpha.8
ARG BUILD_DATE=2025-06-18
ARG GIT_COMMIT=latest

# Set environment variables
ENV NODE_ENV=${NODE_ENV}
ENV DOCUSAURUS_VERSION=${DOCUSAURUS_VERSION}
ENV BUILD_DATE=${BUILD_DATE}
ENV GIT_COMMIT=${GIT_COMMIT}

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production --silent

# Copy source code
COPY . .

# Build the documentation
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Set build arguments for labels
ARG DOCUSAURUS_VERSION=v1.0.0-alpha.8
ARG BUILD_DATE=2025-06-18
ARG GIT_COMMIT=latest

# Add metadata labels
LABEL maintainer="flopynet Team"
LABEL version="${DOCUSAURUS_VERSION}"
LABEL build-date="${BUILD_DATE}"
LABEL git-commit="${GIT_COMMIT}"
LABEL description="FLOPY-NET Documentation - Federated Learning and SDN Observatory Platform"
LABEL org.opencontainers.image.title="FLOPY-NET Documentation"
LABEL org.opencontainers.image.description="Documentation for FLOPY-NET Federated Learning and SDN Observatory Platform"
LABEL org.opencontainers.image.version="${DOCUSAURUS_VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"
LABEL org.opencontainers.image.vendor="flopynet Team"

# Copy built documentation from builder stage
COPY --from=builder /app/build /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Set proper permissions
RUN chown -R nginx:nginx /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
