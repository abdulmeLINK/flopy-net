import { useState, useEffect, useRef } from 'react';
import { 
  Box, 
  Typography, 
  Button, 
  CircularProgress, 
  Paper, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Alert, 
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  Grid,
  Divider,
  Tabs,
  Tab,
  Accordion,
  AccordionSummary,  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Snackbar,
  Popover,
  ButtonGroup
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import StopIcon from '@mui/icons-material/Stop';
import InfoIcon from '@mui/icons-material/Info';
import RefreshIcon from '@mui/icons-material/Refresh';
import SettingsIcon from '@mui/icons-material/Settings';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import CenterFocusStrongIcon from '@mui/icons-material/CenterFocusStrong';

// Network device image utilities
import { getDeviceImage } from '../utils/networkDeviceImages';
import { 
  getScenarios, 
  startScenario, 
  stopScenario, 
  getScenarioConfig,
  getScenarioTopology,
  getScenarioLogs,
  Scenario,
  ScenarioConfig,
  ScenarioTopology,
  ScenarioLogs
} from '../services/scenariosApi';

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
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

// Interactive topology graph component
function InteractiveTopologyGraph({ topology }: { topology: any }) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [nodes, setNodes] = useState<any[]>([]);
  const [links, setLinks] = useState<any[]>([]);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });  const [isDragging, setIsDragging] = useState(false);
  const [dragNode, setDragNode] = useState<any>(null);
  const [dragOffset, setDragOffset] = useState<{ x: number, y: number }>({ x: 0, y: 0 });
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [nodeInfoAnchor, setNodeInfoAnchor] = useState<HTMLElement | null>(null);
  useEffect(() => {
    if (topology?.nodes && topology?.links) {
      // Improved layout algorithm with better spacing
      const initialNodes = topology.nodes.map((node: any, index: number) => {
        // Calculate grid position with better spacing
        const cols = Math.ceil(Math.sqrt(topology.nodes.length));
        const row = Math.floor(index / cols);
        const col = index % cols;
        
        // Improved spacing - larger gaps between nodes
        const xSpacing = 150; // Increased from 120
        const ySpacing = 120; // Increased from 100
        const offsetX = 80;   // Left margin
        const offsetY = 80;   // Top margin
        
        return {
          ...node,
          id: node.name,
          x: node.x || offsetX + col * xSpacing,
          y: node.y || offsetY + row * ySpacing,
          fx: null, // fixed x position
          fy: null  // fixed y position
        };
      });
      setNodes(initialNodes);
      setLinks(topology.links || []);
    }  }, [topology]);

  // No longer need getNodeColor or getNodeIcon functions as we'll use images directly

  const handleZoomIn = () => {
    setZoom(prev => Math.min(prev * 1.2, 3));
  };

  const handleZoomOut = () => {
    setZoom(prev => Math.max(prev / 1.2, 0.3));
  };

  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };
  const handleMouseDown = (event: React.MouseEvent, node: any) => {
    event.preventDefault();
    const rect = svgRef.current?.getBoundingClientRect();
    if (rect) {
      // Calculate the offset from mouse position to node center
      const mouseX = (event.clientX - rect.left - pan.x) / zoom;
      const mouseY = (event.clientY - rect.top - pan.y) / zoom;
      const offsetX = mouseX - node.x;
      const offsetY = mouseY - node.y;
      
      setIsDragging(true);
      setDragNode(node);
      setDragOffset({ x: offsetX, y: offsetY });
    }
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    if (isDragging && dragNode) {
      const rect = svgRef.current?.getBoundingClientRect();
      if (rect) {
        // Apply the offset to prevent jumping
        const mouseX = (event.clientX - rect.left - pan.x) / zoom;
        const mouseY = (event.clientY - rect.top - pan.y) / zoom;
        const x = mouseX - dragOffset.x;
        const y = mouseY - dragOffset.y;
        
        setNodes(prevNodes => 
          prevNodes.map(n => 
            n.id === dragNode.id ? { ...n, x, y } : n
          )
        );
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setDragNode(null);
    setDragOffset({ x: 0, y: 0 });
  };

  const handleNodeClick = (event: React.MouseEvent, node: any) => {
    event.preventDefault();
    setSelectedNode(node);
    setNodeInfoAnchor(event.currentTarget as HTMLElement);
  };  const handleWheel = (event: React.WheelEvent) => {
    // Check if Ctrl key is held down for zoom
    if (event.ctrlKey) {
      event.preventDefault();
      event.stopPropagation();  // Stop event from bubbling up to parent elements
      const delta = event.deltaY * -0.001;
      setZoom(prev => Math.max(0.3, Math.min(3, prev + delta)));
    }
    // Without Ctrl key, allow normal scrolling behavior
  };

  return (
    <Box sx={{ width: '100%', height: '600px', border: '1px solid #ddd', borderRadius: 1, position: 'relative', overflow: 'hidden' }}>      {/* Zoom Controls */}
      <Box sx={{ position: 'absolute', top: 10, right: 10, zIndex: 10 }}>
        <ButtonGroup orientation="vertical" variant="outlined" size="small">
          <Tooltip title="Zoom In (or Ctrl + Mouse Wheel)" placement="left">
            <Button onClick={handleZoomIn}><ZoomInIcon /></Button>
          </Tooltip>
          <Tooltip title="Zoom Out (or Ctrl + Mouse Wheel)" placement="left">
            <Button onClick={handleZoomOut}><ZoomOutIcon /></Button>
          </Tooltip>
          <Tooltip title="Reset View" placement="left">
            <Button onClick={handleResetView}><CenterFocusStrongIcon /></Button>
          </Tooltip>
        </ButtonGroup>
      </Box>

      {/* Zoom level indicator and help text */}
      <Box sx={{ position: 'absolute', bottom: 10, right: 10, zIndex: 10 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
          <Chip label={`${Math.round(zoom * 100)}%`} size="small" />
          <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem' }}>
            Hold Ctrl + mouse wheel to zoom
          </Typography>
        </Box>
      </Box>      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        viewBox="0 0 800 600"
        style={{ cursor: isDragging ? 'grabbing' : 'default' }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Render links first (so they appear behind nodes) */}
          {links.map((link: any, index: number) => {
            const sourceNode = nodes.find((n: any) => n.name === link.source);
            const targetNode = nodes.find((n: any) => n.name === link.target);
            
            if (!sourceNode || !targetNode) return null;
            
            return (
              <line
                key={index}
                x1={sourceNode.x}
                y1={sourceNode.y}
                x2={targetNode.x}
                y2={targetNode.y}
                stroke="#666"
                strokeWidth="2"
                strokeDasharray="none"
                opacity="0.7"
              />
            );
          })}          {/* Render nodes */}
          {nodes.map((node: any, index: number) => {
            const deviceImage = getDeviceImage(node.service_type);
            
            return (
              <g key={index}>                {/* Device image */}
                <image
                  x={node.x - 32}
                  y={node.y - 32}
                  width="64"
                  height="64"
                  href={deviceImage}
                  style={{ 
                    cursor: isDragging && dragNode?.id === node.id ? 'grabbing' : 'grab'
                  }}
                  onMouseDown={(e) => handleMouseDown(e, node)}
                  onClick={(e) => handleNodeClick(e, node)}
                  opacity="0.9"
                />
                
                {/* Node name below the image */}
                <text
                  x={node.x}
                  y={node.y + 50}
                  textAnchor="middle"
                  fontSize="11"
                  fill="#333"
                  fontWeight="bold"
                  pointerEvents="none"
                >
                  {node.name}
                </text>
                
                {/* IP Address below the name */}
                <text
                  x={node.x}
                  y={node.y + 65}
                  textAnchor="middle"
                  fontSize="9"
                  fill="#666"
                  pointerEvents="none"
                >
                  {node.ip_address ? `IP: ${node.ip_address}` : 'No IP'}
                </text>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Node Info Popover */}
      <Popover
        open={Boolean(nodeInfoAnchor && selectedNode)}
        anchorEl={nodeInfoAnchor}
        onClose={() => {
          setNodeInfoAnchor(null);
          setSelectedNode(null);
        }}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'left',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'left',
        }}
      >
        {selectedNode && (
          <Box sx={{ p: 2, maxWidth: 400, maxHeight: 500, overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              {selectedNode.name}
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              Service: {selectedNode.service_type}
            </Typography>
            <Typography variant="body2" color="textSecondary" gutterBottom>
              IP: {selectedNode.ip_address}
            </Typography>
            {selectedNode.ports && (
              <Typography variant="body2" color="textSecondary" gutterBottom>
                Ports: {selectedNode.ports.join(', ')}
              </Typography>
            )}
            
            {selectedNode.environment && (
              <>
                <Divider sx={{ my: 1 }} />
                <Typography variant="subtitle2" gutterBottom>
                  Environment Variables:
                </Typography>
                <Box sx={{ maxHeight: 300, overflow: 'auto' }}>
                  {Object.entries(selectedNode.environment).map(([key, value]) => (
                    <Box key={key} sx={{ mb: 0.5 }}>
                      <Typography variant="caption" fontWeight="bold">
                        {key}:
                      </Typography>
                      <Typography variant="caption" sx={{ ml: 1, wordBreak: 'break-all' }}>
                        {String(value)}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              </>
            )}
          </Box>
        )}
      </Popover>
    </Box>
  );
}

const ScenariosPage = () => {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);
  const [openDialog, setOpenDialog] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<{ [key: string]: boolean }>({});
  const [mounted, setMounted] = useState(true);
  const [tabValue, setTabValue] = useState(0);
  const [scenarioConfig, setScenarioConfig] = useState<ScenarioConfig | null>(null);
  const [scenarioTopology, setScenarioTopology] = useState<ScenarioTopology | null>(null);
  const [scenarioLogs, setScenarioLogs] = useState<ScenarioLogs | null>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [topologyLoading, setTopologyLoading] = useState(false);
  const [logsLoading, setLogsLoading] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error' | 'info' | 'warning'>('info');

  const fetchScenarios = async () => {
    if (!error) {
      setLoading(true);
    }
    
    try {
      const data = await getScenarios();
      
      if (data && data.length > 0) {
        setScenarios(data);
        setError(null);
      } else if (data && data.length === 0) {
        setScenarios([]);
        setError('No scenarios are currently available. You may need to create one or check the server connection.');
        console.warn('No scenarios were returned from the API');
      }
      
      setLoading(false);
    } catch (err: any) {
      if (!mounted) return;
        
      const isNetworkError = err.message?.includes('Network Error') || err.message?.includes('Failed to fetch');
      const isCorsError = err.message?.includes('CORS') || err.message?.includes('Cross-Origin');
      
      let errorMessage = 'Failed to load scenarios. Please try again later.';
      
      if (isCorsError) {
        errorMessage = 'Cross-origin request error: The scenarios API endpoint may not allow requests from this origin. Please check the server CORS configuration.';
      } else if (isNetworkError) {
        errorMessage = 'Network error: Could not connect to the scenarios API. The service may be temporarily unavailable.';
      } else if (err.message?.includes('API is currently unavailable')) {
        errorMessage = 'The API is currently unavailable. The system will retry automatically in 30 seconds.';
      }
      
      setError(errorMessage);
      
      if (!isNetworkError) {
        console.error('Error fetching scenarios:', err);
      }
      
      setLoading(false);
    }
  };

  useEffect(() => {
    setMounted(true);
    fetchScenarios();
    
    let pollingInterval = 10000;
    const maxPollingInterval = 60000;
    
    const intervalId = setInterval(() => {
      if (error) {
        pollingInterval = Math.min(pollingInterval * 1.5, maxPollingInterval);
      } else {
        pollingInterval = 10000;
      }
      
      if (mounted) {
        fetchScenarios();
      }
    }, pollingInterval);
    
    return () => {
      setMounted(false);
      clearInterval(intervalId);
    };
  }, []);

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'info' | 'warning' = 'info') => {
    setSnackbarMessage(message);
    setSnackbarSeverity(severity);
    setSnackbarOpen(true);
  };

  const handleStartScenario = async (scenarioId: string) => {
    setActionLoading(prev => ({ ...prev, [scenarioId]: true }));
    try {
      const result = await startScenario(scenarioId);
      if (mounted) {
        if (result.status === 'started') {
          showSnackbar(`Scenario '${scenarioId}' started successfully!`, 'success');
        } else if (result.status === 'already_running') {
          showSnackbar(`Scenario '${scenarioId}' is already running`, 'info');
        } else {
          showSnackbar(result.message || 'Scenario start initiated', 'info');
        }
        fetchScenarios();
      }
    } catch (err: any) {
      if (mounted) {
        const errorMsg = err.message?.includes('API is currently unavailable') 
          ? 'The API is currently unavailable. Please try again later.'
          : `Failed to start scenario: ${err.message || 'Unknown error'}`;
        showSnackbar(errorMsg, 'error');
        setError(errorMsg);
      }
    } finally {
      if (mounted) {
        setActionLoading(prev => ({ ...prev, [scenarioId]: false }));
      }
    }
  };
  const handleStopScenario = async (scenarioId: string) => {
    setActionLoading(prev => ({ ...prev, [scenarioId]: true }));
    try {
      await stopScenario(scenarioId);
      if (mounted) {
        showSnackbar(`Scenario '${scenarioId}' stopped successfully!`, 'success');
        fetchScenarios();
      }
    } catch (err: any) {
      if (mounted) {
        const errorMsg = err.message?.includes('API is currently unavailable') 
          ? 'The API is currently unavailable. Please try again later.'
          : `Failed to stop scenario: ${err.message || 'Unknown error'}`;
        showSnackbar(errorMsg, 'error');
        setError(errorMsg);
      }
    } finally {
      if (mounted) {
        setActionLoading(prev => ({ ...prev, [scenarioId]: false }));
      }
    }
  };

  const handleViewDetails = async (scenario: Scenario) => {
    setSelectedScenario(scenario);
    setOpenDialog(true);
    setTabValue(0);
    
    const scenarioId = scenario.id || scenario.name;
    
    // Load configuration if available
    if (scenario.has_config) {
      setConfigLoading(true);
      try {
        const config = await getScenarioConfig(scenarioId);
        setScenarioConfig(config);
      } catch (err) {
        console.error('Failed to load scenario config:', err);
        setScenarioConfig(null);
      } finally {
        setConfigLoading(false);
      }
    }
    
    // Load topology if available
    if (scenario.has_topology) {
      setTopologyLoading(true);
      try {
        const topology = await getScenarioTopology(scenarioId);
        setScenarioTopology(topology);
      } catch (err) {
        console.error('Failed to load scenario topology:', err);
        setScenarioTopology(null);
      } finally {
        setTopologyLoading(false);
      }
    }

    // Load logs
    setLogsLoading(true);
    try {
      const logs = await getScenarioLogs(scenarioId, 200);
      setScenarioLogs(logs);
    } catch (err) {
      console.error('Failed to load scenario logs:', err);
      setScenarioLogs(null);
    } finally {
      setLogsLoading(false);
    }
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
    setScenarioConfig(null);
    setScenarioTopology(null);
    setScenarioLogs(null);
  };
  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const renderStatusChip = (status: string) => {
    let color:
      | 'default'
      | 'primary'
      | 'secondary'
      | 'error'
      | 'info'
      | 'success'
      | 'warning' = 'default';
    
    let displayText = status;
    
    switch (status) {
      case 'idle':
        color = 'default';
        break;
      case 'starting':
        color = 'warning';
        break;
      case 'running':
        // Check if the scenario has a message about topology still running
        if (selectedScenario?.message?.includes('Topology is still running')) {
          color = 'success';
          displayText = 'running (topology active)';
        } else {
          color = 'primary';
        }
        break;
      case 'stopping':
        color = 'info';
        break;
      case 'completed':
        color = 'success';
        break;
      case 'failed':
      case 'error':
        color = 'error';
        break;
      default:
        color = 'default';
    }
      return <Chip label={displayText} color={color} size="small" />;
  };

  const renderConfigurationView = (config: any) => {
    if (!config) {
      return <Typography variant="body2">No configuration data available</Typography>;
    }

    const renderConfigSection = (title: string, data: any) => (
      <Accordion key={title}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="subtitle1">{title}</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box component="pre" sx={{ 
            whiteSpace: 'pre-wrap', 
            wordWrap: 'break-word',
            fontSize: '0.875rem',
            backgroundColor: 'grey.100',
            p: 2,
            borderRadius: 1,
            overflow: 'auto',
            maxHeight: 300
          }}>
            {JSON.stringify(data, null, 2)}
          </Box>
        </AccordionDetails>
      </Accordion>
    );

    return (
      <Box>
        <Typography variant="h6" gutterBottom>Configuration</Typography>
        {Object.entries(config).map(([key, value]) => 
          renderConfigSection(key.charAt(0).toUpperCase() + key.slice(1), value)
        )}
      </Box>
    );
  };

  const renderTopologyLinks = () => {
    if (!scenarioTopology?.topology?.links) return <Typography>No links defined</Typography>;
    
    const links = scenarioTopology.topology.links;
    const nodes = scenarioTopology.topology.nodes || [];
    
    return (
      <TableContainer component={Paper} sx={{ mt: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell><strong>Source</strong></TableCell>
              <TableCell><strong>Target</strong></TableCell>
              <TableCell><strong>Connection Type</strong></TableCell>
                             <TableCell><strong>Source Adapter</strong></TableCell>
               <TableCell><strong>Target Adapter</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {links.map((link: any, index: number) => {
              const sourceNode = nodes.find((n: any) => n.name === link.source);
              const targetNode = nodes.find((n: any) => n.name === link.target);
              
              return (
                <TableRow key={index}>
                  <TableCell>
                    {link.source}
                    {sourceNode && (
                      <Typography variant="caption" color="textSecondary" display="block">
                        {sourceNode.service_type} ({sourceNode.ip_address})
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {link.target}
                    {targetNode && (
                      <Typography variant="caption" color="textSecondary" display="block">
                        {targetNode.service_type} ({targetNode.ip_address})
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={link.type || 'Ethernet'} 
                      size="small" 
                      color="primary"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>{link.source_adapter || 0}</TableCell>
                  <TableCell>{link.target_adapter || 0}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  return (
    <Box>
      <Box 
        sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          mb: 3 
        }}
      >
        <Typography variant="h4">
          Scenario Management
        </Typography>
        <Button 
          startIcon={<RefreshIcon />} 
          onClick={fetchScenarios}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box 
          sx={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            height: '200px' 
          }}
        >
          <CircularProgress />
        </Box>
      ) : scenarios.length === 0 ? (
        <Card>
          <CardContent>
            <Typography variant="body1" color="text.secondary" align="center">
              No scenarios available. Scenarios might need to be created or imported.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Started At</TableCell>
                <TableCell>Configuration</TableCell>
                <TableCell>Topology</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {scenarios.map((scenario) => (
                <TableRow key={scenario.id || scenario.name}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {scenario.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {scenario.description}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {renderStatusChip(scenario.status)}
                    {scenario.message?.includes('Topology is still running') && (
                      <Typography variant="caption" sx={{ display: 'block', mt: 0.5 }}>
                        Topology active
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {scenario.started_at ? new Date(scenario.started_at).toLocaleString() : '-'}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      {scenario.has_config === true && (
                        <Tooltip title="Has Configuration">
                          <SettingsIcon color="primary" fontSize="small" />
                        </Tooltip>
                      )}
                      {scenario.has_topology === true && (
                        <Tooltip title="Has Topology">
                          <AccountTreeIcon color="secondary" fontSize="small" />
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      {scenario.has_topology === true && (
                        <Tooltip title="View Topology">
                          <IconButton 
                            color="primary"
                            onClick={() => handleViewDetails(scenario)}
                          >
                            <InfoIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      {(scenario.status === 'idle' || scenario.status === 'error' || scenario.status === 'failed' || scenario.status === 'completed') ? (
                        <Tooltip title="Start Scenario">
                          <IconButton 
                            color="success" 
                            onClick={() => handleStartScenario(scenario.id || scenario.name)}
                            disabled={actionLoading[scenario.id || scenario.name]}
                          >
                            {actionLoading[scenario.id || scenario.name] ? <CircularProgress size={24} /> : <PlayArrowIcon />}
                          </IconButton>
                        </Tooltip>
                      ) : scenario.status === 'running' ? (
                        <Tooltip title="Stop Scenario">
                          <IconButton 
                            color="error" 
                            onClick={() => handleStopScenario(scenario.id || scenario.name)}
                            disabled={actionLoading[scenario.id || scenario.name]}
                          >
                            {actionLoading[scenario.id || scenario.name] ? <CircularProgress size={24} /> : <StopIcon />}
                          </IconButton>
                        </Tooltip>
                      ) : (
                        <Tooltip title="Action in progress">
                          <span>
                            <IconButton disabled>
                              <CircularProgress size={24} />
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Scenario Details Dialog */}
      <Dialog 
        open={openDialog} 
        onClose={handleCloseDialog}
        maxWidth="lg"
        fullWidth
      >
        {selectedScenario && (
          <>
            <DialogTitle>
              Scenario Details: {selectedScenario.name}
            </DialogTitle>
            <DialogContent dividers>
              <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                <Tabs value={tabValue} onChange={handleTabChange}>
                  <Tab label="Overview" />
                  {selectedScenario.has_config && <Tab label="Configuration" />}
                  {selectedScenario.has_topology && <Tab label="Topology" />}
                  <Tab label="Logs" />
                </Tabs>
              </Box>
              
              <TabPanel value={tabValue} index={0}>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <Typography variant="subtitle1">Description</Typography>
                    <Typography variant="body2">{selectedScenario.description}</Typography>
                  </Grid>
                  
                  <Grid item xs={12}>
                    <Divider sx={{ my: 1 }} />
                  </Grid>
                  
                  <Grid item xs={6}>
                    <Typography variant="subtitle2">Status</Typography>
                    <Box sx={{ mt: 1 }}>
                      {renderStatusChip(selectedScenario.status || 'idle')}
                    </Box>
                    {selectedScenario.message && (
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                        {selectedScenario.message}
                      </Typography>
                    )}
                  </Grid>
                  
                  <Grid item xs={6}>
                    <Typography variant="subtitle2">Started At</Typography>
                    <Typography variant="body2">
                      {selectedScenario.started_at ? new Date(selectedScenario.started_at).toLocaleString() : 'Not started'}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={12}>
                    <Typography variant="subtitle2">Available Resources</Typography>
                    <List dense>
                      <ListItem>
                        <ListItemIcon>
                          {selectedScenario.has_config ? <CheckCircleIcon color="success" /> : <ErrorIcon color="error" />}
                        </ListItemIcon>
                        <ListItemText primary="Configuration File" />
                      </ListItem>
                      <ListItem>
                        <ListItemIcon>
                          {selectedScenario.has_topology ? <CheckCircleIcon color="success" /> : <ErrorIcon color="error" />}
                        </ListItemIcon>
                        <ListItemText primary="Topology File" />
                      </ListItem>
                    </List>
                  </Grid>
                </Grid>
              </TabPanel>
              
              {selectedScenario.has_config && (
                <TabPanel value={tabValue} index={selectedScenario.has_topology ? 1 : 1}>
                  {configLoading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                      <CircularProgress />
                    </Box>
                  ) : scenarioConfig ? (
                    renderConfigurationView(scenarioConfig.config)
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Failed to load configuration
                    </Typography>
                  )}
                </TabPanel>
              )}
              
              {selectedScenario.has_topology && (
                <TabPanel value={tabValue} index={selectedScenario.has_config ? 2 : 1}>
                  {topologyLoading ? (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                      <CircularProgress />
                    </Box>
                  ) : scenarioTopology ? (
                    <Box>
                      <Typography variant="h6" gutterBottom>Network Topology</Typography>
                      <Typography variant="body2" color="textSecondary" gutterBottom>
                        File: {scenarioTopology.topology_file}
                      </Typography>
                      
                      {/* Visual Graph */}
                      <Accordion defaultExpanded>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="h6">Topology Visualization</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <InteractiveTopologyGraph topology={scenarioTopology.topology} />
                        </AccordionDetails>
                      </Accordion>

                      {/* Nodes Table */}
                      <Accordion>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="h6">Network Nodes</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <TableContainer component={Paper}>
                            <Table size="small">
                              <TableHead>
                                <TableRow>
                                  <TableCell>Name</TableCell>
                                  <TableCell>Service</TableCell>
                                  <TableCell>IP Address</TableCell>
                                  <TableCell>Ports</TableCell>
                                </TableRow>
                              </TableHead>
                              <TableBody>
                                {scenarioTopology.topology.nodes?.map((node: any, index: number) => (
                                  <TableRow key={index}>
                                    <TableCell>{node.name}</TableCell>
                                    <TableCell>
                                      <Chip 
                                        label={node.service_type} 
                                        size="small" 
                                        color="primary"
                                        variant="outlined"
                                      />
                                    </TableCell>
                                    <TableCell>{node.ip_address}</TableCell>
                                    <TableCell>{node.ports?.join(', ') || 'N/A'}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableContainer>
                        </AccordionDetails>
                      </Accordion>

                      {/* Links Table */}
                      <Accordion>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="h6">Network Links</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          {renderTopologyLinks()}
                        </AccordionDetails>
                      </Accordion>
                      
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      Failed to load topology
                    </Typography>
                  )}
                </TabPanel>
              )}
              
              {/* Logs Tab */}
              <TabPanel value={tabValue} index={
                (selectedScenario.has_config ? 1 : 0) + 
                (selectedScenario.has_topology ? 1 : 0) + 1
              }>
                {logsLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : scenarioLogs ? (
                  <Box>
                                         <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                       <Typography variant="h6">Scenario Logs</Typography>
                       <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                         <Chip 
                           label={`${scenarioLogs.logs.length} lines`} 
                           size="small" 
                           color="primary"
                           variant="outlined"
                         />
                         <Button
                           size="small"
                           variant="outlined"
                           startIcon={<RefreshIcon />}
                           onClick={async () => {
                             setLogsLoading(true);
                             try {
                               const logs = await getScenarioLogs(selectedScenario.id, 200);
                               setScenarioLogs(logs);
                             } catch (err) {
                               console.error('Failed to refresh logs:', err);
                             } finally {
                               setLogsLoading(false);
                             }
                           }}
                         >
                           Refresh
                         </Button>
                       </Box>
                     </Box>
                    {scenarioLogs.logs.length > 0 ? (
                      <Paper 
                        sx={{ 
                          p: 2, 
                          bgcolor: '#f5f5f5', 
                          maxHeight: 500, 
                          overflow: 'auto',
                          border: '1px solid #ddd'
                        }}
                      >
                        <Box component="pre" sx={{ 
                          margin: 0, 
                          fontSize: '0.75rem',
                          fontFamily: 'monospace',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word'
                        }}>
                          {scenarioLogs.logs.join('\n')}
                        </Box>
                      </Paper>
                    ) : (
                      <Alert severity="info">
                        {scenarioLogs.message || 'No logs available for this scenario yet.'}
                      </Alert>
                    )}
                    {selectedScenario.status === 'running' && (
                      <Alert severity="info" sx={{ mt: 2 }}>
                        Scenario is currently running. Logs are being captured in real-time.
                      </Alert>
                    )}
                  </Box>
                ) : (
                  <Alert severity="warning">
                    Failed to load scenario logs
                  </Alert>
                )}
              </TabPanel>
            </DialogContent>
            <DialogActions>
              <Button onClick={handleCloseDialog}>Close</Button>
              {selectedScenario.status === 'idle' || selectedScenario.status === 'error' || selectedScenario.status === 'failed' || selectedScenario.status === 'completed' ? (
                <Button 
                  variant="contained" 
                  color="success"
                  startIcon={<PlayArrowIcon />}
                  onClick={() => {
                    handleStartScenario(selectedScenario.id || selectedScenario.name);
                    handleCloseDialog();
                  }}
                  disabled={actionLoading[selectedScenario.id || selectedScenario.name]}
                >
                  Start Scenario
                </Button>
              ) : selectedScenario.status === 'running' ? (
                <Button 
                  variant="contained" 
                  color="error"
                  startIcon={<StopIcon />}
                  onClick={() => {
                    handleStopScenario(selectedScenario.id || selectedScenario.name);
                    handleCloseDialog();
                  }}
                  disabled={actionLoading[selectedScenario.id || selectedScenario.name]}
                >
                  Stop Scenario
                </Button>
              ) : null}
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={() => setSnackbarOpen(false)}
      >
        <Alert 
          onClose={() => setSnackbarOpen(false)} 
          severity={snackbarSeverity}
          sx={{ width: '100%' }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ScenariosPage;