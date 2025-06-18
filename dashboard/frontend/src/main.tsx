import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css' // Basic global styles
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material';
import { logClientError } from './services/api';

const theme = createTheme({
  // You can customize your MUI theme here
  palette: {
    mode: 'light', // or 'dark'
    primary: {
      main: '#1976d2', // Example primary color
    },
    secondary: {
      main: '#dc004e', // Example secondary color
    },
  },
});

// Create ErrorBoundary component to catch React rendering errors
class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean, error: Error | null }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log the error to our backend
    logClientError(error, {
      componentStack: errorInfo.componentStack,
      type: 'react_error_boundary'
    });
    console.error("React Error Boundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      // Fallback UI
      return (
        <div style={{ 
          padding: '20px', 
          backgroundColor: '#ffdddd', 
          border: '1px solid #ff0000',
          borderRadius: '5px',
          margin: '20px'
        }}>
          <h2>Something went wrong.</h2>
          <p>The application encountered an error. Please try refreshing the page.</p>
          <details>
            <summary>Error Details</summary>
            <pre>{this.state.error?.toString()}</pre>
          </details>
          <button 
            onClick={() => window.location.reload()}
            style={{
              padding: '8px 16px',
              backgroundColor: '#1976d2',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              marginTop: '15px'
            }}
          >
            Refresh Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

// Set up global error handler to log errors to backend
window.addEventListener('error', (event) => {
  console.error("Global error caught:", event.error);
  logClientError(event.error || new Error(event.message), {
    message: event.message,
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
    type: 'global_error'
  });
});

// Also catch unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  console.error("Unhandled rejection caught:", event.reason);
  logClientError(new Error(event.reason?.message || 'Unhandled Promise rejection'), {
    reason: event.reason,
    type: 'unhandled_promise'
  });
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ThemeProvider theme={theme}>
        <CssBaseline /> 
        <App />
      </ThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>,
) 