import { Alert, Box, Paper, Typography } from '@mui/material';

interface ErrorAlertProps {
  message: string;
  details?: string;
}

/**
 * A component for displaying error messages with optional details
 * in a prominent alert box.
 */
const ErrorAlert = ({ message, details }: ErrorAlertProps) => {
  return (
    <Box sx={{ my: 2 }}>
      <Paper elevation={0}>
        <Alert 
          severity="error" 
          variant="filled"
          sx={{ mb: details ? 0 : 2 }}
        >
          {message}
        </Alert>
        
        {details && (
          <Box sx={{ p: 2, bgcolor: 'error.light', color: 'error.contrastText' }}>
            <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
              {details}
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default ErrorAlert; 