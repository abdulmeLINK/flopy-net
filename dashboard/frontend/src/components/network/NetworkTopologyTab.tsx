import React, { useState, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Stack,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material';
import { 
  NetworkCheck as NetworkCheckIcon,
  ExpandMore as ExpandMoreIcon,
  Info as InfoIcon,
  Storage as StorageIcon,
  Router as RouterIcon,
  Computer as ComputerIcon,
  Cloud as CloudIcon,
  Security as SecurityIcon
} from '@mui/icons-material';
import { getDeviceImage } from '../../utils/networkDeviceImages';

interface NetworkTopologyTabProps {
  liveTopology: any;
  selectedNode: any;
  setSelectedNode: (node: any) => void;
  refreshing?: boolean;
}

// Enhanced tooltip component with data source information
const DataSourceTooltip: React.FC<{
  children: React.ReactElement;
  title: string;
  dataSource: 'real' | 'mock' | 'generated' | 'collector' | 'gns3' | 'sdn';
  description: string;
  lastUpdated?: string;
  additionalInfo?: string;
}> = ({ children, title, dataSource, description, lastUpdated, additionalInfo }) => {
  const getSourceColor = (source: string) => {
    switch (source) {
      case 'real': return '#4caf50';
      case 'collector': return '#2196f3';
      case 'gns3': return '#ff9800';
      case 'sdn': return '#9c27b0';
      case 'mock': return '#f44336';
      case 'generated': return '#ff5722';
      default: return '#757575';
    }
  };

  const getSourceLabel = (source: string) => {
    switch (source) {
      case 'real': return 'Real Data';
      case 'collector': return 'Collector Service';
      case 'gns3': return 'GNS3 Network';
      case 'sdn': return 'SDN Controller';
      case 'mock': return 'Mock Data';
      case 'generated': return 'Generated Data';
      default: return 'Unknown Source';
    }
  };

  const tooltipContent = (
    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        {title}
      </Typography>
      <Chip 
        label={getSourceLabel(dataSource)}
        size="small"
        sx={{ 
          bgcolor: getSourceColor(dataSource),
          color: 'white',
          mb: 1,
          fontSize: '0.75rem'
        }}
      />
      <Typography variant="body2" sx={{ mb: 1 }}>
        {description}
      </Typography>
      {lastUpdated && (
        <Typography variant="caption" color="text.secondary">
          Last Updated: {lastUpdated}
        </Typography>
      )}
      {additionalInfo && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
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

export const NetworkTopologyTab: React.FC<NetworkTopologyTabProps> = ({
  liveTopology,
  setSelectedNode,
  refreshing = false
}) => {
  // State for interactive features
  const [nodePositions, setNodePositions] = useState<{[key: string]: {x: number, y: number}}>({});
  const [isDragging, setIsDragging] = useState(false);
  const [draggedNode, setDraggedNode] = useState<any>(null);
  const [zoom, setZoom] = useState(1);
  const svgRef = useRef<SVGSVGElement>(null);

  // Function to determine data source based on topology structure
  const getDataSource = (topologyData: any): 'real' | 'mock' | 'generated' | 'collector' | 'gns3' | 'sdn' => {
    if (!topologyData) return 'mock';
    if (topologyData.source === 'live_query') return 'real';
    if (topologyData.collection_time) return 'collector';
    if (topologyData.project_info) return 'gns3';
    if (topologyData.switches && topologyData.switches.length > 0) return 'sdn';
    return 'generated';
  };
  const renderTopology = () => {
    // Handle both direct topology data and nested topology data from collector
    const topologyData = liveTopology?.topology || liveTopology || {};
    const nodes = topologyData.nodes || [];
    const switchesData = topologyData.switches || [];
    const hostsData = topologyData.hosts || [];
    const dataSource = getDataSource(topologyData);
    
    // Combine all nodes into a unified array for rendering
    const allNodes = [...nodes];
    
    // Add switches as nodes if they're not already in nodes array
    switchesData.forEach((switchNode: any) => {
      if (!allNodes.find(n => n.id === switchNode.id || n.dpid === switchNode.dpid)) {
        allNodes.push({
          ...switchNode,
          id: switchNode.id || switchNode.dpid,
          type: 'switch',
          service_type: 'switch'
        });
      }
    });
    
    // Add hosts as nodes if they're not already in nodes array
    hostsData.forEach((hostNode: any) => {
      if (!allNodes.find(n => n.id === hostNode.id || n.mac === hostNode.mac)) {
        allNodes.push({
          ...hostNode,
          id: hostNode.id || hostNode.mac,
          type: 'host',
          service_type: hostNode.service_type || 'host'
        });
      }
    });
    
    // If we have no data and not refreshing, show enhanced no data message
    if (allNodes.length === 0 && !refreshing) {
      return (
        <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" height={300}>
          <Alert severity="info" sx={{ mb: 2, maxWidth: 600 }}>
            <Typography variant="body1" sx={{ fontWeight: 600, mb: 1 }}>
              No network topology data available
            </Typography>
            <Typography variant="body2" color="text.secondary">
              This could mean:
            </Typography>
            <Box component="ul" sx={{ mt: 1, mb: 0, pl: 2 }}>
              <Typography component="li" variant="body2" color="text.secondary">
                GNS3 network simulator is not running or not connected
              </Typography>
              <Typography component="li" variant="body2" color="text.secondary">
                SDN controller is offline or not responding
              </Typography>
              <Typography component="li" variant="body2" color="text.secondary">
                Collector service is unavailable or not configured
              </Typography>
              <Typography component="li" variant="body2" color="text.secondary">
                Network monitoring services are not active
              </Typography>
            </Box>
          </Alert>
        </Box>
      );
    }
    
    // If we're refreshing but have no previous data, show loading with context
    if (allNodes.length === 0 && refreshing) {
      return (
        <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" height={300}>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 1, fontWeight: 600 }}>
            Loading network topology data...
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2, textAlign: 'center', maxWidth: 400 }}>
            Fetching real-time data from collector service, GNS3 network simulator, and SDN controller
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Data sources being queried:
            </Typography>
            <Chip label="Collector" size="small" variant="outlined" />
            <Chip label="GNS3" size="small" variant="outlined" />
            <Chip label="SDN Controller" size="small" variant="outlined" />
          </Box>
        </Box>
      );
    }

    // Layout dimensions
    const width = 1400;
    const height = 800;
    const centerX = width / 2;
    const centerY = height / 2;
    
    console.log('All nodes:', allNodes);
    
    // Classify node types for better visualization using the unified nodes array
    const switches = allNodes.filter((n: any) => 
      n.type === 'switch' || 
      n.service_type === 'switch' || 
      n.service_type === 'openvswitch' ||
      n.template_name === 'OpenVSwitch' ||
      n.template_name === 'Ethernet switch' ||
      switchesData.some((s: any) => s.id === n.id || s.dpid === n.id)
    );
    const hosts = allNodes.filter((n: any) => 
      n.type === 'host' || 
      n.service_type === 'host' ||
      n.service_type === 'fl-client' ||
      n.service_type === 'fl-server' ||
      n.service_type === 'policy-engine' ||
      n.service_type === 'collector' ||
      n.service_type === 'sdn-controller' ||
      hostsData.some((h: any) => h.id === n.id || h.mac === n.id)
    );
    const others = allNodes.filter((n: any) => 
      !switches.some((s: any) => s.id === n.id) && 
      !hosts.some((h: any) => h.id === n.id)
    );

    // Simple star positioning logic
    const positionedNodes: any[] = [];
    
    allNodes.forEach((node: any, nodeIndex: number) => {
      const nodeKey = node.id || node.name;
      const customPos = nodePositions[nodeKey];
      
      let x, y;
      if (customPos) {
        // Use custom dragged position
        x = customPos.x;
        y = customPos.y;
      } else if (node.x !== undefined && node.y !== undefined) {
        // Use predefined coordinates from config
        x = node.x;
        y = node.y;
      } else {
        // Simple circle arrangement for debugging
        if (nodeIndex === 0) {
          // First node is center
          x = centerX;
          y = centerY;
        } else {
          // Other nodes in a circle around center
          const radius = 250;
          const angle = (2 * Math.PI * (nodeIndex - 1)) / Math.max(1, allNodes.length - 1);
          x = centerX + radius * Math.cos(angle);
          y = centerY + radius * Math.sin(angle);
        }
        
        console.log(`Node ${nodeIndex} (${node.id || node.name}) positioned at (${x}, ${y})`);
      }
      
      positionedNodes.push({
        ...node,
        x,
        y,
        isCenterNode: nodeIndex === 0 // Mark first node as center
      });
    });

    // Mouse event handlers for dragging
    const handleMouseDown = (event: React.MouseEvent, node: any) => {
      event.preventDefault();
      setIsDragging(true);
      setDraggedNode(node);
    };

    const handleMouseMove = (event: React.MouseEvent) => {
      if (isDragging && draggedNode && svgRef.current) {
        const rect = svgRef.current.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width) * width;
        const y = ((event.clientY - rect.top) / rect.height) * height;
        
        const nodeKey = draggedNode.id || draggedNode.name;
        setNodePositions(prev => ({
          ...prev,
          [nodeKey]: { x, y }
        }));
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setDraggedNode(null);
    };

    // Zoom handlers
    const handleWheel = (event: React.WheelEvent) => {
      if (event.ctrlKey) {
        event.preventDefault();
        event.stopPropagation();
        const delta = event.deltaY * -0.001;
        setZoom(prev => Math.max(0.3, Math.min(3, prev + delta)));
      }
    };

    const handleZoomIn = () => {
      setZoom(prev => Math.min(3, prev + 0.2));
    };

    const handleZoomOut = () => {
      setZoom(prev => Math.max(0.3, prev - 0.2));
    };    const handleZoomReset = () => {
      setZoom(1);
    };

    const getNodeTooltipInfo = (node: any) => {
      const nodeType = node.service_type || node.type || 'unknown';
      let description = '';
      let additionalInfo = '';

      switch (nodeType) {
        case 'switch':
        case 'openvswitch':
          description = 'OpenFlow switch that forwards packets based on flow rules from SDN controller';
          additionalInfo = `DPID: ${node.dpid || 'N/A'} | Ports: ${node.ports?.length || 'N/A'}`;
          break;
        case 'fl-client':
          description = 'Federated Learning client node participating in distributed training';
          additionalInfo = `Status: ${node.status || 'Unknown'} | Trust Score: ${node.trust_score || 'N/A'}`;
          break;
        case 'fl-server':
          description = 'Federated Learning server orchestrating the training process';
          additionalInfo = `Active Clients: ${node.active_clients || 'N/A'} | Current Round: ${node.current_round || 'N/A'}`;
          break;
        case 'policy-engine':
          description = 'Policy Engine that makes dynamic decisions for network and FL optimization';
          additionalInfo = `Active Policies: ${node.active_policies || 'N/A'} | Decisions/min: ${node.decisions_per_min || 'N/A'}`;
          break;
        case 'collector':
          description = 'Data collector service gathering metrics from all system components';
          additionalInfo = `Metrics Collected: ${node.metrics_count || 'N/A'} | Uptime: ${node.uptime || 'N/A'}`;
          break;
        case 'sdn-controller':
          description = 'SDN Controller managing network flow rules and topology';
          additionalInfo = `Connected Switches: ${node.switches_count || 'N/A'} | Total Flows: ${node.flows_count || 'N/A'}`;
          break;
        case 'host':
          description = 'Network host or endpoint device';
          additionalInfo = `IP: ${node.ip || node.ipv4?.[0] || 'N/A'} | MAC: ${node.mac || 'N/A'}`;
          break;
        case 'cloud':
          description = 'Cloud connection or external network gateway';
          additionalInfo = `Connection: ${node.status || 'Unknown'} | External Access: ${node.external_access ? 'Yes' : 'No'}`;
          break;
        default:
          description = 'Network device or service component';
          additionalInfo = `Type: ${nodeType} | Status: ${node.status || 'Unknown'}`;
      }

      return { description, additionalInfo };
    };
    
    return (
      <Box>
        {/* Enhanced Header with Data Source Information */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Box>
            <Typography variant="h5" component="h2" gutterBottom sx={{ fontWeight: 600 }}>
              Interactive Network Topology (Star Layout)
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              Real-time visualization with center node and surrounding nodes
            </Typography>
          </Box>
          <Stack direction="row" spacing={1}>
            <DataSourceTooltip
              title="Node Count"
              dataSource={dataSource}
              description={`Total number of network nodes detected in the topology. Data source: ${dataSource}`}
              lastUpdated={liveTopology?.timestamp ? new Date(liveTopology.timestamp * 1000).toLocaleTimeString() : 'Never'}
              additionalInfo={dataSource === 'mock' ? 'This is sample data for demonstration' : 'Live data from network monitoring'}
            >
              <Chip 
                icon={<NetworkCheckIcon />}
                label={`${allNodes.length} nodes`} 
                size="small" 
                color="info"
              />
            </DataSourceTooltip>
            <DataSourceTooltip
              title="Data Freshness"
              dataSource={dataSource}
              description="Indicates when the topology data was last updated from the network"
              lastUpdated={liveTopology?.timestamp ? new Date(liveTopology.timestamp * 1000).toLocaleTimeString() : 'Never'}
              additionalInfo={refreshing ? 'Currently updating...' : 'Data refresh interval: 30 seconds'}
            >
              <Chip 
                label={refreshing ? 'Updating...' : `Updated: ${liveTopology?.timestamp ? new Date(liveTopology.timestamp * 1000).toLocaleTimeString() : 'Never'}`} 
                size="small" 
                variant="outlined"
                color={refreshing ? "primary" : "default"}
              />
            </DataSourceTooltip>
          </Stack>
        </Box>

        {/* Data Source Information Panel */}
        <Accordion sx={{ mb: 3 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center" gap={1}>
              <InfoIcon color="primary" />
              <Typography variant="h6">Network Topology Data Information</Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Data Sources
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <Chip 
                    label={dataSource === 'real' ? 'Live Network Data' : 
                           dataSource === 'collector' ? 'Collector Service' :
                           dataSource === 'gns3' ? 'GNS3 Network Simulator' :
                           dataSource === 'sdn' ? 'SDN Controller' :
                           dataSource === 'mock' ? 'Mock Data (Demo)' : 'Generated Data'}
                    color={dataSource === 'real' || dataSource === 'collector' ? 'success' : 
                           dataSource === 'gns3' || dataSource === 'sdn' ? 'primary' : 'warning'}
                    size="small"
                    sx={{ mr: 1, mb: 1 }}
                  />
                </Box>
                <Typography variant="body2" color="text.secondary" paragraph>
                  {dataSource === 'real' ? 
                    'This topology shows live network data collected in real-time from your GNS3 network and SDN controller. Node positions, connections, and status information reflect the actual network state.' :
                    dataSource === 'collector' ?
                    'Data is aggregated by the collector service from multiple sources including GNS3 nodes, SDN switches, and federated learning components. Updates every 30 seconds.' :
                    dataSource === 'gns3' ?
                    'Network topology from GNS3 network simulator. Shows virtualized network devices, their configurations, and interconnections.' :
                    dataSource === 'sdn' ?
                    'Software-Defined Network topology from the SDN controller. Displays OpenFlow switches, hosts, and flow information.' :
                    dataSource === 'mock' ?
                    'This is demonstration data generated for testing purposes. It simulates a real federated learning network with SDN integration.' :
                    'Generated topology data for visualization testing. Not connected to actual network infrastructure.'}
                </Typography>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Node Types & Services
                </Typography>
                <Stack spacing={1}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <RouterIcon fontSize="small" color="primary" />
                    <Typography variant="body2">
                      <strong>Switches:</strong> OpenFlow-enabled switches managed by SDN controller
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={1}>
                    <ComputerIcon fontSize="small" color="success" />
                    <Typography variant="body2">
                      <strong>FL Clients/Servers:</strong> Federated learning nodes participating in training
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={1}>
                    <SecurityIcon fontSize="small" color="secondary" />
                    <Typography variant="body2">
                      <strong>Policy Engine:</strong> Decision-making component for network and FL optimization
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={1}>
                    <StorageIcon fontSize="small" color="info" />
                    <Typography variant="body2">
                      <strong>Collector:</strong> Metrics and data collection service
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={1}>
                    <CloudIcon fontSize="small" color="warning" />
                    <Typography variant="body2">
                      <strong>Cloud/Gateway:</strong> External network connections and cloud services
                    </Typography>
                  </Box>
                </Stack>
              </Grid>
            </Grid>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body2" color="text.secondary">
              <strong>Interaction:</strong> Click on any node to view detailed information. Drag nodes to reposition them. 
              Use Ctrl+Scroll to zoom in/out. The star topology shows a central node connected to all other nodes for visualization clarity.
            </Typography>
          </AccordionDetails>
        </Accordion>

        {/* Topology Visualization */}
        <Paper sx={{ p: 2, mb: 3, borderRadius: 2 }}>
          {/* Zoom Controls */}
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
            <Tooltip title="Zoom In">
              <IconButton size="small" onClick={handleZoomIn}>+</IconButton>
            </Tooltip>
            <Tooltip title="Zoom Out">
              <IconButton size="small" onClick={handleZoomOut}>-</IconButton>
            </Tooltip>
            <Tooltip title="Reset Zoom">
              <IconButton size="small" onClick={handleZoomReset}>⌂</IconButton>
            </Tooltip>
            <Typography variant="body2" sx={{ alignSelf: 'center', ml: 1, color: 'text.secondary' }}>
              {Math.round(zoom * 100)}%
            </Typography>
          </Box>
          
          <Box sx={{ overflow: 'auto', width: '100%' }}>
            <svg
              ref={svgRef}
              width={width}
              height={height}
              style={{ 
                border: '1px solid #e0e0e0', 
                borderRadius: '8px', 
                width: '100%',
                maxWidth: 'none',
                cursor: isDragging ? 'grabbing' : 'grab'
              }}
              viewBox={`0 0 ${width} ${height}`}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={handleWheel}
            >
              <g transform={`translate(${centerX}, ${centerY}) scale(${zoom}) translate(${-centerX}, ${-centerY})`}>
                {/* Render star connections from center to all other nodes */}
                {positionedNodes.length > 1 && positionedNodes.slice(1).map((node: any, index: number) => {
                  const centerNode = positionedNodes[0];
                  return (
                    <line
                      key={`star-link-${index}`}
                      x1={centerNode.x}
                      y1={centerNode.y}
                      x2={node.x}
                      y2={node.y}
                      stroke="#2196f3"
                      strokeWidth={2}
                      opacity={0.7}
                    />
                  );
                })}
                
                {/* Render nodes */}
                {positionedNodes.map((node: any, index: number) => {
                  const isCenterNode = node.isCenterNode;
                  const isSwitch = node.type === 'switch' || node.service_type === 'switch';
                  const isCloud = node.template_name === 'Cloud' || node.service_type === 'cloud';
                  
                  const radius = isCenterNode ? 50 : (isSwitch ? 35 : (isCloud ? 30 : 25));
                  const color = isCenterNode ? '#f44336' : (isSwitch ? '#1976d2' : (isCloud ? '#ff9800' : '#4caf50'));
                  const strokeWidth = isCenterNode ? 5 : 3;
                    let deviceType = node.service_type;
                  if (!deviceType && node.template_name === 'Cloud') {
                    deviceType = 'cloud';
                  } else if (!deviceType && isSwitch) {
                    deviceType = 'switch';
                  } else if (!deviceType) {
                    deviceType = 'host';
                  }

                  const tooltipInfo = getNodeTooltipInfo(node);
                  
                  return (
                    <g key={`node-${index}`}>
                      {/* Glow effect for center node */}
                      {isCenterNode && (
                        <circle
                          cx={node.x}
                          cy={node.y}
                          r={radius + 10}
                          fill={color}
                          opacity={0.3}
                          stroke="none"
                        />
                      )}
                        {/* Main node circle with enhanced tooltip */}
                      <circle
                        cx={node.x}
                        cy={node.y}
                        r={radius}
                        fill={color}
                        stroke="#fff"
                        strokeWidth={strokeWidth}
                        style={{ cursor: 'pointer' }}
                        onMouseDown={(e) => handleMouseDown(e, node)}
                        onClick={() => setSelectedNode(node)}
                        opacity={0.9}
                      >
                        <title>
                          {`${node.name || node.id || 'Unknown'}\n${tooltipInfo.description}\n${tooltipInfo.additionalInfo}\nData Source: ${dataSource.toUpperCase()}\nClick for detailed information`}
                        </title>
                      </circle>
                      
                      {/* Icon */}
                      <image
                        x={node.x - (isCenterNode ? 20 : 15)}
                        y={node.y - (isCenterNode ? 20 : 15)}
                        width={isCenterNode ? "40" : "30"}
                        height={isCenterNode ? "40" : "30"}
                        href={getDeviceImage(deviceType)}
                        style={{ pointerEvents: 'none' }}
                      />
                      
                      {/* Node label */}
                      <text
                        x={node.x}
                        y={node.y + radius + 25}
                        textAnchor="middle"
                        fontSize={isCenterNode ? "16" : "12"}
                        fill="#333"
                        fontWeight={isCenterNode ? "700" : "600"}
                      >
                        {node.name || node.id || 'Unknown'}
                      </text>
                      
                      {/* Center indicator */}
                      {isCenterNode && (
                        <text
                          x={node.x}
                          y={node.y + radius + 45}
                          textAnchor="middle"
                          fontSize="12"
                          fill="#f44336"
                          fontWeight="500"
                        >
                          (Center)
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            </svg>
          </Box>          {/* Enhanced Legend with tooltips */}
          <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center', gap: 4 }}>
            <DataSourceTooltip
              title="Center Node"
              dataSource={dataSource}
              description="The central node in star topology - typically the most important or well-connected node"
              additionalInfo="In FL networks, this is often the server or main controller"
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'help' }}>
                <Box sx={{ width: 20, height: 20, borderRadius: '50%', bgcolor: '#f44336' }} />
                <Typography variant="body2" sx={{ fontWeight: 500 }}>Center Node</Typography>
              </Box>
            </DataSourceTooltip>
            <DataSourceTooltip
              title="Network Switches"
              dataSource={dataSource}
              description="OpenFlow switches that forward packets based on flow rules from SDN controller"
              additionalInfo="Managed by SDN controller for dynamic traffic management"
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'help' }}>
                <Box sx={{ width: 20, height: 20, borderRadius: '50%', bgcolor: '#1976d2' }} />
                <Typography variant="body2" sx={{ fontWeight: 500 }}>Switches</Typography>
              </Box>
            </DataSourceTooltip>
            <DataSourceTooltip
              title="Host Devices"
              dataSource={dataSource}
              description="End devices including FL clients, servers, and other network services"
              additionalInfo="Includes federated learning nodes and system components"
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'help' }}>
                <Box sx={{ width: 20, height: 20, borderRadius: '50%', bgcolor: '#4caf50' }} />
                <Typography variant="body2" sx={{ fontWeight: 500 }}>Hosts</Typography>
              </Box>
            </DataSourceTooltip>
            <DataSourceTooltip
              title="Network Connections"
              dataSource={dataSource}
              description="Logical connections in star topology for visualization"
              additionalInfo="Physical topology may differ - this shows conceptual relationships"
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, cursor: 'help' }}>
                <Box sx={{ width: 30, height: 2, bgcolor: '#2196f3' }} />
                <Typography variant="body2" sx={{ fontWeight: 500 }}>Star Links</Typography>
              </Box>
            </DataSourceTooltip>
          </Box>
        </Paper>

        {/* Enhanced Topology Statistics with data source info */}
        <Grid container spacing={2}>
          <Grid item xs={6} md={3}>
            <DataSourceTooltip
              title="Network Switches"
              dataSource={dataSource}
              description="Total number of OpenFlow switches detected in the network"
              additionalInfo={dataSource === 'mock' ? 'Sample switch data for demonstration' : 'Live switch count from SDN controller'}
            >
              <Paper sx={{ p: 2, textAlign: 'center', borderRadius: 2, cursor: 'help' }}>
                <Typography variant="h4" color="primary" sx={{ fontWeight: 600 }}>{switches.length}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>Switches</Typography>
              </Paper>
            </DataSourceTooltip>
          </Grid>
          <Grid item xs={6} md={3}>
            <DataSourceTooltip
              title="Host Devices"
              dataSource={dataSource}
              description="Network hosts including FL clients, servers, and system services"
              additionalInfo={dataSource === 'mock' ? 'Sample host data for demonstration' : 'Live host count from network discovery'}
            >
              <Paper sx={{ p: 2, textAlign: 'center', borderRadius: 2, cursor: 'help' }}>
                <Typography variant="h4" color="success.main" sx={{ fontWeight: 600 }}>{hosts.length}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>Hosts</Typography>
              </Paper>
            </DataSourceTooltip>
          </Grid>
          <Grid item xs={6} md={3}>
            <DataSourceTooltip
              title="Other Devices"
              dataSource={dataSource}
              description="Other network devices or services not classified as switches or hosts"
              additionalInfo="May include routers, gateways, or specialized network appliances"
            >
              <Paper sx={{ p: 2, textAlign: 'center', borderRadius: 2, cursor: 'help' }}>
                <Typography variant="h4" color="warning.main" sx={{ fontWeight: 600 }}>{others.length}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>Others</Typography>
              </Paper>
            </DataSourceTooltip>
          </Grid>
          <Grid item xs={6} md={3}>
            <DataSourceTooltip
              title="Total Network Nodes"
              dataSource={dataSource}
              description="Total count of all network devices and services in the topology"
              additionalInfo={`Data freshness: ${liveTopology?.timestamp ? 'Live' : 'Cached'}`}
            >
              <Paper sx={{ p: 2, textAlign: 'center', borderRadius: 2, cursor: 'help' }}>
                <Typography variant="h4" color="info.main" sx={{ fontWeight: 600 }}>{allNodes.length}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>Total Nodes</Typography>
              </Paper>
            </DataSourceTooltip>
          </Grid>
        </Grid>

        {/* Information Section */}
        <Accordion sx={{ mt: 3, borderRadius: 2 }} defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>Topology Data Sources</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" paragraph>
              This network topology is generated from real-time data collected from various network devices. The data is processed and visualized to provide insights into the network structure and status.
            </Typography>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Node Types:</strong> The topology displays different types of nodes including switches, hosts, and other devices. Each node type is represented by a unique color and icon for easy identification.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Switches:</strong> Represented in blue, switches are network devices that connect multiple hosts and forward data packets between them.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Hosts:</strong> Represented in green, hosts are devices such as computers and servers that communicate over the network.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Others:</strong> Represented in orange, these are other types of network devices that do not fall into the switch or host categories.
            </Typography>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="body2" color="text.secondary" paragraph>
              <strong>Data Sources:</strong> The data for this topology is sourced from network discovery protocols and APIs. It includes information such as device types, connections, and real-time status updates.
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              The topology is updated in real-time to reflect the current state of the network. Use the controls to zoom, pan, and interact with the topology for detailed analysis.
            </Typography>
          </AccordionDetails>
        </Accordion>
      </Box>
    );
  };
  
  return renderTopology();
};
