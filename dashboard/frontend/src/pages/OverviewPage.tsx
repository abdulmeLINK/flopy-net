import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Box, 
  Grid, 
  Typography,
  Card, 
  CardContent, 
  Chip, 
  Alert, 
  Skeleton,
  IconButton,
  Tooltip,
  CircularProgress
} from '@mui/material';
import { 
  Refresh as RefreshIcon, 
  Schedule as ScheduleIcon
} from '@mui/icons-material';
import { 
  getFLStatus, 
  getNetworkStatus, 
  getEventsSummary, 
  FLStatus, 
  NetworkStatus, 
  EventsSummary
} from '../services/overviewApi';
import {
  getPolicies,
  getPolicyDecisions,
  getPolicyEngineStatus
} from '../services/policyApi';
import { FL_THRESHOLDS, NETWORK_THRESHOLDS, POLICY_THRESHOLDS, TIMING, getStatusIndicator, getFLStatusColor, getNetworkStatusColor } from '../config/thresholds';
import { useFLData } from '../components/fl/hooks/useFLData';

interface ComponentState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  refreshing: boolean;
}

interface CalculatedPolicyStatus {
  active_policies: number;
  decisions_last_hour: number;
  allow_count_last_hour: number;
  deny_count_last_hour: number;
  avg_decision_time_ms: number;
  status: string;
  error?: string;
}

