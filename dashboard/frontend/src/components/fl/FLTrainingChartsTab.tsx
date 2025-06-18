import React, { useState, useCallback, useMemo } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
  Alert,
  Button,
  Chip,
  Stack,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  PeopleAlt as PeopleAltIcon,
  Storage as StorageIcon,
  Restore as RestoreAllIcon,
  FilterList as FilterListIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon
} from '@mui/icons-material';
import FLChart from './FLChart';
import { FLDataState } from './types/flTypes';

interface FLTrainingChartsTabProps {
  data: FLDataState;
}

interface ChartFilters {
  accuracy: number[];
  loss: number[];
  clients_connected: number[];
  model_size_mb: number[];
}

// Enhanced tooltip component for FL training chart data
const FLChartDataTooltip: React.FC<{
  children: React.ReactElement;
  title: string;
  description: string;
  dataSource: 'fl-server' | 'collector' | 'mock' | 'real';
  isRealTime?: boolean;
  additionalInfo?: string;
}> = ({ children, title, description, dataSource, isRealTime = false, additionalInfo }) => {
  
  const getSourceColor = (source: string): string => {
    switch (source) {
      case 'fl-server': return '#2196f3';
      case 'collector': return '#9c27b0';
      case 'real': return '#4caf50';
      case 'mock': return '#ff9800';
      default: return '#757575';
    }
  };

  const getSourceLabel = (source: string): string => {
    switch (source) {
      case 'fl-server': return 'FL Server';
      case 'collector': return 'Collector';
      case 'real': return 'Live Data';
      case 'mock': return 'Demo Data';
      default: return 'Unknown';
    }
  };

  const tooltipContent = (
    <Box sx={{ p: 1, maxWidth: 350 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        {title}
      </Typography>
      <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
        <Chip 
          label={getSourceLabel(dataSource)}
          size="small"
          sx={{ 
            bgcolor: getSourceColor(dataSource),
            color: 'white',
            fontSize: '0.7rem'
          }}
        />
        {isRealTime && (
          <Chip 
            label="Real-time"
            size="small"
            color="success"
            variant="outlined"
            sx={{ fontSize: '0.7rem' }}
          />
        )}
      </Box>
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

const ChartCard = ({ 
  title, 
  icon, 
  children, 
  height = 450,
  dataSource,
  description,
  additionalInfo
}: { 
  title: string; 
  icon: React.ReactNode; 
  children: React.ReactNode;
  height?: number;
  dataSource?: 'fl-server' | 'collector' | 'mock' | 'real';
  description?: string;
  additionalInfo?: string;
}) => (
  <FLChartDataTooltip
    title={title}
    description={description || `Training chart showing ${title.toLowerCase()} data over rounds`}
    dataSource={dataSource || 'fl-server'}
    isRealTime={dataSource === 'fl-server' || dataSource === 'real'}
    additionalInfo={additionalInfo}
  >
    <Card 
      sx={{ 
        borderRadius: 2,
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        height,
        display: 'flex',
        flexDirection: 'column',
        transition: 'box-shadow 0.3s ease',
        '&:hover': {
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)'
        }
      }}
    >
      <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center">
            {icon}
            <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
              {title}
            </Typography>
          </Box>
        </Box>
        <Box flex={1}>
          {children}
        </Box>
      </CardContent>
    </Card>
  </FLChartDataTooltip>
);

export const FLTrainingChartsTab: React.FC<FLTrainingChartsTabProps> = ({
  data
}) => {
  const { metrics, loading, error } = data;

  // State for managing excluded data points per chart
  const [excludedDataPoints, setExcludedDataPoints] = useState<ChartFilters>({
    accuracy: [],
    loss: [],
    clients_connected: [],
    model_size_mb: []
  });

  // Handler for data point changes
  const handleDataPointsChanged = useCallback((chartType: keyof ChartFilters, excludedRounds: number[]) => {
    setExcludedDataPoints(prev => ({
      ...prev,
      [chartType]: excludedRounds
    }));
  }, []);

  // Handler to restore all data points
  const handleRestoreAllDataPoints = useCallback(() => {
    setExcludedDataPoints({
      accuracy: [],
      loss: [],
      clients_connected: [],
      model_size_mb: []
    });
  }, []);
  // Calculate total excluded data points
  const totalExcludedPoints = useMemo(() => {
    const allExcluded = new Set([
      ...excludedDataPoints.accuracy,
      ...excludedDataPoints.loss,
      ...excludedDataPoints.clients_connected,
      ...excludedDataPoints.model_size_mb
    ]);
    return allExcluded.size;
  }, [excludedDataPoints]);
  // Determine data source based on available data
  const getDataSource = (): 'fl-server' | 'collector' | 'mock' | 'real' => {
    if (!metrics || metrics.length === 0) return 'mock';
    
    // Check if we have realistic FL server data indicators
    const hasServerPatterns = metrics.some(m => 
      m.timestamp && m.round && (m.accuracy !== undefined || m.loss !== undefined)
    );
    
    // Check for structured training data that suggests FL server origin
    const hasTrainingPatterns = metrics.some(m => 
      m.round > 0 && m.accuracy && m.loss && m.clients_connected
    );
    
    if (hasServerPatterns && hasTrainingPatterns) return 'fl-server';
    if (hasTrainingPatterns) return 'collector';
    return 'mock';
  };

  const dataSource = getDataSource();
  const isRealTime = dataSource === 'fl-server';

  if (error) {
    return (
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Alert severity="error">
            {error}
          </Alert>
        </Grid>
      </Grid>
    );
  }

  if (loading && metrics.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <Box textAlign="center">
          <CircularProgress size={48} />
          <Typography variant="h6" sx={{ mt: 2 }}>
            Loading Training Charts...
          </Typography>
        </Box>
      </Box>
    );
  }

  // Use the metrics data directly as it already matches the FLMetric interface
  const chartData = metrics.filter(metric => metric.round > 0).map(metric => ({
    ...metric,
    // Only use actual data from server - no fallbacks
    clients_connected: metric.clients_connected || metric.clients_total || 0,
    model_size_mb: metric.model_size_mb || 0
  }));
  return (
    <Box>
      {/* Enhanced Header with Data Source Information */}
      <Box sx={{ mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 600 }}>
            Training Charts Analysis
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip 
              label={dataSource === 'fl-server' ? 'FL Server Data' : 
                     dataSource === 'collector' ? 'Collector Service' : 
                     dataSource === 'real' ? 'Live Training Data' : 'Demo Data'}
              color={dataSource === 'fl-server' ? 'primary' : 
                     dataSource === 'collector' ? 'secondary' : 
                     dataSource === 'real' ? 'success' : 'warning'}
              size="small"
              sx={{ fontWeight: 500 }}
            />
            {isRealTime && (
              <Chip 
                label="Real-time Updates"
                size="small"
                color="info"
                variant="outlined"
              />
            )}
            {loading && (
              <Chip 
                label="Loading..."
                size="small"
                color="primary"
                variant="outlined"
              />
            )}
          </Box>
        </Box>

        {/* Data Source Information Panel */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center" gap={1}>
              <InfoIcon color="primary" />
              <Typography variant="h6">FL Training Data Information</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Current Data Source
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" paragraph>
                    {dataSource === 'fl-server' ? 
                      'Data retrieved directly from the FL server showing live training progress. Metrics include model accuracy, loss values, client participation, and model parameters updated during each training round.' :
                      dataSource === 'collector' ?
                      'Training data aggregated by the collector service from FL training sessions. Historical metrics provide insights into training progression and client behavior patterns.' :
                      dataSource === 'real' ?
                      'Live federated learning training data with real-time updates. Charts show actual training progress as it happens across the distributed network.' :
                      'Demonstration data simulating realistic FL training scenarios. Shows typical training patterns, client participation, and model convergence for evaluation purposes.'}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  <strong>Update Frequency:</strong> {dataSource === 'fl-server' ? 'Real-time with training rounds' : dataSource === 'collector' ? 'Historical data with batch updates' : 'Static demonstration data'}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Chart Metrics Explanation
                </Typography>
                <Grid container spacing={1}>
                  <Grid item xs={6}>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <TrendingUpIcon fontSize="small" color="success" />
                      <Typography variant="body2"><strong>Accuracy:</strong> Model performance metric</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <TrendingDownIcon fontSize="small" color="error" />
                      <Typography variant="body2"><strong>Loss:</strong> Training optimization metric</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <PeopleAltIcon fontSize="small" color="primary" />
                      <Typography variant="body2"><strong>Clients:</strong> Participant count per round</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <StorageIcon fontSize="small" color="secondary" />
                      <Typography variant="body2"><strong>Model Size:</strong> Parameter count evolution</Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" color="text.secondary">
              <strong>Interactive Features:</strong> Click chart dots to exclude outliers, use the dot/line toggle for cleaner visualization, and hover over data points for detailed metrics. Use the "Restore All Data" button to reset any excluded points.
            </Typography>
          </AccordionDetails>
        </Accordion>
      </Box>

      {/* Global Chart Controls */}
      {chartData.length > 0 && (
        <Box sx={{ mb: 3, p: 2, bgcolor: 'background.paper', borderRadius: 2, boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
          <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between" flexWrap="wrap">
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
                Training Charts Data Management
              </Typography>
              <Typography variant="body2" color="text.secondary">
                • Click the dots/smooth line icon to toggle data point visibility for cleaner charts<br/>
                • Click on data points or use chart options to filter outliers and customize your analysis
              </Typography>
            </Box>
            
            <Stack direction="row" spacing={2} alignItems="center">
              {totalExcludedPoints > 0 && (
                <Chip
                  label={`${totalExcludedPoints} points excluded`}
                  color="warning"
                  variant="outlined"
                  icon={<FilterListIcon />}
                />
              )}
              
              <Tooltip title="Restore all excluded data points across all charts">
                <Button
                  variant="outlined"
                  startIcon={<RestoreAllIcon />}
                  onClick={handleRestoreAllDataPoints}
                  disabled={totalExcludedPoints === 0}
                  size="small"
                >
                  Restore All Data
                </Button>
              </Tooltip>
            </Stack>
          </Stack>
        </Box>
      )}

      <Grid container spacing={3}>        {/* Accuracy Chart */}
        <Grid item xs={12} lg={6}>
          <ChartCard
            title="Training Accuracy"
            icon={<TrendingUpIcon color="success" />}
            dataSource={dataSource}
            description="Model accuracy progression across training rounds, showing how well the federated model performs on validation data"
            additionalInfo={dataSource === 'mock' ? 'Sample accuracy progression for demonstration' : 'Live accuracy metrics from FL training rounds'}
          >
            {chartData.length > 0 ? (
              <FLChart
                data={chartData}
                dataKey="accuracy"
                title="Accuracy Progress"
                color="#4caf50"
                yAxisLabel="Accuracy"
                formatter={(value) => `${(value * 100).toFixed(2)}%`}
                enableDataPointRemoval={true}
                onDataPointsChanged={(excludedRounds) => handleDataPointsChanged('accuracy', excludedRounds)}
                showDots={false} // Start with smooth line for less crowded view
                enableDotToggle={true}
              />
            ) : (
              <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                <Typography color="text.secondary">No accuracy data available</Typography>
              </Box>
            )}
          </ChartCard>
        </Grid>        {/* Loss Chart */}
        <Grid item xs={12} lg={6}>
          <ChartCard
            title="Training Loss"
            icon={<TrendingDownIcon color="error" />}
            dataSource={dataSource}
            description="Training loss reduction over rounds, indicating model optimization progress and convergence"
            additionalInfo={dataSource === 'mock' ? 'Sample loss reduction curve for demonstration' : 'Real-time loss metrics from federated training'}
          >
            {chartData.length > 0 ? (
              <FLChart
                data={chartData}
                dataKey="loss"
                title="Loss Progress"
                color="#f44336"
                yAxisLabel="Loss"
                formatter={(value) => value.toFixed(4)}
                enableDataPointRemoval={true}
                onDataPointsChanged={(excludedRounds) => handleDataPointsChanged('loss', excludedRounds)}
                showDots={false} // Start with smooth line for less crowded view
                enableDotToggle={true}
              />
            ) : (
              <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                <Typography color="text.secondary">No loss data available</Typography>
              </Box>
            )}
          </ChartCard>
        </Grid>        {/* Clients Participation Chart */}
        <Grid item xs={12} lg={6}>
          <ChartCard
            title="Client Participation"
            icon={<PeopleAltIcon color="primary" />}
            dataSource={dataSource}
            description="Number of clients participating in each training round, showing network engagement and availability"
            additionalInfo={dataSource === 'mock' ? 'Simulated client participation patterns' : 'Actual client connection counts per training round'}
          >
            {chartData.length > 0 ? (
              <FLChart
                data={chartData}
                dataKey="clients_connected"
                title="Client Participation"
                color="#2196f3"
                yAxisLabel="Connected Clients"
                formatter={(value) => Math.round(value).toString()}
                enableDataPointRemoval={true}
                onDataPointsChanged={(excludedRounds) => handleDataPointsChanged('clients_connected', excludedRounds)}
                showDots={true} // Keep dots for client data since it's usually discrete values
                enableDotToggle={true}
              />
            ) : (
              <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                <Typography color="text.secondary">No client data available</Typography>
              </Box>
            )}
          </ChartCard>
        </Grid>        {/* Model Size Chart */}
        <Grid item xs={12} lg={6}>
          <ChartCard
            title="Model Size Evolution"
            icon={<StorageIcon color="secondary" />}
            dataSource={dataSource}
            description="Model parameter size changes over training rounds, tracking model complexity and compression effects"
            additionalInfo={dataSource === 'mock' ? 'Example model size progression' : 'Real-time model parameter size tracking'}
          >
            {chartData.length > 0 ? (
              <FLChart
                data={chartData}
                dataKey="model_size_mb"
                title="Model Size Over Time"
                color="#ff9800"
                yAxisLabel="Model Size (MB)"
                formatter={(value) => `${value.toFixed(2)} MB`}
                enableDataPointRemoval={true}
                onDataPointsChanged={(excludedRounds) => handleDataPointsChanged('model_size_mb', excludedRounds)}
                showDots={true} // Keep dots for model size data since it might change less frequently
                enableDotToggle={true}
              />
            ) : (
              <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                <Typography color="text.secondary">No model size data available</Typography>
              </Box>
            )}
          </ChartCard>
        </Grid>
      </Grid>
    </Box>
  );
}; 