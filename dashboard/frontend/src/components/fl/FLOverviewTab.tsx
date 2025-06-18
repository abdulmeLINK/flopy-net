import React from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
  CircularProgress,
  IconButton,
  Alert,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  Speed as SpeedIcon,
  People as PeopleIcon,
  Storage as StorageIcon,
  Timer as TimerIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon
} from '@mui/icons-material';
import { FLDataState } from './types/flTypes';

interface FLOverviewTabProps {
  data: FLDataState;
  onRefresh: () => void;
  formatAccuracy: (accuracy: number) => string;
  formatLoss: (loss: number) => string;
  formatModelSize: (sizeInMB: number) => string;
  getTrainingStatusColor: () => 'success' | 'warning' | 'error' | 'info';
  getTrainingStatusText: () => string;
}

// Enhanced tooltip component for FL data
const FLDataTooltip: React.FC<{
  children: React.ReactElement;
  title: string;
  description: string;
  dataSource: 'real' | 'mock' | 'fl-server' | 'collector';
  isRealTime?: boolean;
  additionalInfo?: string;
}> = ({ children, title, description, dataSource, isRealTime = false, additionalInfo }) => {
  const getSourceColor = (source: string) => {
    switch (source) {
      case 'real': return '#4caf50';
      case 'fl-server': return '#2196f3';
      case 'collector': return '#9c27b0';
      case 'mock': return '#f44336';
      default: return '#757575';
    }
  };

  const getSourceLabel = (source: string) => {
    switch (source) {
      case 'real': return 'Real FL Data';
      case 'fl-server': return 'FL Server';
      case 'collector': return 'Collector Service';
      case 'mock': return 'Mock Data';
      default: return 'Unknown Source';
    }
  };

  const tooltipContent = (
    <Box>
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

const LoadingIndicator = ({ size = 16, refreshing = false }: { size?: number; refreshing?: boolean }) => (
  <CircularProgress 
    size={size} 
    sx={{ 
      color: refreshing ? 'orange' : 'inherit',
      opacity: refreshing ? 0.7 : 1
    }} 
  />
);

const MetricValue = ({ 
  value, 
  loading, 
  error, 
  formatter = (v) => {
    // Ensure proper number parsing to avoid extra zeros
    const numValue = Number(v);
    if (isNaN(numValue)) return '0';
    
    // For whole numbers, don't show decimal places
    if (Number.isInteger(numValue)) {
      return numValue.toString();
    }
    
    // For decimals, limit to reasonable precision
    return numValue.toString();
  },
  refreshing = false,
  variant = 'body1'
}: { 
  value: any; 
  loading: boolean; 
  error?: boolean;
  formatter?: (value: any) => string;
  refreshing?: boolean;
  variant?: 'h6' | 'body1' | 'body2';
}) => {
  if (loading) {
    return <LoadingIndicator size={20} refreshing={refreshing} />;
  }
  
  if (error) {
    return <Typography color="error" variant="body2">Error</Typography>;
  }
  
  return (
    <Typography 
      variant={variant}
      component="span"
      sx={{ 
        opacity: refreshing ? 0.7 : 1,
        transition: 'opacity 0.3s ease',
        fontWeight: variant === 'h6' ? 600 : 500
      }}
    >
      {formatter(value)}
    </Typography>
  );
};

export const FLOverviewTab: React.FC<FLOverviewTabProps> = ({
  data,
  onRefresh,
  formatAccuracy,
  formatLoss,
  formatModelSize,
  getTrainingStatusColor,
  getTrainingStatusText
}) => {
  const { 
    trainingStatus, 
    summary, 
    loading, 
    refreshing, 
    error, 
    lastUpdateTime 
  } = data;

  // Determine data source based on available data
  const getDataSource = (): 'real' | 'mock' | 'fl-server' | 'collector' => {
    if (error) return 'mock';
    if (trainingStatus && !loading) return 'fl-server';
    if (summary && Object.keys(summary).length > 0) return 'collector';
    return 'mock';
  };

  const dataSource = getDataSource();
  const isRealTime = dataSource === 'fl-server' || dataSource === 'collector';

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  };

  const formatRoundNumber = (round: any): string => {
    let valueToProcess: string;

    // Ensure valueToProcess is a string, and clean if it was initially a string
    if (typeof round === 'number') {
      valueToProcess = String(round);
    } else if (typeof round === 'string') {
      valueToProcess = round.replace(/[^\\d.]/g, ''); // Clean up if already a string
    } else {
      // Default for other types or null/undefined, then convert to string
      valueToProcess = String(round || 0);
    }
    
    // Debug logging to understand the issue
    if (process.env.NODE_ENV === 'development') {
      console.log('formatRoundNumber input:', round, '(type:', typeof round, '), initial valueToProcess:', valueToProcess);
    }
    
    let potentiallyCorrectedValue = valueToProcess;
    
    // Specific fix for the reported issue: e.g., 169 -> 1690 pattern
    // Check if the string looks like a concatenated number ending with 0
    // Ensure we are not misinterpreting valid numbers like 10, 100, 1000 etc.
    if (potentiallyCorrectedValue.length >= 2 && potentiallyCorrectedValue.endsWith('0')) {
      const withoutLastZero = potentiallyCorrectedValue.slice(0, -1);
      // Ensure withoutLastZero is not empty (e.g. for input "0")
      if (withoutLastZero.length > 0) {
        const originalValueCandidate = parseInt(withoutLastZero, 10);
        const fullValue = parseInt(potentiallyCorrectedValue, 10);
        
        // If removing the last zero gives us a value that's exactly 1/10th of the full value,
        // and the original candidate is a positive number, it's likely the extra zero issue.
        // Example: "1690" -> fullValue=1690, withoutLastZero="169", originalValueCandidate=169. 1690 = 169 * 10. Correct to "169".
        // Example: "10"   -> fullValue=10,   withoutLastZero="1",   originalValueCandidate=1.   10 = 1 * 10. Correct to "1". (This might be too aggressive for "10")
        // Let's refine: only apply if originalValueCandidate * 10 === fullValue AND originalValueCandidate is what we expect (e.g. not 1 for 10)
        // The problem description was "1510" from "151". So, the "original" is > 10.
        if (!isNaN(originalValueCandidate) && !isNaN(fullValue) && 
            fullValue === originalValueCandidate * 10 && originalValueCandidate > 0) {
            
            // Heuristic: if the original number was likely two digits or more (e.g. 151, not 1)
            // "1690" (current) vs "169" (total). originalValueCandidate = 169.
            // If the problem is specifically "NNN0" from "NNN", this implies NNN had multiple digits.
            // A simple "10" should probably remain "10".
            // If `originalValueCandidate` has at least 2 digits OR `originalValueCandidate` is single digit but `fullValue` is >= 100 (e.g. 700 from 70)
            if (withoutLastZero.length >= 2 || (withoutLastZero.length === 1 && fullValue >=100) ) {
                 potentiallyCorrectedValue = withoutLastZero;
                 if (process.env.NODE_ENV === 'development') {
                    console.log('Fixed round number concatenation:', fullValue, '->', originalValueCandidate);
                }
            } else if (process.env.NODE_ENV === 'development') {
                console.log('Did not apply 10x fix for:', fullValue, 'original candidate:', originalValueCandidate, 'withoutLastZero.length:', withoutLastZero.length);
            }
        }
      }
    }
    
    // Safely parse round number and ensure it's an integer
    const parsed = parseInt(potentiallyCorrectedValue, 10);
    const result = isNaN(parsed) ? '0' : String(parsed);
    
    if (process.env.NODE_ENV === 'development') {
      console.log('formatRoundNumber output:', result, ' (from potentiallyCorrectedValue:', potentiallyCorrectedValue + ')');
    }
    
    return result;
  };

  const formatClientCount = (clients: any): string => {
    const count = parseInt(String(clients || 0), 10);
    if (isNaN(count) || count <= 0) {
      return 'No clients';
    }
    return String(count);
  };

  const getStatusIcon = () => {
    const color = getTrainingStatusColor();
    switch (color) {
      case 'success':
        return <CheckCircleIcon color="success" />;
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <InfoIcon color="info" />;
    }
  };

  return (
    <Box>
      {/* Enhanced Header with Data Source Information */}
      <Box sx={{ mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 600 }}>
            Federated Learning Overview
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip 
              label={dataSource === 'real' ? 'Live FL Data' : 
                     dataSource === 'fl-server' ? 'FL Server Connected' :
                     dataSource === 'collector' ? 'Collector Service' : 'Demo Data'}
              color={dataSource === 'real' || dataSource === 'fl-server' ? 'success' : 
                     dataSource === 'collector' ? 'primary' : 'warning'}
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
            {refreshing && (
              <Chip 
                label="Updating..."
                size="small"
                color="primary"
                variant="outlined"
              />
            )}
          </Box>
        </Box>

        {/* Data Source Information Panel */}
        <Accordion sx={{ mb: 1 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center" gap={1}>
              <InfoIcon color="primary" />
              <Typography variant="h6">Federated Learning Data Information</Typography>
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
                    {dataSource === 'real' ? 
                      'This dashboard shows live federated learning data directly from the FL server and participating clients. All metrics reflect actual training progress, client participation, and system performance.' :
                      dataSource === 'fl-server' ?
                      'Connected to the FL server for real-time training metrics. Client data, round progress, and model performance are updated as training progresses.' :
                      dataSource === 'collector' ?
                      'Data is aggregated by the collector service from FL components. Includes historical metrics and current training status from multiple sources.' :
                      'This is demonstration data for testing purposes. It simulates a real federated learning training session with realistic metrics and client behavior.'}
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Metrics Explanation
                </Typography>
                <Grid container spacing={1}>
                  <Grid item xs={6}>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <TrendingUpIcon fontSize="small" color="success" />
                      <Typography variant="body2"><strong>Accuracy:</strong> Model performance</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <SpeedIcon fontSize="small" color="error" />
                      <Typography variant="body2"><strong>Loss:</strong> Training error rate</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <PeopleIcon fontSize="small" color="primary" />
                      <Typography variant="body2"><strong>Clients:</strong> Participating nodes</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <TimerIcon fontSize="small" color="warning" />
                      <Typography variant="body2"><strong>Rounds:</strong> Training iterations</Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" color="text.secondary">
              <strong>Data Quality:</strong> {dataSource === 'mock' ? 'Demo data for demonstration - not connected to actual FL infrastructure' : 'Live data from federated learning system components'}
            </Typography>
          </AccordionDetails>
        </Accordion>
      </Box>

      <Grid container spacing={3}>
      {/* Error Alert */}
      {error && (
        <Grid item xs={12}>
          <Alert severity="error" onClose={() => {}}>
            {error}
          </Alert>
        </Grid>
      )}

      {/* Training Status Card */}
      <Grid item xs={12} md={6} lg={4}>
        <FLDataTooltip
          title="Training Status"
          description="Current state of the federated learning training process"
          dataSource={dataSource}
          isRealTime={isRealTime}
          additionalInfo={dataSource === 'mock' ? 'Simulated training status for demonstration' : 'Live training status from FL server'}
        >
          <Card 
            sx={{ 
              borderRadius: 2,
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              height: 280,
              display: 'flex',
              flexDirection: 'column',
              cursor: 'help'
            }}
            className="metric-card"
          >
          <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
              <Box display="flex" alignItems="center">
                {getStatusIcon()}
                <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
                  Training Status
                </Typography>
              </Box>
              <Tooltip title="Refresh">
                <IconButton 
                  onClick={onRefresh} 
                  size="small"
                  disabled={loading}
                  sx={{ 
                    opacity: refreshing ? 0.6 : 1,
                    '&:hover': { backgroundColor: 'rgba(0,0,0,0.04)' }
                  }}
                >
                  <RefreshIcon 
                    sx={{ 
                      animation: refreshing ? 'spin 1s linear infinite' : 'none',
                      '@keyframes spin': {
                        '0%': { transform: 'rotate(0deg)' },
                        '100%': { transform: 'rotate(360deg)' }
                      }
                    }} 
                  />
                </IconButton>
              </Tooltip>
            </Box>

            <Box flex={1} display="flex" flexDirection="column" justifyContent="space-between">
              <Box>
                <Chip
                  label={getTrainingStatusText()}
                  color={getTrainingStatusColor()}
                  variant="filled"
                  sx={{ 
                    mb: 2, 
                    fontWeight: 500,
                    ...(trainingStatus?.training_active && {
                      animation: 'statusPulse 2s ease-in-out infinite'
                    })
                  }}
                />
                
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Round: <Typography 
                    variant="body1"
                    component="span"
                    sx={{ 
                      opacity: refreshing ? 0.7 : 1,
                      transition: 'opacity 0.3s ease',
                      fontWeight: 500
                    }}
                  >
                    {loading ? (
                      <LoadingIndicator size={20} refreshing={refreshing} />
                    ) : (
                      formatRoundNumber(trainingStatus?.current_round || 0)
                    )}
                  </Typography>
                  
                </Typography>
                
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Accuracy: <MetricValue 
                    value={trainingStatus?.latest_accuracy || 0} 
                    loading={loading} 
                    formatter={formatAccuracy}
                    refreshing={refreshing}
                    variant="body1"
                  />
                </Typography>
                
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Loss: <MetricValue 
                    value={trainingStatus?.latest_loss || 0} 
                    loading={loading} 
                    formatter={formatLoss}
                    refreshing={refreshing}
                    variant="body1"
                  />
                </Typography>
                
                <Typography variant="body2" color="text.secondary">
                  Clients: <MetricValue 
                    value={trainingStatus?.connected_clients || 0} 
                    loading={loading} 
                    refreshing={refreshing}
                    variant="body1"
                    formatter={formatClientCount}
                  />
                </Typography>
              </Box>

             
            </Box>
          </CardContent>
        </Card>
        </FLDataTooltip>
      </Grid>

      {/* Performance Metrics Cards */}
      <Grid item xs={12} md={6} lg={4}>
        <FLDataTooltip
          title="Performance Metrics"
          description="Best accuracy and lowest loss achieved during federated learning training"
          dataSource={dataSource}
          isRealTime={isRealTime}
          additionalInfo={dataSource === 'mock' ? 'Sample performance metrics for demonstration' : 'Historical best values from training rounds'}
        >
          <Card 
            sx={{ 
              borderRadius: 2,
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              height: 280,
              display: 'flex',
              flexDirection: 'column',
              cursor: 'help'
            }}
            className="metric-card"
          >
          <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box display="flex" alignItems="center" mb={2}>
              <TrendingUpIcon color="primary" />
              <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
                Performance
              </Typography>
            </Box>

            <Box flex={1} display="flex" flexDirection="column" justifyContent="space-around">
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Tooltip title="Best accuracy achieved across all training rounds">
                  <Typography variant="body2" color="text.secondary">
                    Best Accuracy
                  </Typography>
                </Tooltip>
                <MetricValue 
                  value={summary?.bestAccuracy || 0} 
                  loading={loading} 
                  formatter={formatAccuracy}
                  refreshing={refreshing}
                />
              </Box>

              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Tooltip title="Lowest loss value achieved during training">
                  <Typography variant="body2" color="text.secondary">
                    Lowest Loss
                  </Typography>
                </Tooltip>
                <MetricValue 
                  value={summary?.lowestLoss || 0} 
                  loading={loading} 
                  formatter={formatLoss}
                  refreshing={refreshing}
                />
              </Box>

              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Tooltip title="Rate of accuracy improvement over time (requires at least 3 rounds with accuracy data)">
                  <Typography variant="body2" color="text.secondary">
                    Convergence Rate
                  </Typography>
                </Tooltip>
                <MetricValue 
                  value={summary?.convergenceRate || 0} 
                  loading={loading} 
                  formatter={(v) => {
                    const rate = Number(v);
                    if (rate === -1) return 'Insufficient data';
                    return `${rate.toFixed(2)}%`;
                  }}
                  refreshing={refreshing}
                />
              </Box>

              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Tooltip title="Consistency of training results across rounds (requires at least 3 rounds with accuracy data)">
                  <Typography variant="body2" color="text.secondary">
                    Stability Score
                  </Typography>
                </Tooltip>
                <MetricValue 
                  value={summary?.stabilityScore || 0} 
                  loading={loading} 
                  formatter={(v) => {
                    const score = Number(v);
                    if (score === -1) return 'Insufficient data';
                    return `${score.toFixed(1)}%`;
                  }}
                  refreshing={refreshing}
                />
              </Box>

              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Tooltip title="Overall training efficiency rating (requires accuracy and round data)">
                  <Typography variant="body2" color="text.secondary">
                    Efficiency Rating
                  </Typography>
                </Tooltip>
                <MetricValue 
                  value={summary?.efficiencyRating || 0} 
                  loading={loading} 
                  formatter={(v) => {
                    const rating = Number(v);
                    if (rating === -1) return 'Cannot calculate';
                    return `${rating.toFixed(1)}%`;
                  }}
                  refreshing={refreshing}
                />
              </Box>
            </Box>
          </CardContent>
        </Card>
        </FLDataTooltip>
      </Grid>

      {/* Resource Usage Card */}
      <Grid item xs={12} md={6} lg={4}>
        <Card 
          sx={{ 
            borderRadius: 2,
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            height: 280,
            display: 'flex',
            flexDirection: 'column'
          }}
          className="metric-card"
        >
          <CardContent sx={{ p: 3, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box display="flex" alignItems="center" mb={2}>
              <StorageIcon color="secondary" />
              <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
                Resource Usage
              </Typography>
            </Box>

            <Box flex={1} display="flex" flexDirection="column" justifyContent="space-around">
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="body2" color="text.secondary">
                  Total Rounds
                </Typography>
                <MetricValue 
                  value={summary?.totalRounds || 0} 
                  loading={loading} 
                  refreshing={refreshing}
                />
              </Box>

              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="body2" color="text.secondary">
                  Avg Clients
                </Typography>
                <MetricValue 
                  value={summary?.averageClientsConnected || 0} 
                  loading={loading} 
                  formatter={(v) => {
                    const count = Number(v);
                    if (count === -1) return 'Not available';
                    if (count <= 0) return 'No data';
                    return String(count);
                  }}
                  refreshing={refreshing}
                  variant="h6"
                />
              </Box>

              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="body2" color="text.secondary">
                  Avg Model Size
                </Typography>
                <MetricValue 
                  value={summary?.averageModelSize || 0} 
                  loading={loading} 
                  formatter={(v) => {
                    const size = Number(v);
                    if (size === -1) return 'Not provided';
                    if (size <= 0) return 'No data';
                    return formatModelSize(size);
                  }}
                  refreshing={refreshing}
                  variant="h6"
                />
              </Box>

              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Tooltip title="Average percentage of maximum clients participating in training (requires at least 3 rounds of data)">
                  <Typography variant="body2" color="text.secondary">
                    Participation Rate
                  </Typography>
                </Tooltip>
                <MetricValue 
                  value={summary?.participationRate || 0} 
                  loading={loading} 
                  formatter={(v) => {
                    const rate = Number(v);
                    if (rate === -1) return 'Insufficient data';
                    if (rate === 0) return 'No data';
                    return `${rate.toFixed(1)}%`;
                  }}
                  refreshing={refreshing}
                  variant="h6"
                />
              </Box>

              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Tooltip title="Consistency of client participation across training rounds (requires at least 3 rounds of data)">
                  <Typography variant="body2" color="text.secondary">
                    Client Reliability
                  </Typography>
                </Tooltip>
                <MetricValue 
                  value={summary?.clientReliabilityRate || 0} 
                  loading={loading} 
                  formatter={(v) => {
                    const rate = Number(v);
                    if (rate === -1) return 'Insufficient data';
                    if (rate === 0) return 'No data';
                    return `${rate.toFixed(1)}%`;
                  }}
                  refreshing={refreshing}
                  variant="h6"
                />
              </Box>

              {summary?.totalTrainingTime && (
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2" color="text.secondary">
                    Training Time
                  </Typography>
                  <MetricValue 
                    value={summary.totalTrainingTime} 
                    loading={loading} 
                    formatter={formatDuration}
                    refreshing={refreshing}
                  />
                </Box>
              )}
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* System Status Cards */}
      <Grid item xs={12} md={6}>
        <Card sx={{ borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
          <CardContent sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" mb={2}>
              <SpeedIcon color="primary" />
              <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
                System Status
              </Typography>
            </Box>

            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    FL Server
                  </Typography>
                  <Chip
                    label={trainingStatus?.fl_server_available ? 'Available' : 'Offline'}
                    color={trainingStatus?.fl_server_available ? 'success' : 'error'}
                    size="small"
                    variant="outlined"
                  />
                </Box>
              </Grid>
              <Grid item xs={6}>
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Collector
                  </Typography>
                  <Chip
                    label={trainingStatus?.collector_monitoring ? 'Monitoring' : 'Inactive'}
                    color={trainingStatus?.collector_monitoring ? 'success' : 'warning'}
                    size="small"
                    variant="outlined"
                  />
                </Box>
              </Grid>
            </Grid>

            <Box mt={2}>
              <Typography variant="caption" color="text.secondary">
                Last Updated: {new Date(lastUpdateTime).toLocaleTimeString()}
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Quick Stats */}
      <Grid item xs={12} md={6}>
        <Card sx={{ borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
          <CardContent sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" mb={2}>
              <TimerIcon color="secondary" />
              <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
                Training Stats
              </Typography>
            </Box>

            <Grid container spacing={2}>
              {summary?.averageRoundDuration && (
                <Grid item xs={6}>
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Avg Round Duration
                    </Typography>
                    <Typography variant="h6">
                      {formatDuration(summary.averageRoundDuration)}
                    </Typography>
                  </Box>
                </Grid>
              )}
              
              {summary?.fastestRound && (
                <Grid item xs={6}>
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Fastest Round
                    </Typography>
                    <Typography variant="h6">
                      {formatDuration(summary.fastestRound)}
                    </Typography>
                  </Box>
                </Grid>
              )}

              {summary?.trainingEfficiency && summary.trainingEfficiency !== -1 && (
                <Grid item xs={6}>
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Training Efficiency
                    </Typography>
                    <Typography variant="h6">
                      {summary.trainingEfficiency.toFixed(3)}/min
                    </Typography>
                  </Box>
                </Grid>
              )}
              
              {(!summary?.trainingEfficiency || summary.trainingEfficiency === -1) && (
                <Grid item xs={6}>
                  <Box>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Training Efficiency
                    </Typography>
                    <Typography variant="body2" color="text.disabled">
                      Cannot calculate
                    </Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          </CardContent>
        </Card>
      </Grid>

      {/* Enhanced Training Overview Card */}
      <Grid item xs={12}>
        <Card sx={{ borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
          <CardContent sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
              <Box display="flex" alignItems="center">
                <TrendingUpIcon color="primary" />
                <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
                  Training Progress Summary
                </Typography>
              </Box>
              <Chip
                label={summary?.totalRounds && summary.totalRounds > 0 ? 
                  `${summary.totalRounds} Rounds Completed` : 
                  'No rounds completed'
                }
                color="primary"
                variant="outlined"
                size="small"
              />
            </Box>

            <Grid container spacing={3}>
              {/* Current Progress */}
              <Grid item xs={12} md={3}>
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Current Progress
                  </Typography>
                  <Box display="flex" alignItems="center" gap={2}>
                    <Box flex={1}>
                      <LinearProgress 
                        variant="determinate" 
                        value={trainingStatus?.max_rounds && trainingStatus.max_rounds > 0 
                          ? Math.min(100, (trainingStatus.current_round || 0) / trainingStatus.max_rounds * 100)
                          : 0} 
                        sx={{ 
                          height: 8, 
                          borderRadius: 4,
                          backgroundColor: 'rgba(0,0,0,0.1)',
                          '& .MuiLinearProgress-bar': {
                            borderRadius: 4
                          }
                        }}
                      />
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: 40 }}>
                      {trainingStatus?.max_rounds && trainingStatus.max_rounds > 0 
                        ? Math.round((trainingStatus.current_round || 0) / trainingStatus.max_rounds * 100)
                        : 0}%
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    Round {formatRoundNumber(trainingStatus?.current_round)}
                  </Typography>
                </Box>
              </Grid>

              {/* Best Performance */}
              <Grid item xs={12} md={3}>
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Best Performance
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="h5" color="primary.main">
                      {formatAccuracy(summary?.bestAccuracy || 0)}
                    </Typography>
                    {summary?.convergenceRate && summary.convergenceRate > 0 && (
                      <Chip
                        label={`+${summary.convergenceRate.toFixed(1)}%`}
                        color="success"
                        size="small"
                        sx={{ height: 20, fontSize: '0.75rem' }}
                      />
                    )}
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    Accuracy achieved
                  </Typography>
                </Box>
              </Grid>

              {/* Training Efficiency */}
              <Grid item xs={12} md={3}>
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Training Efficiency
                  </Typography>
                  <Typography variant="h5" color="secondary.main">
                    {summary?.efficiencyRating?.toFixed(1) || 0}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Overall efficiency rating
                  </Typography>
                </Box>
              </Grid>

              {/* System Health */}
              <Grid item xs={12} md={3}>
                <Box>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    System Health
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Box
                      sx={{
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        backgroundColor: trainingStatus?.fl_server_available ? 'success.main' : 'error.main'
                      }}
                    />
                    <Typography variant="body2">
                      {trainingStatus?.fl_server_available ? 'Healthy' : 'Issues Detected'}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {summary?.participationRate !== undefined && summary.participationRate !== -1 ? 
                      `${summary.participationRate.toFixed(0)}% client participation rate` : 
                      'Client participation data requires more training rounds'
                    }
                  </Typography>
                </Box>
              </Grid>
            </Grid>

            {/* Key Metrics Row */}
            <Box mt={3} pt={3} sx={{ borderTop: '1px solid rgba(0,0,0,0.1)' }}>
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Box textAlign="center">
                    <Typography variant="h6" color="primary.main">
                      {summary?.averageRoundDuration ? formatDuration(summary.averageRoundDuration) : 'N/A'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Avg Round Duration
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box textAlign="center">
                    <Typography variant="h6" color="secondary.main">
                      {summary?.stabilityScore !== undefined && summary.stabilityScore !== -1 ? 
                        `${summary.stabilityScore.toFixed(1)}%` : 
                        'Not available'
                      }
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Training Stability
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h6" color="success.main">
                      {summary?.averageClientsConnected !== undefined && summary.averageClientsConnected !== -1 ? 
                        summary.averageClientsConnected : 
                        'Not available'
                      }
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Avg Clients
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box textAlign="center">
                    <Typography variant="h6" color="warning.main">
                      {formatLoss(summary?.lowestLoss || 0)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Lowest Loss
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
    </Box>
  );
}; 