const OverviewPage = () => {
  const navigate = useNavigate();
  
  // Hook for FL data with proper color logic
  const flDataHook = useFLData();
  
  // Individual state for each component to prevent interruptions
  const [flState, setFlState] = useState<ComponentState<FLStatus>>({
    data: null,
    loading: true,
    error: null,
    lastUpdated: null,
    refreshing: false
  });
  
  const [networkState, setNetworkState] = useState<ComponentState<NetworkStatus>>({
    data: null,
    loading: true,
    error: null,
    lastUpdated: null,
    refreshing: false
  });
  
  const [policyState, setPolicyState] = useState<ComponentState<CalculatedPolicyStatus>>({
    data: null,
    loading: true,
    error: null,
    lastUpdated: null,
    refreshing: false
  });
  
  const [eventsState, setEventsState] = useState<ComponentState<EventsSummary>>({
    data: null,
    loading: true,
    error: null,
    lastUpdated: null,
    refreshing: false
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Refs to track component mount state and prevent memory leaks
  const isMountedRef = useRef(true);

  // Generic fetch function with graceful error handling for manual refresh
  const createManualFetcher = <T,>(
    fetchFn: () => Promise<T>,
    setState: React.Dispatch<React.SetStateAction<ComponentState<T>>>,
    componentName: string
  ) => {
    return async (isRefresh = false) => {
      if (!isMountedRef.current) return;

      try {
        // Set loading state without clearing existing data
        setState(prev => ({
          ...prev,
          loading: !isRefresh && !prev.data, // Only show loading spinner on initial load
          refreshing: isRefresh,
          error: null
        }));

        const data = await fetchFn();
        
        if (isMountedRef.current) {
          setState(prev => ({
            ...prev,
            data,
            loading: false,
            refreshing: false,
            error: null,
            lastUpdated: new Date()
          }));
        }
      } catch (error) {
        console.error(`Failed to fetch ${componentName} data:`, error);
        
        if (isMountedRef.current) {
          setState(prev => ({
            ...prev,
            loading: false,
            refreshing: false,
            error: `Failed to load ${componentName} data`
            // Keep existing data on error
          }));
        }
      }
    };
  };

  // Create individual fetchers for manual refresh
  const fetchFLData = useCallback(
    createManualFetcher(getFLStatus, setFlState, 'FL'),
    []
  );

  const fetchNetworkData = useCallback(
    createManualFetcher(getNetworkStatus, setNetworkState, 'Network'),
    []
  );

  const fetchPolicyData = useCallback(async (isRefresh = false) => {
    if (!isMountedRef.current) return;

    try {
      // Set loading state without clearing existing data
      setPolicyState(prev => ({
        ...prev,
        loading: !isRefresh && !prev.data, // Only show loading spinner on initial load
        refreshing: isRefresh,
        error: null
      }));

      // Use the backend API to get policy status summary
      const response = await fetch('/api/policy-engine/status');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const policyData = await response.json();

      if (isMountedRef.current) {
        setPolicyState(prev => ({
          ...prev,
          data: policyData,
          loading: false,
          refreshing: false,
          error: null,
          lastUpdated: new Date()
        }));
      }
    } catch (error) {
      console.error(`Error fetching Policy data:`, error);
      if (isMountedRef.current) {
        setPolicyState(prev => ({
          ...prev,
          loading: false,
          refreshing: false,
          error: error instanceof Error ? error.message : 'Failed to fetch policy data'
        }));
      }
    }
  }, []);

  const fetchEventsData = useCallback(
    createManualFetcher(getEventsSummary, setEventsState, 'Events'),
    []
  );

  // Manual refresh functions
  const refreshFL = () => fetchFLData(true);
  const refreshNetwork = () => fetchNetworkData(true);
  const refreshPolicy = () => fetchPolicyData(true);
  
  // Global refresh function that refreshes all data in parallel
  const refreshAll = async () => {
    // Manually fetch all data if WebSocket is not connected or for explicit refresh
    const promises = [
      fetchFLData(true),
      fetchNetworkData(true),
      fetchPolicyData(true),
      fetchEventsData(true)
    ];
    
    await Promise.allSettled(promises);
  };

  // Initial load - completely parallel and show cached data instantly
  const initialLoadViaRest = async () => {
    setFlState(prev => ({ ...prev, loading: true, refreshing: false }));
    setNetworkState(prev => ({ ...prev, loading: true, refreshing: false }));
    setPolicyState(prev => ({ ...prev, loading: true, refreshing: false }));
    setEventsState(prev => ({ ...prev, loading: true, refreshing: false }));
    
    // Start all API calls in parallel immediately
    const flPromise = fetchFLData(false);
    const networkPromise = fetchNetworkData(false);
    const policyPromise = fetchPolicyData(false);
    const eventsPromise = fetchEventsData(false);
    
    // Don't wait for all to complete - let them update independently
    Promise.allSettled([flPromise, networkPromise, policyPromise, eventsPromise])
      .then(() => {
        console.log('All initial data loaded');
      })
      .catch(error => {
        console.error('Some initial data failed to load:', error);
      });
  };

  // Setup WebSocket connection and initial data load
  useEffect(() => {
    isMountedRef.current = true;

    // Function to update state from WebSocket message
    const updateStateFromWS = (data: any) => {
      console.log('Updating state from WebSocket data:', Object.keys(data));
      if (data.fl) {
        setFlState({ data: data.fl, loading: false, error: data.fl.status === 'error' ? data.fl.error : null, lastUpdated: new Date(), refreshing: false });
      }
      if (data.network) {
        setNetworkState({ data: data.network, loading: false, error: data.network.status === 'error' ? data.network.error : null, lastUpdated: new Date(), refreshing: false });
      }
      if (data.policy) {
        setPolicyState({ data: data.policy, loading: false, error: data.policy.status === 'error' ? data.policy.error : null, lastUpdated: new Date(), refreshing: false });
      }
      if (data.events) {
        setEventsState({ data: data.events, loading: false, error: data.events.status === 'error' ? data.events.error : null, lastUpdated: new Date(), refreshing: false });
      }
    };
    
    const connectWebSocket = () => {
      // Skip WebSocket in production to avoid connection issues
      if (process.env.NODE_ENV === 'production') {
        console.log('WebSocket disabled in production, using polling only');
        return;
      }
      
      // Construct WebSocket URL (adjust if your backend serves from a different path/port in dev)
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/api/overview/ws/overview`;
      
      wsRef.current = new WebSocket(wsUrl);
      console.log('Attempting to connect WebSocket to:', wsUrl);

      wsRef.current.onopen = () => {
        console.log('WebSocket connection established for OverviewPage.');
        // Clear any reconnect timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data as string);
          console.log('WebSocket message received:', message.type, message.data ? 'with data' : 'no data');
          if (message.type === 'overview_update' && message.data) {
            if (isMountedRef.current) {
              updateStateFromWS(message.data);
            }
          } else {
            console.warn('Unexpected WebSocket message format:', message);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error, 'Raw data:', event.data);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        // Fall back to polling
        if (isMountedRef.current) {
          console.log('WebSocket error - falling back to polling');
          startPolling();
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('WebSocket connection closed for OverviewPage.', event.code, event.reason);
        wsRef.current = null;
        
        if (isMountedRef.current && !event.wasClean) { 
          console.log('WebSocket closed unexpectedly - starting polling fallback');
          startPolling();
          
          // Try to reconnect WebSocket after configurable delay
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
          console.log(`Will attempt WebSocket reconnect in ${TIMING.websocketReconnectDelay} seconds...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isMountedRef.current) {
              stopPolling();
              connectWebSocket();
            }
          }, TIMING.websocketReconnectDelay * 1000);
        }
      };
    };

    // Polling fallback mechanism
    const startPolling = () => {
      if (pollingIntervalRef.current) return; // Already polling
      
      console.log(`Starting polling fallback (every ${TIMING.pollingInterval} seconds)`);
      pollingIntervalRef.current = setInterval(async () => {
        if (isMountedRef.current) {
          try {
            console.log('Polling for updates...');
            await Promise.allSettled([
              fetchFLData(),
              fetchNetworkData(), 
              fetchPolicyData(),
              fetchEventsData()
            ]);
          } catch (error) {
            console.error('Error during polling:', error);
          }
        }
      }, TIMING.pollingInterval * 1000); // Use configurable polling interval
    };
    
    const stopPolling = () => {
      if (pollingIntervalRef.current) {
        console.log('Stopping polling');
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };

    // Immediately load any cached data
    initialLoadViaRest();
    
    // Try WebSocket first, fallback to polling
    connectWebSocket();
    
    // Always start polling as backup after 10 seconds
    const pollingBackupTimeout = setTimeout(() => {
      if (isMountedRef.current) {
        startPolling();
      }
    }, 10000);

    return () => {
      isMountedRef.current = false;
      
      clearTimeout(pollingBackupTimeout);
      stopPolling();
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        console.log('Closing WebSocket connection due to component unmount.');
        wsRef.current.close(1000, 'Component unmounted'); // 1000 is a normal closure
        wsRef.current = null;
      }
    };
  }, [fetchFLData, fetchNetworkData, fetchPolicyData, fetchEventsData]); // Dependencies for fetchers

  // Component for loading indicators
  const LoadingIndicator = ({ size = 16, refreshing = false }: { size?: number; refreshing?: boolean }) => (
    <Tooltip title={refreshing ? "Refreshing..." : "Loading..."}>
      <CircularProgress 
        size={size} 
        sx={{ 
          ml: 1,
          color: refreshing ? 'primary.main' : 'text.secondary'
        }} 
      />
    </Tooltip>
  );

  // Component for refresh button with last updated info
  const RefreshButton = ({ 
    onRefresh, 
    lastUpdated, 
    refreshing 
  }: { 
    onRefresh: () => void; 
    lastUpdated: Date | null; 
    refreshing: boolean;
  }) => (
    <Box display="flex" alignItems="center" gap={1}>
      {lastUpdated && (
        <Tooltip title={`Last updated: ${lastUpdated.toLocaleString()}`}>
          <Box display="flex" alignItems="center" sx={{ color: 'text.secondary', fontSize: '0.75rem' }}>
            <ScheduleIcon sx={{ fontSize: '0.875rem', mr: 0.5 }} />
            {lastUpdated.toLocaleTimeString()}
          </Box>
        </Tooltip>
      )}
      <Tooltip title="Refresh">
        <IconButton 
          size="small" 
          onClick={onRefresh}
          disabled={refreshing}
          sx={{ 
            color: refreshing ? 'primary.main' : 'text.secondary',
            '&:hover': { color: 'primary.main' }
          }}
        >
          <RefreshIcon sx={{ 
            fontSize: '1rem',
            animation: refreshing ? 'spin 1s linear infinite' : 'none',
            '@keyframes spin': {
              '0%': { transform: 'rotate(0deg)' },
              '100%': { transform: 'rotate(360deg)' }
            }
          }} />
        </IconButton>
      </Tooltip>
    </Box>
  );

  // Component for metric values with graceful loading
  const MetricValue = ({ 
    value, 
    loading, 
    error, 
    formatter = (v) => v?.toString() || '0',
    refreshing = false
  }: { 
    value: any; 
    loading: boolean; 
    error?: boolean;
    formatter?: (value: any) => string;
    refreshing?: boolean;
  }) => {
    if (loading && !refreshing) {
      return (
        <Box display="flex" alignItems="center">
          <Skeleton variant="text" width={60} height={40} />
          <LoadingIndicator />
        </Box>
      );
    }
    
    if (error && !value) {
      return <Typography variant="h5" color="error">--</Typography>;
    }
    
    return (
      <Box display="flex" alignItems="center">
        <Typography variant="h5">{formatter(value)}</Typography>
        {refreshing && <LoadingIndicator size={14} refreshing />}
      </Box>
    );
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          FLOPY-NET System Overview
        </Typography>
        <Tooltip title="Refresh All Data">
          <IconButton 
            onClick={refreshAll}
            disabled={flState.refreshing || networkState.refreshing || policyState.refreshing || eventsState.refreshing}
            color="primary"
            sx={{ 
              '&:hover': { backgroundColor: 'primary.light' }
            }}
          >
            <RefreshIcon sx={{ 
              fontSize: '1.5rem',
              animation: (flState.refreshing || networkState.refreshing || policyState.refreshing || eventsState.refreshing) ? 'spin 1s linear infinite' : 'none',
              '@keyframes spin': {
                '0%': { transform: 'rotate(0deg)' },
                '100%': { transform: 'rotate(360deg)' }
              }
            }} />
          </IconButton>
        </Tooltip>
      </Box>

      <Grid container spacing={3}>
        {/* Federated Learning Status */}
        <Grid item xs={12}>
          <Card 
            sx={{ 
              cursor: 'pointer',
              transition: 'transform 0.2s, box-shadow 0.2s',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: 4
              }
            }}
            onClick={() => navigate('/fl-monitoring')}
          >
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Box display="flex" alignItems="center">
                  <Typography variant="h6">Federated Learning Status</Typography>
                  {(flState.loading && !flState.data) && <LoadingIndicator />}
                </Box>
                <Box display="flex" alignItems="center" gap={2}>
                  <RefreshButton 
                    onRefresh={refreshFL}
                    lastUpdated={flState.lastUpdated}
                    refreshing={flState.refreshing}
                  />
                  {flState.loading && !flState.data ? (
                    <Skeleton variant="rectangular" width={80} height={24} />
                  ) : flState.data?.status === 'error' ? (
                    <Chip label="Error" color="error" />
                  ) : (
                    <Chip 
                      label={flDataHook.getTrainingStatusText() || (
                        flState.data?.status === 'no_data' ? 'No Data' : 
                        flState.data?.status === 'active' ? 'Training Active' : 
                        flState.data?.status === 'completed' ? 'Training Complete' :
                        flState.data?.status === 'idle' ? 'Idle' :
                        flState.data?.status === 'error' ? 'Error' :
                        'Unknown'
                      )}
                      color={flDataHook.getTrainingStatusColor() || getFLStatusColor(flState.data?.clients_connected || 0, flState.data?.accuracy || 0, flState.data?.status || 'error')} 
                    />
                  )}
                </Box>
              </Box>
              
              {flState.error && !flState.data ? (
                <Alert severity="error">{flState.error}</Alert>
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Current Round</Typography>
                    <MetricValue 
                      value={flState.data?.round} 
                      loading={flState.loading} 
                      error={!!flState.error}
                      refreshing={flState.refreshing}
                    />
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Connected Clients</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={flState.data?.clients_connected} 
                        loading={flState.loading} 
                        error={!!flState.error}
                        refreshing={flState.refreshing}
                      />
                      {!flState.loading && !flState.error && flState.data && (
                        <Chip 
                          size="small" 
                          label="●" 
                          color={flState.data.clients_connected === 0 ? 'error' : 'success'}
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Current Accuracy</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={flState.data?.accuracy} 
                        loading={flState.loading} 
                        error={!!flState.error}
                        refreshing={flState.refreshing}
                        formatter={(v) => `${v?.toFixed(2) || '0.00'}%`}
                      />
                      {!flState.loading && !flState.error && flState.data && (
                        <Chip 
                          size="small" 
                          label="↗" 
                          color={getStatusIndicator(flState.data.accuracy || 0, FL_THRESHOLDS.accuracy)} 
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Current Loss</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={flState.data?.loss} 
                        loading={flState.loading} 
                        error={!!flState.error}
                        refreshing={flState.refreshing}
                        formatter={(v) => v?.toFixed(4) || '0.0000'}
                      />
                      {!flState.loading && !flState.error && flState.data && (
                        <Chip 
                          size="small" 
                          label="↗" 
                          color={getStatusIndicator(flState.data.loss || 0, FL_THRESHOLDS.loss)} 
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Network Status */}
        <Grid item xs={12}>
          <Card
            sx={{ 
              cursor: 'pointer',
              transition: 'transform 0.2s, box-shadow 0.2s',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: 4
              }
            }}
            onClick={() => navigate('/network')}
          >
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Box display="flex" alignItems="center">
                  <Typography variant="h6">Network Status</Typography>
                  {(networkState.loading && !networkState.data) && <LoadingIndicator />}
                </Box>
                <Box display="flex" alignItems="center" gap={2}>
                  <RefreshButton 
                    onRefresh={refreshNetwork}
                    lastUpdated={networkState.lastUpdated}
                    refreshing={networkState.refreshing}
                  />
                  {networkState.loading && !networkState.data ? (
                    <Skeleton variant="rectangular" width={80} height={24} />
                  ) : networkState.data?.status === 'error' ? (
                    <Chip label="Error" color="error" />
                  ) : (
                    <Chip 
                      label={(() => {
                        const status = networkState.data?.status || 'error';
                        const nodes = networkState.data?.active_nodes || 0;
                        const packetLoss = networkState.data?.packet_loss_percent || 0;
                        
                        if (status === 'error') return 'Error';
                        if (status === 'no_data') return 'No Data';
                        if (nodes === 0) return 'No Active Nodes';
                        if (packetLoss > 5) return 'High Packet Loss';
                        if (packetLoss > 1) return 'Warning';
                        return 'Healthy';
                      })()} 
                      color={getNetworkStatusColor(networkState.data?.active_nodes || 0, networkState.data?.packet_loss_percent || 0, networkState.data?.status || 'error')} 
                    />
                  )}
                </Box>
              </Box>
              
              {networkState.error && !networkState.data ? (
                <Alert severity="error">{networkState.error}</Alert>
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Active Nodes</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={networkState.data?.active_nodes} 
                        loading={networkState.loading} 
                        error={!!networkState.error}
                        refreshing={networkState.refreshing}
                      />
                      {!networkState.loading && !networkState.error && networkState.data && (
                        <Chip 
                          size="small" 
                          label="●" 
                          color={networkState.data.active_nodes === 0 ? 'error' : 'success'}
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Active Links</Typography>
                    <MetricValue 
                      value={networkState.data?.links_count} 
                      loading={networkState.loading} 
                      error={!!networkState.error}
                      refreshing={networkState.refreshing}
                    />
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Avg. Latency</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={networkState.data?.avg_latency} 
                        loading={networkState.loading} 
                        error={!!networkState.error}
                        refreshing={networkState.refreshing}
                        formatter={(v) => `${v?.toFixed(2) || '0.00'} ms`}
                      />
                      {!networkState.loading && !networkState.error && networkState.data && (
                        <Chip 
                          size="small" 
                          label="↗" 
                          color={getStatusIndicator(networkState.data.avg_latency || 0, NETWORK_THRESHOLDS.latency)} 
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Packet Loss</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={networkState.data?.packet_loss_percent} 
                        loading={networkState.loading} 
                        error={!!networkState.error}
                        refreshing={networkState.refreshing}
                        formatter={(v) => `${v?.toFixed(2) || '0.00'}%`}
                      />
                      {!networkState.loading && !networkState.error && networkState.data && (
                        <Chip 
                          size="small" 
                          label="↗" 
                          color={getStatusIndicator(networkState.data.packet_loss_percent || 0, NETWORK_THRESHOLDS.packetLoss)} 
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* SDN Controller */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Box display="flex" alignItems="center">
                  <Typography variant="h6">SDN Controller</Typography>
                  {(networkState.loading && !networkState.data) && <LoadingIndicator />}
                </Box>
                <Box display="flex" alignItems="center" gap={2}>
                  <RefreshButton 
                    onRefresh={refreshNetwork}
                    lastUpdated={networkState.lastUpdated}
                    refreshing={networkState.refreshing}
                  />
                  {networkState.loading && !networkState.data ? (
                    <Skeleton variant="rectangular" width={80} height={24} />
                  ) : (
                    <Chip 
                      label={networkState.data?.sdn_status === 'connected' ? 'Active' : 'Unknown'} 
                      color={networkState.data?.sdn_status === 'connected' ? 'success' : 'warning'} 
                    />
                  )}
                </Box>
              </Box>
              
              <Grid container spacing={2}>
                <Grid item xs={3}>
                  <Typography variant="body2" color="textSecondary">SDN Switches</Typography>
                  <Box display="flex" alignItems="center">
                    <MetricValue 
                      value={networkState.data?.switches_count} 
                      loading={networkState.loading} 
                      error={!!networkState.error}
                      refreshing={networkState.refreshing}
                    />
                    {!networkState.loading && !networkState.error && networkState.data && (
                      <Chip 
                        size="small" 
                        label="●" 
                        color={networkState.data.switches_count === 0 ? 'error' : 'success'}
                        sx={{ ml: 1 }}
                      />
                    )}
                  </Box>
                </Grid>
                <Grid item xs={3}>
                  <Typography variant="body2" color="textSecondary">Flow Rules</Typography>
                  <MetricValue 
                    value={networkState.data?.total_flows} 
                    loading={networkState.loading} 
                    error={!!networkState.error}
                    refreshing={networkState.refreshing}
                  />
                </Grid>
                <Grid item xs={3}>
                  <Typography variant="body2" color="textSecondary">Bandwidth Usage</Typography>
                  <Box display="flex" alignItems="center">
                    <MetricValue 
                      value={networkState.data?.bandwidth_utilization} 
                      loading={networkState.loading} 
                      error={!!networkState.error}
                      refreshing={networkState.refreshing}
                      formatter={(v) => `${v?.toFixed(1) || '0.0'}%`}
                    />
                    {!networkState.loading && !networkState.error && networkState.data && (
                      <Chip 
                        size="small" 
                        label="↗" 
                        color={getStatusIndicator(networkState.data.bandwidth_utilization || 0, NETWORK_THRESHOLDS.bandwidth)} 
                        sx={{ ml: 1 }}
                      />
                    )}
                  </Box>
                </Grid>
                <Grid item xs={3}>
                  <Typography variant="body2" color="textSecondary">Nodes</Typography>
                  <Box display="flex" alignItems="center">
                    <MetricValue 
                      value={networkState.data?.nodes_count} 
                      loading={networkState.loading} 
                      error={!!networkState.error}
                      refreshing={networkState.refreshing}
                    />
                    {!networkState.loading && !networkState.error && networkState.data && (
                      <Chip 
                        size="small" 
                        label="●" 
                        color={networkState.data.nodes_count > 0 ? 'success' : 'warning'}
                        sx={{ ml: 1 }}
                      />
                    )}
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Enhanced Network Performance */}
        {networkState.data?.bandwidth && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Box display="flex" alignItems="center">
                    <Typography variant="h6">Network Performance</Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={2}>
                    {networkState.data?.health_score && (
                      <Chip 
                        label={`Health: ${networkState.data.health_score}%`}
                        color={
                          networkState.data.health_score >= 90 ? 'success' : 
                          networkState.data.health_score >= 70 ? 'warning' : 'error'
                        }
                      />
                    )}
                  </Box>
                </Box>
                
                <Grid container spacing={2}>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Current Bandwidth</Typography>
                    <MetricValue 
                      value={networkState.data?.bandwidth?.current_total_bps}
                      loading={networkState.loading} 
                      error={!!networkState.error}
                      refreshing={networkState.refreshing}
                      formatter={(v) => {
                        if (!v) return '0 bps';
                        const mbps = v / 1000000;
                        return mbps >= 1 ? `${mbps.toFixed(2)} Mbps` : `${(v / 1000).toFixed(2)} Kbps`;
                      }}
                    />
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Peak Bandwidth</Typography>
                    <MetricValue 
                      value={networkState.data?.bandwidth?.peak_bandwidth_bps}
                      loading={networkState.loading} 
                      error={!!networkState.error}
                      refreshing={networkState.refreshing}
                      formatter={(v) => {
                        if (!v) return '0 bps';
                        const mbps = v / 1000000;
                        return mbps >= 1 ? `${mbps.toFixed(2)} Mbps` : `${(v / 1000).toFixed(2)} Kbps`;
                      }}
                    />
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Data Transferred</Typography>
                    <MetricValue 
                      value={networkState.data?.totals?.bytes_transferred}
                      loading={networkState.loading} 
                      error={!!networkState.error}
                      refreshing={networkState.refreshing}
                      formatter={(v) => {
                        if (!v) return '0 B';
                        const mb = v / (1024 * 1024);
                        const gb = v / (1024 * 1024 * 1024);
                        return gb >= 1 ? `${gb.toFixed(2)} GB` : mb >= 1 ? `${mb.toFixed(2)} MB` : `${(v / 1024).toFixed(2)} KB`;
                      }}
                    />
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Uptime</Typography>
                    <MetricValue 
                      value={networkState.data?.totals?.uptime_seconds}
                      loading={networkState.loading} 
                      error={!!networkState.error}
                      refreshing={networkState.refreshing}
                      formatter={(v) => {
                        if (!v) return '0s';
                        const hours = Math.floor(v / 3600);
                        const minutes = Math.floor((v % 3600) / 60);
                        return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
                      }}
                    />
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Policy Engine */}
        <Grid item xs={12}>
          <Card
            sx={{ 
              cursor: 'pointer',
              transition: 'transform 0.2s, box-shadow 0.2s',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: 4
              }
            }}
            onClick={() => navigate('/policy')}
          >
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Box display="flex" alignItems="center">
                  <Typography variant="h6">Policy Engine</Typography>
                  {(policyState.loading && !policyState.data) && <LoadingIndicator />}
                </Box>
                <Box display="flex" alignItems="center" gap={2}>
                  <RefreshButton 
                    onRefresh={refreshPolicy}
                    lastUpdated={policyState.lastUpdated}
                    refreshing={policyState.refreshing}
                  />
                  {policyState.loading && !policyState.data ? (
                    <Skeleton variant="rectangular" width={80} height={24} />
                  ) : policyState.data?.status === 'error' ? (
                    <Chip label="Error" color="error" />
                  ) : (
                    <Chip 
                      label={policyState.data?.status === 'active' ? 'Active' : 'Error'} 
                      color={policyState.data?.status === 'active' ? 'success' : 'error'} 
                    />
                  )}
                </Box>
              </Box>
              
              {policyState.error && !policyState.data ? (
                <Alert severity="error">{policyState.error}</Alert>
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Active Policies</Typography>
                    <MetricValue 
                      value={policyState.data?.active_policies} 
                      loading={policyState.loading} 
                      error={!!policyState.error}
                      refreshing={policyState.refreshing}
                    />
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Allowed (Last Hour)</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={policyState.data?.allow_count_last_hour} 
                        loading={policyState.loading} 
                        error={!!policyState.error}
                        refreshing={policyState.refreshing}
                      />
                      {!policyState.loading && !policyState.error && policyState.data && (
                        <Chip 
                          size="small" 
                          label="●" 
                          color="success"
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Denied (Last Hour)</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={policyState.data?.deny_count_last_hour} 
                        loading={policyState.loading} 
                        error={!!policyState.error}
                        refreshing={policyState.refreshing}
                      />
                      {!policyState.loading && !policyState.error && policyState.data && (
                        <Chip 
                          size="small" 
                          label="●" 
                          color="warning"
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Avg Decision Time</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={policyState.data?.avg_decision_time_ms} 
                        loading={policyState.loading} 
                        error={!!policyState.error}
                        refreshing={policyState.refreshing}
                        formatter={(v) => {
                          if (!v || v === 0) return '0 ms';
                          return v < 1 ? '<1 ms' : v < 1000 ? `${v.toFixed(1)} ms` : `${(v/1000).toFixed(2)} s`;
                        }}
                      />
                      {!policyState.loading && !policyState.error && policyState.data && (
                        <Chip 
                          size="small" 
                          label="↗" 
                          color={getStatusIndicator(policyState.data.avg_decision_time_ms || 0, POLICY_THRESHOLDS.decisionTime)} 
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* System Events */}
        <Grid item xs={12}>
          <Card
            sx={{ 
              cursor: 'pointer',
              transition: 'transform 0.2s, box-shadow 0.2s',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: 4
              }
            }}
            onClick={() => navigate('/events')}
          >
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Typography variant="h6">System Events</Typography>
                {(eventsState.loading && !eventsState.data) && <LoadingIndicator />}
              </Box>
              
              {eventsState.error && !eventsState.data ? (
                <Alert severity="error">{eventsState.error}</Alert>
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Total Events</Typography>
                    <MetricValue 
                      value={eventsState.data?.total_count} 
                      loading={eventsState.loading} 
                      error={!!eventsState.error}
                      refreshing={eventsState.refreshing}
                    />
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Errors</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={eventsState.data?.error_count} 
                        loading={eventsState.loading} 
                        error={!!eventsState.error}
                        refreshing={eventsState.refreshing}
                      />
                      {!eventsState.loading && !eventsState.error && eventsState.data && (
                        <Chip 
                          size="small" 
                          label="●" 
                          color={eventsState.data.error_count === 0 ? 'success' : 'error'}
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Warnings</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={eventsState.data?.warning_count} 
                        loading={eventsState.loading} 
                        error={!!eventsState.error}
                        refreshing={eventsState.refreshing}
                      />
                      {!eventsState.loading && !eventsState.error && eventsState.data && (
                        <Chip 
                          size="small" 
                          label="●" 
                          color={eventsState.data.warning_count === 0 ? 'success' : 'warning'}
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                  <Grid item xs={3}>
                    <Typography variant="body2" color="textSecondary">Info</Typography>
                    <Box display="flex" alignItems="center">
                      <MetricValue 
                        value={eventsState.data?.info_count} 
                        loading={eventsState.loading} 
                        error={!!eventsState.error}
                        refreshing={eventsState.refreshing}
                      />
                      {!eventsState.loading && !eventsState.error && eventsState.data && (
                        <Chip 
                          size="small" 
                          label="●" 
                          color="info"
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Box>
                  </Grid>
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default OverviewPage; 