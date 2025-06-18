import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Get backend URL from environment variables
const BACKEND_URL = process.env.VITE_BACKEND_URL || 'http://localhost:8001';

// Get version and build info from environment variables
const APP_VERSION = process.env.VITE_APP_VERSION || process.env.npm_package_version || 'alpha-0.4.3';
const BUILD_DATE = process.env.VITE_BUILD_DATE || new Date().toISOString().split('T')[0];
const GIT_COMMIT = process.env.VITE_GIT_COMMIT || 'latest';
const ENVIRONMENT = process.env.VITE_ENVIRONMENT || 'development';

console.log('Vite build configuration:');
console.log(`  APP_VERSION: ${APP_VERSION}`);
console.log(`  BUILD_DATE: ${BUILD_DATE}`);
console.log(`  GIT_COMMIT: ${GIT_COMMIT}`);
console.log(`  ENVIRONMENT: ${ENVIRONMENT}`);
console.log(`  BACKEND_URL: ${BACKEND_URL}`);

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],  
  build: {
    minify: false,
  },
  define: {
    // Frontend only needs to know the backend URL
    'process.env': {
      BACKEND_URL: JSON.stringify(BACKEND_URL)
    },
    // Use environment variables for version and build information
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(APP_VERSION),
    'import.meta.env.VITE_BUILD_DATE': JSON.stringify(BUILD_DATE),
    'import.meta.env.VITE_GIT_COMMIT': JSON.stringify(GIT_COMMIT),
    'import.meta.env.VITE_ENVIRONMENT': JSON.stringify(ENVIRONMENT)
  },
  server: {
    port: 8085, // Desired frontend port
    cors: true,
    proxy: {      // Proxy /api requests to the backend service during development
      '/api': {
        target: BACKEND_URL, // Backend API URL - using environment variable
        changeOrigin: true,
        secure: false,
        headers: {
          'Access-Control-Allow-Origin': '*'
        }
        // rewrite: (path) => path.replace(/^\/api/, '') // if backend doesn't have /api prefix
      },
      // Proxy /ws requests to the backend WebSocket during development
      '/ws': {
        target: BACKEND_URL.replace('http', 'ws'),
        ws: true,
        changeOrigin: true,
        secure: false
      },
      '/api/fl-monitoring/ws': {
        target: BACKEND_URL.replace('http', 'ws'),
        ws: true,
        changeOrigin: true,
        secure: false
      }
    }
  }
}) 