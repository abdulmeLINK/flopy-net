import React, { useState, useEffect } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Stack,
  LinearProgress,
  Divider,
  Chip,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  Router as RouterIcon,
  Computer as ComputerIcon,
  Cable as CableIcon,
  NetworkCheck as NetworkCheckIcon,
  Speed as SpeedIcon,
  QueryStats as QueryStatsIcon,
  Timeline as TimelineIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon
} from '@mui/icons-material';
import { getEnhancedPerformanceMetrics, EnhancedPerformanceMetrics } from '../../services/networkApi';

interface NetworkOverviewTabProps {
  networkStats: any;
  refreshing: boolean;
}

// Enhanced tooltip component for network data
const NetworkDataTooltip: React.FC<{
  children: React.ReactElement;
  title: string;
  description: string;
  dataSource: 'real' | 'mock' | 'sdn' | 'collector' | 'gns3';
  isLive?: boolean;
  additionalInfo?: string;
}> = ({ children, title, description, dataSource, isLive = false, additionalInfo }) => {
  const getSourceColor = (source: string) => {
    switch (source) {
      case 'real': return '#4caf50';
      case 'sdn': return '#2196f3';
      case 'collector': return '#9c27b0';
      case 'gns3': return '#ff9800';
      case 'mock': return '#f44336';
      default: return '#757575';
    }
  };

  const getSourceLabel = (source: string) => {
    switch (source) {
      case 'real': return 'Live Network Data';
      case 'sdn': return 'SDN Controller';
      case 'collector': return 'Collector Service';
      case 'gns3': return 'GNS3 Network';
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
        {isLive && (
          <Chip 
            label="Live Data"
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

const MetricCard: React.FC<{
  title: string;
  value: React.ReactNode;
  subtitle: React.ReactNode;
  icon: React.ReactNode;
  color: string;
  refreshing: boolean;
}> = ({ title, value, subtitle, icon, color, refreshing }) => (
  <Card sx={{ height: '140px', display: 'flex', flexDirection: 'column' }}>
    <CardContent sx={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', p: 2 }}>
      <Box display="flex" alignItems="center" mb={1}>
        {icon}
        <Typography variant="h6" noWrap sx={{ ml: 1 }}>{title}</Typography>
      </Box>
      <Typography 
        variant="h3" 
        color={color} 
        sx={{ 
          mb: 1, 
          lineHeight: 1,
          opacity: refreshing ? 0.7 : 1,
          transition: 'opacity 0.3s ease'
        }}
      >
        {value}
      </Typography>
      <Typography 
        variant="body2" 
        color="text.secondary" 
        sx={{ 
          fontSize: '0.75rem', 
          lineHeight: 1.2,
          opacity: refreshing ? 0.7 : 1,
          transition: 'opacity 0.3s ease'
        }}
      >
        {subtitle}
      </Typography>
    </CardContent>
  </Card>
);

export const NetworkOverviewTab: React.FC<NetworkOverviewTabProps> = ({
  networkStats,
  refreshing
}) => {
  const [enhancedMetrics, setEnhancedMetrics] = useState<EnhancedPerformanceMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(true);

  // Determine data source based on available data
  const getDataSource = (): 'real' | 'mock' | 'sdn' | 'collector' | 'gns3' => {
    if (!networkStats) return 'mock';
    if (networkStats.sdn_controller?.status === 'connected') return 'sdn';
    if (networkStats.gns3_status?.connection_status === 'connected') return 'gns3';
    if (networkStats.last_updated) return 'collector';
    return 'mock';
  };

  const dataSource = getDataSource();
  const isLive = dataSource === 'sdn' || dataSource === 'gns3' || dataSource === 'collector';

  useEffect(() => {
    const fetchEnhancedMetrics = async () => {
      try {
        setMetricsLoading(true);
        const metrics = await getEnhancedPerformanceMetrics();
        setEnhancedMetrics(metrics);
      } catch (error) {
        console.warn('Failed to fetch enhanced metrics:', error);
      } finally {
        setMetricsLoading(false);
      }
    };

    fetchEnhancedMetrics();

    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchEnhancedMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  // Utility functions
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatBandwidth = (bps: number): string => {
    if (bps === 0) return '0 bps';
    const k = 1000;
    const sizes = ['bps', 'Kbps', 'Mbps', 'Gbps'];
    const i = Math.floor(Math.log(bps) / Math.log(k));
    return parseFloat((bps / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDuration = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const getHealthColor = (score: number): string => {
    if (score >= 80) return 'success.main';
    if (score >= 60) return 'warning.main';
    return 'error.main';
  };
  return (
    <Box>
      {/* Enhanced Header with Data Source Information */}
      <Box sx={{ mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 600 }}>
            Network Overview
          </Typography>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip 
              label={dataSource === 'real' ? 'Live Network Data' : 
                     dataSource === 'sdn' ? 'SDN Controller' :
                     dataSource === 'gns3' ? 'GNS3 Network' :
                     dataSource === 'collector' ? 'Collector Service' : 'Demo Data'}
              color={dataSource === 'real' || dataSource === 'sdn' ? 'success' : 
                     dataSource === 'gns3' || dataSource === 'collector' ? 'primary' : 'warning'}
              size="small"
              sx={{ fontWeight: 500 }}
            />
            {isLive && (
              <Chip 
                label="Live Monitoring"
                size="small"
                color="info"
                variant="outlined"
              />
            )}
            {refreshing && (
              <Chip 
                label="Refreshing..."
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
              <Typography variant="h6">Network Monitoring Data Information</Typography>
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
                      'This dashboard displays live network performance data collected from network devices and monitoring systems. All metrics reflect actual network conditions including bandwidth usage, latency, packet loss, and device health.' :
                      dataSource === 'sdn' ?
                      'Connected to SDN controller for real-time network statistics. Flow information, switch status, and traffic patterns are updated as network conditions change.' :
                      dataSource === 'gns3' ?
                      'Network data from GNS3 network simulator. Shows virtualized network performance metrics and device status from the simulated network topology.' :
                      dataSource === 'collector' ?
                      'Data aggregated by the collector service from multiple network monitoring sources. Includes historical trends and current network performance indicators.' :
                      'This is demonstration data for testing purposes. It simulates realistic network performance metrics and device behavior for evaluation.'}
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
                      <NetworkCheckIcon fontSize="small" color="success" />
                      <Typography variant="body2"><strong>Health:</strong> Overall network status</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <SpeedIcon fontSize="small" color="primary" />
                      <Typography variant="body2"><strong>Bandwidth:</strong> Data transfer rates</Typography>
                    </Box>
                  </Grid>
                  <Grid item xs={6}>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <QueryStatsIcon fontSize="small" color="warning" />
                      <Typography variant="body2"><strong>Latency:</strong> Response times</Typography>
                    </Box>
                    <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                      <TimelineIcon fontSize="small" color="error" />
                      <Typography variant="body2"><strong>Packet Loss:</strong> Data transmission errors</Typography>
                    </Box>
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" color="text.secondary">
              <strong>Data Quality:</strong> {dataSource === 'mock' ? 'Demo data for demonstration - not connected to actual network infrastructure' : 'Live data from network monitoring infrastructure with automatic refresh every 5 seconds'}
            </Typography>
          </AccordionDetails>
        </Accordion>
      </Box>

      <Grid container spacing={3}>      {/* Network Health & Performance Overview */}
      <Grid item xs={12} md={3}>
        <NetworkDataTooltip
          title="Network Health Score"
          description="Overall network health calculated from latency, packet loss, bandwidth utilization, and device status"
          dataSource={dataSource}
          isLive={isLive}
          additionalInfo={dataSource === 'mock' ? 'Sample health score for demonstration' : 'Real-time health monitoring with 5-second updates'}
        >
          <div>
            <MetricCard
              title="Network Health"
              value={metricsLoading ? "..." : `${enhancedMetrics?.health_score || 0}`}
              subtitle="Overall score (0-100)"
              icon={<NetworkCheckIcon color="primary" />}
              color={metricsLoading ? "text.secondary" : getHealthColor(enhancedMetrics?.health_score || 0)}
              refreshing={refreshing || metricsLoading}
            />
          </div>
        </NetworkDataTooltip>
      </Grid>

      <Grid item xs={12} md={3}>
        <NetworkDataTooltip
          title="Network Bandwidth"
          description="Current total bandwidth usage across all network interfaces and peak bandwidth recorded"
          dataSource={dataSource}
          isLive={isLive}
          additionalInfo={dataSource === 'mock' ? 'Sample bandwidth data for demonstration' : 'Live bandwidth monitoring from network interfaces'}
        >
          <div>
            <MetricCard
              title="Current Bandwidth"
              value={metricsLoading ? "..." : formatBandwidth(enhancedMetrics?.bandwidth.current_total_bps || 0)}
              subtitle={`Peak: ${formatBandwidth(enhancedMetrics?.bandwidth.peak_bandwidth_bps || 0)}`}
              icon={<SpeedIcon color="primary" />}
              color="primary"
              refreshing={refreshing || metricsLoading}
            />
          </div>
        </NetworkDataTooltip>
      </Grid>

      <Grid item xs={12} md={3}>
        <MetricCard
          title="Average Latency"
          value={metricsLoading ? "..." : `${enhancedMetrics?.latency.average_ms?.toFixed(1) || 0.0} ms`}
          subtitle={`Range: ${enhancedMetrics?.latency.min_ms?.toFixed(1) || 0} - ${enhancedMetrics?.latency.max_ms?.toFixed(1) || 0} ms`}
          icon={<TimelineIcon color="warning" />}
          color="warning.main"
          refreshing={refreshing || metricsLoading}
        />
      </Grid>

      <Grid item xs={12} md={3}>
        <MetricCard
          title="Active Flows"
          value={metricsLoading ? "..." : `${enhancedMetrics?.flows.active || 0}`}
          subtitle={`Total: ${enhancedMetrics?.flows.total || 0} flows`}
          icon={<QueryStatsIcon color="success" />}
          color="success.main"
          refreshing={refreshing || metricsLoading}
        />
      </Grid>

      {/* Topology Information */}
      <Grid item xs={12}>
        <Typography variant="h6" gutterBottom sx={{ mt: 2, mb: 1, fontWeight: 600 }}>
          Network Topology
        </Typography>
      </Grid>
      
      <Grid item xs={12} md={3}>
        <MetricCard
          title="Switches"
          value={networkStats?.topology?.total_switches || enhancedMetrics?.ports.total || 0}
          subtitle={`${enhancedMetrics?.ports.up || 0} ports up`}
          icon={<RouterIcon color="primary" />}
          color="primary"
          refreshing={refreshing || metricsLoading}
        />
      </Grid>

      <Grid item xs={12} md={3}>
        <MetricCard
          title="Hosts"
          value={networkStats?.topology?.total_hosts || 0}
          subtitle="Connected devices"
          icon={<ComputerIcon color="success" />}
          color="success.main"
          refreshing={refreshing}
        />
      </Grid>

      <Grid item xs={12} md={3}>
        <MetricCard
          title="Links"
          value={networkStats?.topology?.total_links || 0}
          subtitle="Network connections"
          icon={<CableIcon color="warning" />}
          color="warning.main"
          refreshing={refreshing}
        />
      </Grid>

      <Grid item xs={12} md={3}>
        <MetricCard
          title="Port Errors"
          value={metricsLoading ? "..." : `${enhancedMetrics?.ports.errors || 0}`}
          subtitle="Error count"
          icon={<NetworkCheckIcon color="error" />}
          color={enhancedMetrics?.ports.errors ? "error.main" : "success.main"}
          refreshing={refreshing || metricsLoading}
        />
      </Grid>

      {/* Real-time Statistics */}
      <Grid item xs={12} md={6}>
        <Card sx={{ minHeight: '300px' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Real-time Statistics
            </Typography>
            <Stack spacing={2} sx={{ opacity: refreshing || metricsLoading ? 0.7 : 1, transition: 'opacity 0.3s ease' }}>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Data Transfer Rate
                </Typography>
                <Typography variant="h5" color="primary">
                  {formatBytes(enhancedMetrics?.rates.bytes_per_second || 0)}/s
                </Typography>
              </Box>
              
              <Divider />
              
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Packet Rate
                </Typography>
                <Typography variant="h5" color="success.main">
                  {(enhancedMetrics?.rates.packets_per_second || 0).toLocaleString()} pps
                </Typography>
              </Box>
              
              <Divider />
              
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Flow Creation Rate
                </Typography>
                <Typography variant="h5" color="info.main">
                  {(enhancedMetrics?.rates.flows_per_hour || 0).toFixed(1)} flows/hour
                </Typography>
              </Box>
              
              <Divider />
              
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Network Uptime
                </Typography>
                <Typography variant="h5" color="warning.main">
                  {formatDuration(enhancedMetrics?.totals.uptime_seconds || 0)}
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      {/* Cumulative Totals */}
      <Grid item xs={12} md={6}>
        <Card sx={{ minHeight: '300px' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Cumulative Statistics
            </Typography>
            <Stack spacing={2} sx={{ opacity: refreshing || metricsLoading ? 0.7 : 1, transition: 'opacity 0.3s ease' }}>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Total Bytes Transferred
                </Typography>
                <Typography variant="h5" color="primary">
                  {formatBytes(enhancedMetrics?.totals.bytes_transferred || 0)}
                </Typography>
              </Box>
              
              <Divider />
              
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Total Packets Transferred
                </Typography>
                <Typography variant="h5" color="success.main">
                  {(enhancedMetrics?.totals.packets_transferred || 0).toLocaleString()}
                </Typography>
              </Box>
              
              <Divider />
              
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Total Flows Created
                </Typography>
                <Typography variant="h5" color="info.main">
                  {(enhancedMetrics?.totals.flows_created || 0).toLocaleString()}
                </Typography>
              </Box>
              
              <Divider />
              
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Health Score Progress
                </Typography>
                <Box display="flex" alignItems="center" mt={1}>
                  <Box width="100%" mr={1}>
                    <LinearProgress 
                      variant="determinate" 
                      value={enhancedMetrics?.health_score || 0} 
                      color={enhancedMetrics?.health_score && enhancedMetrics.health_score >= 80 ? 'success' : enhancedMetrics?.health_score && enhancedMetrics.health_score >= 60 ? 'warning' : 'error'}
                    />
                  </Box>
                  <Box minWidth={35}>
                    <Typography variant="body2" color="text.secondary">
                      {`${Math.round(enhancedMetrics?.health_score || 0)}%`}
                    </Typography>
                  </Box>
                </Box>
              </Box>
            </Stack>
          </CardContent>        </Card>
      </Grid>
    </Grid>
    </Box>
  );
};
