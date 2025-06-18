import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Tooltip
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Settings as SettingsIcon,
  ModelTraining as ModelTrainingIcon,
  Security as SecurityIcon,
  Storage as StorageIcon,
  Timeline as TimelineIcon,
  Computer as ComputerIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { FLConfiguration } from '../../services/flMonitoringApi';

interface FLConfigurationTabProps {
  configuration: FLConfiguration | null;
  configLoading: boolean;
  configError: string | null;
  onReloadConfig: () => void;
}

// Enhanced tooltip component for FL configuration data
const FLConfigTooltip: React.FC<{
  children: React.ReactElement;
  title: string;
  description: string;
  configType?: string;
  additionalInfo?: string;
}> = ({ children, title, description, configType, additionalInfo }) => {
  
  const getConfigTypeColor = (type: string): string => {
    switch (type) {
      case 'model': return '#2196f3';
      case 'training': return '#4caf50';
      case 'network': return '#ff9800';
      case 'security': return '#f44336';
      case 'system': return '#9c27b0';
      default: return '#757575';
    }
  };

  const tooltipContent = (
    <Box sx={{ p: 1, maxWidth: 400 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        {title}
      </Typography>
      {configType && (
        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
          <Chip 
            label={configType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            size="small"
            sx={{ 
              bgcolor: getConfigTypeColor(configType),
              color: 'white',
              fontSize: '0.7rem'
            }}
          />
        </Box>
      )}
      <Typography variant="body2" sx={{ mb: 1 }}>
        {description}
      </Typography>
      {additionalInfo && (
        <Typography variant="caption" color="text.secondary">
          {additionalInfo}
        </Typography>
      )}
    </Box>
  );

  return (
    <Tooltip title={tooltipContent} arrow placement="top">
      {children}
    </Tooltip>
  );
};

const formatConfigValue = (value: any, type?: 'boolean' | 'number' | 'string' | 'array' | 'object'): React.ReactNode => {
  if (value === null || value === undefined) {
    return (
      <Chip 
        label="Not Available" 
        size="small" 
        variant="outlined" 
        color="default"
        sx={{ fontSize: '0.75rem' }}
      />
    );
  }

  // Handle special configuration states
  if (typeof value === 'string') {
    const lowerValue = value.toLowerCase();
    if (lowerValue.includes('pending') || lowerValue.includes('configuration pending')) {
      return (
        <Chip 
          label="Pending Configuration" 
          size="small" 
          color="warning"
          variant="outlined"
          sx={{ fontSize: '0.75rem' }}
        />
      );
    }
    if (lowerValue.includes('unavailable') || lowerValue.includes('not available')) {
      return (
        <Chip 
          label="Unavailable" 
          size="small" 
          color="error"
          variant="outlined"
          sx={{ fontSize: '0.75rem' }}
        />
      );
    }
    if (lowerValue === 'unknown' || lowerValue === 'pending') {
      return (
        <Chip 
          label="Configuration Loading..." 
          size="small" 
          color="info"
          variant="outlined"
          sx={{ fontSize: '0.75rem' }}
        />
      );
    }
  }

  switch (type) {
    case 'boolean':
      return (
        <Chip 
          label={value ? 'Yes' : 'No'} 
          size="small" 
          color={value ? 'success' : 'default'}
          variant={value ? 'filled' : 'outlined'}
          sx={{ fontSize: '0.75rem' }}
        />
      );
    case 'number':
      return <Typography variant="body2" component="span">{typeof value === 'number' ? value.toLocaleString() : value}</Typography>;
    case 'array':
      if (Array.isArray(value)) {
        return value.length > 0 ? value.join(', ') : 'None';
      }
      return String(value);
    case 'object':
      if (typeof value === 'object' && value !== null) {
        return <pre style={{ fontSize: '0.75rem', margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(value, null, 2)}</pre>;
      }
      return String(value);
    default:
      return <Typography variant="body2" component="span">{String(value)}</Typography>;
  }
};

const ConfigSection = ({ 
  title, 
  icon, 
  children, 
  defaultExpanded = false,
  status = 'info'
}: { 
  title: string; 
  icon: React.ReactNode; 
  children: React.ReactNode;
  defaultExpanded?: boolean;
  status?: 'success' | 'warning' | 'error' | 'info';
}) => {
  const getStatusIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon color="success" fontSize="small" />;
      case 'warning':
        return <WarningIcon color="warning" fontSize="small" />;
      case 'error':
        return <ErrorIcon color="error" fontSize="small" />;
      default:
        return <InfoIcon color="info" fontSize="small" />;
    }
  };

  return (
    <Accordion defaultExpanded={defaultExpanded} sx={{ mb: 1 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box display="flex" alignItems="center">
          {icon}
          <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
            {title}
          </Typography>
          <Box sx={{ ml: 1 }}>
            {getStatusIcon()}
          </Box>
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        {children}
      </AccordionDetails>
    </Accordion>
  );
};

const ConfigTable = ({ 
  data, 
  loading = false 
}: { 
  data: Array<{ label: string; value: any; type?: string }>; 
  loading?: boolean;
}) => (
  <TableContainer component={Paper} variant="outlined" sx={{ mt: 1 }} className="config-table">
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell sx={{ fontWeight: 600 }}>Parameter</TableCell>
          <TableCell sx={{ fontWeight: 600 }}>Value</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {data.map((item, index) => (
          <TableRow key={index}>
            <TableCell>{item.label}</TableCell>
            <TableCell>
              {formatConfigValue(item.value, item.type as any)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </TableContainer>
);

export const FLConfigurationTab: React.FC<FLConfigurationTabProps> = ({
  configuration,
  configLoading,
  configError,
  onReloadConfig
}) => {
  if (configError) {
    return (
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Alert 
            severity="error" 
            action={
              <Box component="span" onClick={onReloadConfig} sx={{ cursor: 'pointer', textDecoration: 'underline' }}>
                Retry
              </Box>
            }
          >
            Failed to load configuration: {configError}
          </Alert>
        </Grid>
      </Grid>
    );
  }

  if (configLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <Box textAlign="center">
          <CircularProgress size={48} />
          <Typography variant="h6" sx={{ mt: 2 }}>
            Loading FL Configuration...
          </Typography>
        </Box>
      </Box>
    );
  }

  if (!configuration) {
    return (
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Alert severity="warning">
            No configuration data available. Make sure the FL server and policy engine are running.
          </Alert>
        </Grid>
      </Grid>
    );
  }

  // Determine overall configuration status
  const getConfigStatus = () => {
    const status = configuration.status;
    if (status === 'comprehensive') return 'success';
    if (status === 'enhanced' || status === 'basic') return 'warning';
    return 'error';
  };

  const flServerData = [
    { label: 'Model', value: configuration.fl_server.model, type: 'string' },
    { label: 'Dataset', value: configuration.fl_server.dataset, type: 'string' },
    { label: 'Total Rounds', value: configuration.fl_server.total_rounds, type: 'number' },
    { label: 'Current Round', value: configuration.fl_server.current_round, type: 'number' },
    { label: 'Min Clients', value: configuration.fl_server.min_clients, type: 'number' },
    { label: 'Min Available Clients', value: configuration.fl_server.min_available_clients, type: 'number' },
    { label: 'Server Host', value: configuration.fl_server.server_host, type: 'string' },
    { label: 'Server Port', value: configuration.fl_server.server_port, type: 'number' },
    { label: 'Training Complete', value: configuration.fl_server.training_complete, type: 'boolean' },
    { label: 'Stay Alive After Training', value: configuration.fl_server.stay_alive_after_training, type: 'boolean' }
  ];

  const trainingParamsData = [
    { label: 'Total Rounds', value: configuration.training_parameters.total_rounds, type: 'number' },
    { label: 'Local Epochs', value: configuration.training_parameters.local_epochs, type: 'number' },
    { label: 'Batch Size', value: configuration.training_parameters.batch_size, type: 'number' },
    { label: 'Learning Rate', value: configuration.training_parameters.learning_rate, type: 'number' },
    { label: 'Aggregation Strategy', value: configuration.training_parameters.aggregation_strategy, type: 'string' },
    { label: 'Evaluation Strategy', value: configuration.training_parameters.evaluation_strategy, type: 'string' },
    { label: 'Privacy Mechanism', value: configuration.training_parameters.privacy_mechanism, type: 'string' },
    { label: 'Secure Aggregation', value: configuration.training_parameters.secure_aggregation, type: 'boolean' }
  ];

  const modelConfigData = [
    { label: 'Model Type', value: configuration.model_config.model_type, type: 'string' },
    { label: 'Number of Classes', value: configuration.model_config.num_classes, type: 'number' },
    { label: 'Architecture', value: configuration.model_config.architecture, type: 'string' },
    { label: 'Estimated Parameters', value: configuration.model_config.estimated_parameters, type: 'number' },
    ...(configuration.model_config.input_shape ? [
      { label: 'Input Shape', value: JSON.stringify(configuration.model_config.input_shape), type: 'string' }
    ] : []),
    ...(configuration.model_config.input_size ? [
      { label: 'Input Size', value: configuration.model_config.input_size, type: 'number' }
    ] : []),
    ...(configuration.model_config.hidden_sizes ? [
      { label: 'Hidden Sizes', value: JSON.stringify(configuration.model_config.hidden_sizes), type: 'string' }
    ] : [])
  ];
  const policyEngineData = configuration.policy_engine.policy_allowed ? [
    { label: 'Policy Decision', value: configuration.policy_engine.policy_decision, type: 'string' },
    { label: 'Policy Allowed', value: configuration.policy_engine.policy_allowed, type: 'boolean' },
    ...(configuration.policy_engine.max_clients ? [
      { label: 'Max Clients', value: configuration.policy_engine.max_clients, type: 'number' }
    ] : []),
    ...(configuration.policy_engine.differential_privacy_epsilon ? [
      { label: 'DP Epsilon', value: configuration.policy_engine.differential_privacy_epsilon, type: 'number' }
    ] : []),
    ...(configuration.policy_engine.differential_privacy_delta ? [
      { label: 'DP Delta', value: configuration.policy_engine.differential_privacy_delta, type: 'number' }
    ] : [])
  ] : [
    { label: 'Status', value: 'No policy engine configuration available', type: 'string' }
  ];

  return (
    <Box>
      {/* Enhanced Header with Configuration Information */}
      <Box sx={{ mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 600 }}>
            FL System Configuration
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={configuration.status.toUpperCase()}
              color={getConfigStatus()}
              variant="filled"
              sx={{ fontWeight: 500 }}
            />
            <Chip 
              label={`${configuration.data_sources.length} Data Sources`}
              size="small"
              color="info"
              variant="outlined"
            />
          </Box>
        </Box>

        {/* Configuration Information Panel */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center" gap={1}>
              <InfoIcon color="primary" />
              <Typography variant="h6">FL Configuration Information</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Configuration Sources
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    <strong>Data Sources:</strong> {configuration.data_sources.join(', ')}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    <strong>Completeness:</strong> {configuration.metadata.config_completeness}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <strong>Sources Used:</strong> {configuration.metadata.data_sources_used.join(', ')}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Configuration Sections
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                  <Typography variant="body2" color="text.secondary">
                    <ComputerIcon fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
                    <strong>FL Server:</strong> Core server configuration and status
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <ModelTrainingIcon fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
                    <strong>Training:</strong> Hyperparameters and training settings
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <TimelineIcon fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
                    <strong>Model:</strong> Architecture and parameter configuration
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    <SecurityIcon fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
                    <strong>Policy:</strong> Security and governance policies
                  </Typography>
                </Box>
              </Grid>
            </Grid>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" color="text.secondary">
              <strong>Last Updated:</strong> {new Date(configuration.timestamp).toLocaleString()} • 
              <strong> Execution Time:</strong> {configuration.metadata.execution_time_ms}ms • 
              <strong> API Version:</strong> {configuration.metadata.api_version}
            </Typography>
          </AccordionDetails>
        </Accordion>
      </Box>
      
      <Grid container spacing={3}>
      {/* Configuration Status Card */}
      <Grid item xs={12}>
        <Card sx={{ borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
          <CardContent sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
              <Box display="flex" alignItems="center">
                <SettingsIcon color="primary" />
                <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
                  Configuration Status
                </Typography>
              </Box>
              <Chip
                label={configuration.status.toUpperCase()}
                color={getConfigStatus()}
                variant="filled"
                sx={{ fontWeight: 500 }}
              />
            </Box>

            <Typography variant="body2" color="text.secondary" gutterBottom>
              Data Sources: {configuration.data_sources.join(', ')}
            </Typography>
            
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Completeness: {configuration.metadata.config_completeness}
            </Typography>
            
            <Typography variant="body2" color="text.secondary">
              Last Updated: {new Date(configuration.timestamp).toLocaleString()}
            </Typography>
          </CardContent>
        </Card>
      </Grid>      {/* FL Server Configuration */}
      <Grid item xs={12} lg={6}>
        <FLConfigTooltip
          title="FL Server Configuration"
          description="Core federated learning server settings including model, dataset, rounds configuration, and server status"
          configType="system"
          additionalInfo={`Source: ${configuration.fl_server.source} - ${configuration.fl_server.source === 'fl_server_direct' ? 'Direct server connection' : 'Configuration from other sources'}`}
        >
          <div>
            <ConfigSection
              title="FL Server Configuration"
              icon={<ComputerIcon color="primary" />}
              defaultExpanded={true}
              status={configuration.fl_server.source === 'fl_server_direct' ? 'success' : 'warning'}
            >
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Source: {configuration.fl_server.source}
              </Typography>
              <ConfigTable data={flServerData} loading={configLoading} />
            </ConfigSection>
          </div>
        </FLConfigTooltip>
      </Grid>

      {/* Training Parameters */}
      <Grid item xs={12} lg={6}>
        <FLConfigTooltip
          title="Training Parameters"  
          description="Hyperparameters and training configuration including rounds, epochs, batch size, learning rate, and privacy settings"
          configType="training"
          additionalInfo="These parameters control the federated learning training process and model optimization"
        >
          <div>
            <ConfigSection
              title="Training Parameters"
              icon={<ModelTrainingIcon color="secondary" />}
              defaultExpanded={true}
              status={configuration.training_parameters.total_rounds > 0 ? 'success' : 'warning'}
            >
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Hyperparameters and training configuration
              </Typography>
              <ConfigTable data={trainingParamsData} loading={configLoading} />
            </ConfigSection>
          </div>
        </FLConfigTooltip>
      </Grid>      {/* Model Configuration */}
      <Grid item xs={12} lg={6}>
        <FLConfigTooltip
          title="Model Configuration"
          description="Neural network model architecture details including type, classes, parameters, and input specifications"
          configType="model"
          additionalInfo="Defines the structure and properties of the machine learning model used in federated training"
        >
          <div>
            <ConfigSection
              title="Model Configuration"
              icon={<TimelineIcon color="info" />}
              defaultExpanded={false}
              status={configuration.model_config.model_type ? 'success' : 'warning'}
            >
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Model architecture and parameters
              </Typography>
              <ConfigTable data={modelConfigData} loading={configLoading} />
            </ConfigSection>
          </div>
        </FLConfigTooltip>
      </Grid>

      {/* Policy Engine Configuration */}
      <Grid item xs={12} lg={6}>
        <FLConfigTooltip
          title="Policy Engine Configuration"
          description="Security and governance policies controlling FL training including client limits, privacy parameters, and access control"
          configType="security"
          additionalInfo={configuration.policy_engine.policy_allowed ? 'Policies are active and controlling FL behavior' : 'Policy engine may not be configured or accessible'}
        >
          <div>
            <ConfigSection
              title="Policy Engine Configuration"
              icon={<SecurityIcon color="warning" />}
              defaultExpanded={false}
              status={configuration.policy_engine.policy_allowed ? 'success' : 'error'}
            >
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Policy-derived parameters and constraints
              </Typography>
              <ConfigTable data={policyEngineData} loading={configLoading} />
            </ConfigSection>
          </div>
        </FLConfigTooltip>
      </Grid>

      {/* Federation Configuration (if available) */}
      {configuration.federation_config && Object.keys(configuration.federation_config).length > 0 && (
        <Grid item xs={12}>
          <ConfigSection
            title="Federation Configuration"
            icon={<StorageIcon color="success" />}
            defaultExpanded={false}
            status="info"
          >
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Federation-level configuration from FL server events
            </Typography>
            <ConfigTable 
              data={[
                { label: 'Model', value: configuration.federation_config.model, type: 'string' },
                { label: 'Dataset', value: configuration.federation_config.dataset, type: 'string' },
                { label: 'Rounds', value: configuration.federation_config.rounds, type: 'number' },
                { label: 'Min Clients', value: configuration.federation_config.min_clients, type: 'number' },
                { label: 'Stay Alive After Training', value: configuration.federation_config.stay_alive_after_training, type: 'boolean' },
                { label: 'Source', value: configuration.federation_config.source, type: 'string' }
              ]} 
              loading={configLoading} 
            />
          </ConfigSection>
        </Grid>
      )}

      {/* Metadata */}
      <Grid item xs={12}>
        <Card sx={{ borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
              Metadata
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Execution Time
                </Typography>
                <Typography variant="body1">
                  {configuration.metadata.execution_time_ms}ms
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  API Version
                </Typography>
                <Typography variant="body1">
                  {configuration.metadata.api_version}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Sources Used
                </Typography>
                <Typography variant="body1">
                  {configuration.metadata.data_sources_used.length}
                </Typography>
              </Grid>
              
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Timestamp
                </Typography>
                <Typography variant="body1">
                  {new Date(configuration.metadata.timestamp).toLocaleTimeString()}
                </Typography>
              </Grid>
            </Grid>

            <Divider sx={{ my: 2 }} />

            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Data Sources Used:
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={1}>
                {configuration.metadata.data_sources_used.map((source, index) => (
                  <Chip
                    key={index}
                    label={source}
                    size="small"
                    variant="outlined"
                    color="primary"
                  />
                ))}
              </Box>
            </Box>          </CardContent>
        </Card>
      </Grid>
    </Grid>
    </Box>
  );
};