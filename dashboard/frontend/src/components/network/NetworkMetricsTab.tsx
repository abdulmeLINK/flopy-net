import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Chip,
  LinearProgress,
  useTheme,
  alpha
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Speed as SpeedIcon,
  NetworkCheck as NetworkCheckIcon,
  Timer as TimerIcon,
  Assessment as AssessmentIcon,
  Clear as ClearIcon
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer
} from 'recharts';
import { getEnhancedPerformanceMetrics, EnhancedPerformanceMetrics } from '../../services/networkApi';

interface MetricsHistory {
  timestamp: number;
  bandwidth_bps: number;
  latency_ms: number;
  packets_per_second: number;
  flows_active: number;
  health_score: number;
}

const METRICS_HISTORY_KEY = 'networkMetricsHistory';
const MAX_HISTORY_POINTS = 50;

const NetworkMetricsTab: React.FC = () => {
  const theme = useTheme();
  const [metrics, setMetrics] = useState<EnhancedPerformanceMetrics | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<MetricsHistory[]>(() => {
    // Load persisted metrics history from localStorage on initialization
    try {
      const saved = localStorage.getItem(METRICS_HISTORY_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        // Filter out data older than 1 hour to prevent stale data
        const oneHourAgo = Date.now() - (60 * 60 * 1000);
        return parsed.filter((item: MetricsHistory) => item.timestamp > oneHourAgo);
      }
    } catch (error) {
      console.warn('Failed to load metrics history from localStorage:', error);
    }
    return [];
  });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchMetrics = useCallback(async (isRefresh = false) => {
    try {
      if (!isRefresh) setLoading(true);
      setRefreshing(isRefresh);
      setError(null);

      const data = await getEnhancedPerformanceMetrics();
      setMetrics(data);
      setLastUpdated(new Date());      // Add to history for charts
      const historyPoint: MetricsHistory = {
        timestamp: Date.now(),
        bandwidth_bps: data.bandwidth?.current_total_bps || 0,
        latency_ms: data.latency?.average_ms || 0,
        packets_per_second: data.rates?.packets_per_second || 0,
        flows_active: data.flows?.active || 0,
        health_score: data.network_health?.score || 0
      };

      setMetricsHistory(prev => {
        const newHistory = [...prev, historyPoint];
        // Keep last 50 data points for charts
        const trimmedHistory = newHistory.slice(-MAX_HISTORY_POINTS);
        
        // Persist to localStorage
        try {
          localStorage.setItem(METRICS_HISTORY_KEY, JSON.stringify(trimmedHistory));
        } catch (error) {
          console.warn('Failed to save metrics history to localStorage:', error);
        }
        
        return trimmedHistory;
      });

    } catch (err) {
      console.error('Failed to fetch metrics:', err);
      setError('Failed to load performance metrics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }  }, []);

  useEffect(() => {
    fetchMetrics();
    
    // Auto-refresh every 5 seconds
    const interval = setInterval(() => fetchMetrics(true), 5000);
    return () => clearInterval(interval);
  }, [fetchMetrics]);

  const clearMetricsHistory = useCallback(() => {
    setMetricsHistory([]);
    try {
      localStorage.removeItem(METRICS_HISTORY_KEY);
    } catch (error) {
      console.warn('Failed to clear metrics history from localStorage:', error);
    }
  }, []);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  const formatBandwidth = (bps: number): string => {
    if (bps === 0) return '0 bps';
    const k = 1000;
    const sizes = ['bps', 'Kbps', 'Mbps', 'Gbps'];
    const i = Math.floor(Math.log(bps) / Math.log(k));
    return `${parseFloat((bps / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
  };

  const formatDuration = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours}h ${minutes}m ${secs}s`;
  };

  const getHealthColor = (score: number): string => {
    if (score >= 90) return theme.palette.success.main;
    if (score >= 70) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  const getHealthStatus = (score: number): string => {
    if (score >= 90) return 'Excellent';
    if (score >= 70) return 'Good';
    if (score >= 50) return 'Fair';
    return 'Poor';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="h6" sx={{ ml: 2 }}>
          Loading performance metrics...
        </Typography>
      </Box>
    );
  }

  if (error || !metrics) {
    return (
      <Box p={3}>
        <Alert severity="error" action={
          <IconButton color="inherit" onClick={() => fetchMetrics()}>
            <RefreshIcon />
          </IconButton>
        }>
          {error || 'No metrics data available'}
        </Alert>
      </Box>
    );
  }

  return (
    <Box p={3}>
      {/* Header with refresh */}
      <Box display="flex" justifyContent="between" alignItems="center" mb={3}>
        <Typography variant="h5" component="h2">
          Network Performance Metrics
        </Typography>        <Box display="flex" alignItems="center" gap={2}>
          {metricsHistory.length > 0 && (
            <Chip 
              label={`${metricsHistory.length} data points`}
              size="small"
              variant="outlined"
              color="info"
            />
          )}
          {lastUpdated && (
            <Typography variant="body2" color="text.secondary">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </Typography>
          )}
          <Tooltip title="Clear chart history">
            <IconButton 
              onClick={clearMetricsHistory}
              color="secondary"
              size="small"
            >
              <ClearIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Refresh metrics">
            <IconButton 
              onClick={() => fetchMetrics(true)} 
              disabled={refreshing}
              color="primary"
            >
              <RefreshIcon className={refreshing ? 'rotate' : ''} />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Overview Cards */}
      <Grid container spacing={3} mb={3}>
        {/* Health Score */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Network Health
                  </Typography>                  <Typography variant="h4" component="div">
                    {metrics.network_health?.score || 0}
                  </Typography>
                  <Chip 
                    label={getHealthStatus(metrics.network_health?.score || 0)}
                    sx={{ 
                      backgroundColor: alpha(getHealthColor(metrics.network_health?.score || 0), 0.1),
                      color: getHealthColor(metrics.network_health?.score || 0),
                      fontWeight: 'bold'
                    }}
                    size="small"
                  />
                </Box>
                <AssessmentIcon sx={{ fontSize: 40, color: getHealthColor(metrics.network_health.score) }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Current Bandwidth */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Current Bandwidth
                  </Typography>                  <Typography variant="h6" component="div">
                    {formatBandwidth(metrics.bandwidth?.current_total_bps || 0)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Peak: {formatBandwidth(metrics.bandwidth?.peak_bandwidth_bps || 0)}
                  </Typography>
                </Box>
                <SpeedIcon sx={{ fontSize: 40, color: theme.palette.primary.main }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Latency */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Average Latency
                  </Typography>                  <Typography variant="h6" component="div">
                    {(metrics.latency?.average_ms || 0).toFixed(1)} ms
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Min: {(metrics.latency?.min_ms || 0).toFixed(1)}ms Max: {(metrics.latency?.max_ms || 0).toFixed(1)}ms
                  </Typography>
                </Box>
                <TimerIcon sx={{ fontSize: 40, color: theme.palette.secondary.main }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Active Flows */}
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Active Flows
                  </Typography>                  <Typography variant="h6" component="div">
                    {(metrics.flows?.active || 0)} / {(metrics.flows?.total || 0)}
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={metrics.flows?.total ? ((metrics.flows?.active || 0) / (metrics.flows?.total || 1)) * 100 : 0}
                    sx={{ mt: 1 }}
                  />
                </Box>
                <NetworkCheckIcon sx={{ fontSize: 40, color: theme.palette.info.main }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts Grid */}
      <Grid container spacing={3}>
        {/* Bandwidth Over Time */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="h3" gutterBottom>
                Bandwidth Over Time
              </Typography>              <ResponsiveContainer width="100%" height={300}>
                {metricsHistory.length > 0 ? (
                  <AreaChart data={metricsHistory}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp"
                      tickFormatter={(timestamp) => new Date(timestamp).toLocaleTimeString()}
                    />
                    <YAxis tickFormatter={formatBandwidth} />
                    <RechartsTooltip 
                      labelFormatter={(timestamp) => new Date(timestamp).toLocaleString()}
                      formatter={(value) => [formatBandwidth(value as number), 'Bandwidth']}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="bandwidth_bps" 
                      stroke={theme.palette.primary.main}
                      fill={alpha(theme.palette.primary.main, 0.3)}
                    />
                  </AreaChart>
                ) : (
                  <Box display="flex" alignItems="center" justifyContent="center" height="100%">
                    <Typography color="text.secondary">
                      No historical data available. Data will appear as metrics are collected.
                    </Typography>
                  </Box>
                )}
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Latency Over Time */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="h3" gutterBottom>
                Latency Over Time
              </Typography>              <ResponsiveContainer width="100%" height={300}>
                {metricsHistory.length > 0 ? (
                  <LineChart data={metricsHistory}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp"
                      tickFormatter={(timestamp) => new Date(timestamp).toLocaleTimeString()}
                    />
                    <YAxis />
                    <RechartsTooltip 
                      labelFormatter={(timestamp) => new Date(timestamp).toLocaleString()}
                      formatter={(value) => [`${value} ms`, 'Latency']}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="latency_ms" 
                      stroke={theme.palette.secondary.main}
                      strokeWidth={2}
                      dot={{ fill: theme.palette.secondary.main }}
                    />
                  </LineChart>
                ) : (
                  <Box display="flex" alignItems="center" justifyContent="center" height="100%">
                    <Typography color="text.secondary">
                      No historical data available. Data will appear as metrics are collected.
                    </Typography>
                  </Box>
                )}
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Total Statistics */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="h3" gutterBottom>
                Cumulative Statistics
              </Typography>
              <Grid container spacing={2}>                <Grid item xs={6}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="primary">
                      {formatBytes(metrics.totals?.bytes_transferred || 0)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Data Transferred
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="primary">
                      {(metrics.totals?.packets_transferred || 0).toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Packets
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="primary">
                      {metrics.flows?.total || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Flows
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={6}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="primary">
                      {metrics.ports?.up || 0} / {metrics.ports?.total || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Active Ports
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Real-time Rates */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="h3" gutterBottom>
                Real-time Rates
              </Typography>              <Box display="flex" flexDirection="column" gap={2}>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Data Rate
                  </Typography>
                  <Typography variant="h5">
                    {formatBytes(metrics.rates?.bytes_per_second || 0)}/s
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Packet Rate
                  </Typography>
                  <Typography variant="h5">
                    {(metrics.rates?.packets_per_second || 0).toFixed(1)} pps
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Flow Creation Rate
                  </Typography>
                  <Typography variant="h5">
                    {(metrics.rates?.flows_per_hour || 0).toFixed(1)} flows/hour
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default NetworkMetricsTab;
export { NetworkMetricsTab };
