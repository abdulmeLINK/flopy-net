import { 
  Box, 
  Typography, 
  Paper, 
  Grid, 
  CircularProgress, 
  Alert, 
  Chip, 
  Divider,
  Stack
} from '@mui/material';
import { useEffect, useState } from 'react';
import { getSystemConfig, getSystemInfo, SystemConfig, SystemInfo } from '../services/configApi';

const SystemConfigPage = () => {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [configData, systemData] = await Promise.all([
          getSystemConfig(),
          getSystemInfo()
        ]);
        setConfig(configData);
        setSystemInfo(systemData);
        setError(null);
      } catch (err) {
        console.error('Error fetching system data:', err);
        setError('Failed to load system configuration');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);

  const InfoRow = ({ label, value, monospace = false }: { label: string; value: string; monospace?: boolean }) => (
    <>
      <Grid item xs={4}>
        <Typography variant="subtitle2" color="text.secondary">
          {label}:
        </Typography>
      </Grid>
      <Grid item xs={8}>
        <Typography 
          variant="body2" 
          sx={{ 
            fontFamily: monospace ? 'monospace' : 'inherit',
            wordBreak: 'break-all'
          }}
        >
          {value || 'Not configured'}
        </Typography>
      </Grid>
    </>
  );
  
  return (
    <Box>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4">
          System Configuration
        </Typography>
        {systemInfo?.application && (
          <Chip 
            label={`v${systemInfo.application.version}`}
            color="primary"
            size="small"
          />
        )}
        {systemInfo?.application.environment && systemInfo.application.environment !== 'production' && (
          <Chip 
            label={systemInfo.application.environment.toUpperCase()}
            color="warning"
            size="small"
          />
        )}
      </Stack>
      
      <Typography variant="body1" paragraph color="text.secondary">
        System information and environment variables for the FLOPY-NET dashboard.
      </Typography>
      
      {loading ? (
        <Box display="flex" justifyContent="center" p={3}>
          <CircularProgress />
        </Box>
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : (
        <Grid container spacing={3}>
          {/* Application Information */}
          {systemInfo?.application && (
            <Grid item xs={12} lg={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom color="primary">
                  Application Information
                </Typography>
                <Grid container spacing={1}>
                  <InfoRow label="Name" value={systemInfo.application.name} />
                  <InfoRow label="Version" value={systemInfo.application.version} />
                  <InfoRow label="Build Date" value={systemInfo.application.build_date} />
                  <InfoRow label="Git Commit" value={systemInfo.application.git_commit} monospace />
                  <InfoRow label="Environment" value={systemInfo.application.environment} />
                </Grid>
              </Paper>
            </Grid>
          )}

          {/* Container Information */}
          {systemInfo?.container && (
            <Grid item xs={12} lg={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom color="primary">
                  Container Information
                </Typography>
                <Grid container spacing={1}>
                  <InfoRow label="Container Name" value={systemInfo.container.container_name} />
                  <InfoRow label="Hostname" value={systemInfo.container.hostname} />
                  <InfoRow label="Startup Time" value={new Date(systemInfo.runtime.startup_time).toLocaleString()} />
                </Grid>
              </Paper>
            </Grid>
          )}

          {/* Runtime Configuration */}
          {systemInfo?.runtime && (
            <Grid item xs={12} lg={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom color="primary">
                  Runtime Configuration
                </Typography>
                <Grid container spacing={1}>
                  <InfoRow label="Log Level" value={systemInfo.runtime.log_level} />
                  <InfoRow label="Connection Timeout" value={`${systemInfo.runtime.connection_timeout}s`} />
                  <InfoRow label="Connection Retries" value={systemInfo.runtime.connection_retries} />
                </Grid>
              </Paper>
            </Grid>
          )}

          {/* Service URLs */}
          <Grid item xs={12} lg={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom color="primary">
                Remote Service URLs
              </Typography>
              <Grid container spacing={1}>
                <InfoRow 
                  label="GNS3 Server" 
                  value={systemInfo?.services?.gns3_url || config?.gns3_url || 'Not configured'} 
                  monospace 
                />
                <InfoRow 
                  label="Collector Service" 
                  value={systemInfo?.services?.collector_url || config?.collector_url || 'Not configured'} 
                  monospace 
                />
                <InfoRow 
                  label="Policy Engine" 
                  value={systemInfo?.services?.policy_engine_url || config?.policy_engine_url || 'Not configured'} 
                  monospace 
                />
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default SystemConfigPage;