import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Alert,
  Button,
  CircularProgress,
  Stack
} from '@mui/material';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import {
  NetworkOverviewTab,
  NetworkTopologyTab,
  NetworkSwitchesTab,
  NetworkHostsTab,
  NetworkLinksTab,
  NetworkFlowsTab,
  NetworkMetricsTab,
  NodeDetailDialog
} from '../components/network';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`network-tabpanel-${index}`}
      aria-labelledby={`network-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `network-tab-${index}`,
    'aria-controls': `network-tabpanel-${index}`,
  };
}

const NetworkPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);  const [networkStats, setNetworkStats] = useState<any>(null);
  const [hostsList, setHostsList] = useState<any[]>([]);
  const [switchesList, setSwitchesList] = useState<any[]>([]);
  const [linksList, setLinksList] = useState<any[]>([]);
  const [flowsData, setFlowsData] = useState<any>(null);
  const [liveTopology, setLiveTopology] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);
  // Graceful data fetch function without flickering - don't clear existing data on refresh
  const fetchAllNetworkData = useCallback(async (isRefresh = false) => {
    // Only show loading state on initial load, not on refresh
    if (!isRefresh) {
      setLoading(true);
    }
    setRefreshing(isRefresh);
    
    try {      const [
        topologyResponse,
        statsResponse,
        hostsResponse,
        switchesResponse,
        linksResponse,
        flowsResponse
      ] = await Promise.all([
        fetch('/api/network/topology/live'),
        fetch('/api/network/statistics'),
        fetch('/api/network/hosts'),
        fetch('/api/network/switches'),
        fetch('/api/network/links'),
        fetch('/api/network/flows')
      ]);      // Check if responses are ok before parsing
      const responses = [topologyResponse, statsResponse, hostsResponse, switchesResponse, linksResponse, flowsResponse];
      const validResponses = responses.every(response => response.ok);
      
      if (validResponses) {        const [topology, stats, hosts, switches, links, flows] = await Promise.all([
          topologyResponse.json(),
          statsResponse.json(),
          hostsResponse.json(),
          switchesResponse.json(),
          linksResponse.json(),
          flowsResponse.json()
        ]);

        // Only update state if we have valid data - don't replace with null/undefined
        if (topology && Object.keys(topology).length > 0) {
          setLiveTopology(topology);
        }
        if (stats && Object.keys(stats).length > 0) {
          setNetworkStats(stats);
        }
        if (hosts?.hosts && Array.isArray(hosts.hosts)) {
          setHostsList(hosts.hosts);
        }
        if (switches?.switches && Array.isArray(switches.switches)) {
          setSwitchesList(switches.switches);
        }        if (links?.links && Array.isArray(links.links)) {
          setLinksList(links.links);
        }
        if (flows && Object.keys(flows).length > 0) {
          setFlowsData(flows);
        }
        
        setError(null);
      } else {
        // If refresh fails, don't show error to avoid flickering
        if (!isRefresh) {
          setError('Failed to fetch network data');
        }
      }
    } catch (err) {
      console.error('Error fetching network data:', err);
      // Only show error on initial load, not on refresh to avoid flickering
      if (!isRefresh) {
        setError('Failed to fetch network data');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Initial data fetch
  useEffect(() => {
    fetchAllNetworkData();
  }, [fetchAllNetworkData]);

  // Auto-refresh functionality - always enabled with graceful updates
  useEffect(() => {
    // Clear existing interval
    if (refreshIntervalRef.current) {
      clearInterval(refreshIntervalRef.current);
    }
    
    // Set up new interval for graceful refresh - always enabled
    refreshIntervalRef.current = setInterval(() => {
      fetchAllNetworkData(true); // Pass true to indicate this is a refresh
    }, 10000); // Refresh every 10 seconds
    
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [fetchAllNetworkData]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleRefresh = () => {
    fetchAllNetworkData(true);
  };

  if (loading) {
    return <LoadingSpinner message="Loading network topology..." />;
  }

  return (
    <Box>
      <Box mb={4}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
          Network Topology
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Monitor real-time network topology, switches, hosts, and connections
        </Typography>
      </Box>

      <Box display="flex" justifyContent="flex-end" alignItems="center" mb={3}>
        <Stack direction="row" spacing={2} alignItems="center">
          {refreshing && (
            <Box display="flex" alignItems="center" gap={1}>
              <CircularProgress size={16} />
              <Typography variant="body2" color="text.secondary">
                Updating...
              </Typography>
            </Box>
          )}
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={loading || refreshing}
          >
            Refresh
          </Button>
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ borderRadius: 2, overflow: 'hidden' }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
          variant="fullWidth"
        >          <Tab label="Overview" {...a11yProps(0)} />
          <Tab label="Metrics" {...a11yProps(1)} />
          <Tab label="Topology" {...a11yProps(2)} />
          <Tab label="Switches" {...a11yProps(3)} />
          <Tab label="Hosts" {...a11yProps(4)} />
          <Tab label="Links" {...a11yProps(5)} />
          <Tab label="Flows" {...a11yProps(6)} />
        </Tabs>        <TabPanel value={tabValue} index={0}>
          <NetworkOverviewTab 
            networkStats={networkStats}
            refreshing={refreshing}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <NetworkMetricsTab />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <NetworkTopologyTab 
            liveTopology={liveTopology}
            selectedNode={selectedNode}
            setSelectedNode={setSelectedNode}
            refreshing={refreshing}
          />
        </TabPanel>        <TabPanel value={tabValue} index={3}>
          <NetworkSwitchesTab 
            switchesList={switchesList}
            refreshing={refreshing}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={4}>
          <NetworkHostsTab 
            hostsList={hostsList}
            refreshing={refreshing}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={5}>
          <NetworkLinksTab 
            linksList={linksList}
            refreshing={refreshing}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={6}>
          <NetworkFlowsTab 
            flowsData={flowsData}
            refreshing={refreshing}
          />
        </TabPanel>
      </Paper>      {/* Node Detail Dialog */}
      <NodeDetailDialog 
        node={selectedNode} 
        open={!!selectedNode} 
        onClose={() => setSelectedNode(null)} 
      />
    </Box>
  );
};

export default NetworkPage;
