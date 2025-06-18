# Stage 1: Build React application
FROM node:18-alpine AS build

# Accept build arguments for version information
ARG NODE_ENV=production
ARG VITE_BACKEND_URL=http://localhost:8001
ARG VITE_APP_VERSION=Alpha-0.4.3
ARG VITE_BUILD_DATE=2025-05-26
ARG VITE_GIT_COMMIT=latest
ARG VITE_ENVIRONMENT=development

# Set them as environment variables for the build process
ENV NODE_ENV=${NODE_ENV}
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}
ENV VITE_APP_VERSION=${VITE_APP_VERSION}
ENV VITE_BUILD_DATE=${VITE_BUILD_DATE}
ENV VITE_GIT_COMMIT=${VITE_GIT_COMMIT}
ENV VITE_ENVIRONMENT=${VITE_ENVIRONMENT}

WORKDIR /app

# Set npm configuration for better reliability
RUN npm config set registry https://registry.npmjs.org/ \
    && npm config set fetch-timeout 600000 \
    && npm config set fetch-retries 3

# Copy package.json and package-lock.json (or yarn.lock)
COPY dashboard/frontend/package*.json ./

# Install dependencies with proper error handling (including devDependencies for build)
RUN npm install --include=dev --no-audit --no-fund --loglevel=error || \
    (echo "Package installation failed, retrying..." && \
    npm cache clean --force && \
    npm install --include=dev --no-audit --no-fund --loglevel=error)

# Copy the rest of the code
COPY dashboard/frontend/ .

# Build the application with environment variables available
RUN echo "Building with VITE_APP_VERSION=${VITE_APP_VERSION} and VITE_BUILD_DATE=${VITE_BUILD_DATE}" && \
    npm run build

# Stage 2: Serve the application using Nginx
FROM nginx:stable-alpine

# Copy the custom nginx config
COPY dashboard/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy the build output from Stage 1
COPY --from=build /app/dist /usr/share/nginx/html

# Add a healthcheck to the container
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/index.html || exit 1

# Expose port 80
EXPOSE 80

# Run nginx
CMD ["nginx", "-g", "daemon off;"]