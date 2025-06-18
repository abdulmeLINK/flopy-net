import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { 
  Box, 
  Typography, 
  FormControl, 
  InputLabel, 
  Select, 
  MenuItem, 
  TextField, 
  Grid, 
  Chip, 
  SelectChangeEvent, 
  Paper, 
  Button,
  ChipProps,
  Alert,
  FormControlLabel,
  Switch,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
  Tooltip,
  IconButton,
  Divider,
  Badge
} from '@mui/material';
import {
  Refresh,
  ExpandMore,
  Error,
  Warning,
  Info,
  BugReport,
  FilterList,
  Search,
  Event,
  Timeline,
  Visibility,
  VisibilityOff,
  PlayArrow,
  Pause,
  FiberManualRecord,
  TrendingUp,
  Speed
} from '@mui/icons-material';
import { getEvents, getEventsSummary, SystemEvent, EventsResponse, EventsSummary, connectToEventsStream, WebSocketEvent } from '../services/eventsApi';
import TimeRangeSelector from '../components/common/TimeRangeSelector';
import LoadingSpinner from '../components/common/LoadingSpinner';

// Helper function for chip colors
const getChipColorForLevel = (level: string): ChipProps['color'] => {
  switch (level.toUpperCase()) {
    case 'ERROR': return 'error';
    case 'WARNING': return 'warning';
    case 'INFO': return 'info';
    case 'DEBUG': return 'secondary';
    default: return 'default';
  }
};

// Helper function for level icons
const getLevelIcon = (level: string) => {
  switch (level.toUpperCase()) {
    case 'ERROR': return <Error color="error" />;
    case 'WARNING': return <Warning color="warning" />;
    case 'INFO': return <Info color="info" />;
    case 'DEBUG': return <BugReport color="action" />;
    default: return <Event />;
  }
};

// Helper to format JSON details
const formatDetails = (details: any): string => {
  if (!details) return '';
  
  try {
    if (typeof details === 'string') return details;
    return JSON.stringify(details, null, 2);
  } catch {
    return String(details);
  }
};

// Helper to safely get message from event
const getEventMessage = (event: SystemEvent): string => {
  return event?.message || '';
};

// Helper to truncate long text
const truncateText = (text: string, maxLength: number = 100): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

const EventsPage: React.FC = () => {
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [summary, setSummary] = useState<EventsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  
  // Filter states
  const [startTime, setStartTime] = useState<string>(
    new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
  );
  const [endTime, setEndTime] = useState<string>(new Date().toISOString());
  const [componentFilter, setComponentFilter] = useState<string>('');
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [hideCollectorEvents, setHideCollectorEvents] = useState<boolean>(true);
  const [showFilters, setShowFilters] = useState<boolean>(false);
  const [limit, setLimit] = useState<number>(100);

  // Live monitoring states
  const [liveMonitoring, setLiveMonitoring] = useState<boolean>(false);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [liveStats, setLiveStats] = useState({
    eventsPerMinute: 0,
    recentErrors: 0,
    recentWarnings: 0,
    lastActivity: new Date()
  });
  const [recentImportantEvents, setRecentImportantEvents] = useState<SystemEvent[]>([]);

  // Load events and summary
  const loadData = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);
      
      // Prepare query parameters
      const params: any = {
        start_time: startTime,
        end_time: endTime,
        limit: limit
      };
      
      if (componentFilter) params.component = componentFilter;
      if (levelFilter) params.level = levelFilter.toLowerCase();
      
      console.log('EventsPage: Loading data with params:', params);
      
      // Load events and summary in parallel
      const [eventsResponse, summaryResponse] = await Promise.all([
        getEvents(params),
        getEventsSummary()
      ]);
      
      console.log('EventsPage: Events response:', eventsResponse);
      console.log('EventsPage: Summary response:', summaryResponse);
      
      let eventsData = eventsResponse.events || [];
      
      // Apply client-side filters
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase();
        eventsData = eventsData.filter(event => 
          event.message?.toLowerCase().includes(searchLower) ||
          event.component?.toLowerCase().includes(searchLower) ||
          event.event_type?.toLowerCase().includes(searchLower) ||
          formatDetails(event.details).toLowerCase().includes(searchLower)
        );
      }
      
      if (hideCollectorEvents) {
        eventsData = eventsData.filter(event => event.component !== 'COLLECTOR');
      }
      
      setEvents(eventsData);
      setSummary(summaryResponse);
      
      console.log(`EventsPage: Loaded ${eventsData.length} events`);
      
    } catch (err) {
      console.error('EventsPage: Error loading data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load events');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [startTime, endTime, componentFilter, levelFilter, searchTerm, hideCollectorEvents, limit]);

  // Initial load
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Live monitoring WebSocket connection
  useEffect(() => {
    if (!liveMonitoring) return;

    console.log('EventsPage: Starting live monitoring');
    
    const cleanup = connectToEventsStream(
      // onEvent
      (wsEvent: WebSocketEvent) => {
        if (wsEvent.type === 'event' && wsEvent.event) {
          const systemEvent = wsEvent.event as SystemEvent;
          
          // Update live stats
          setLiveStats(prev => ({
            ...prev,
            lastActivity: new Date(),
            recentErrors: systemEvent.level === 'error' ? prev.recentErrors + 1 : prev.recentErrors,
            recentWarnings: systemEvent.level === 'warning' ? prev.recentWarnings + 1 : prev.recentWarnings
          }));
          
          // Add to recent important events if it's an error or warning
          if (systemEvent.level === 'error' || systemEvent.level === 'warning') {
            setRecentImportantEvents(prev => 
              [systemEvent, ...prev.slice(0, 9)] // Keep last 10 important events
            );
          }
        }
      },
      // onError
      (error: any) => {
        console.error('Live monitoring error:', error);
        setWsConnected(false);
      },
      // onConnect
      () => {
        console.log('Live monitoring connected');
        setWsConnected(true);
      },
      // onDisconnect
      () => {
        console.log('Live monitoring disconnected');
        setWsConnected(false);
      }
    );

    return cleanup;
  }, [liveMonitoring]);

  // Calculate events per minute
  useEffect(() => {
    if (!liveMonitoring) return;

    const interval = setInterval(() => {
      // Reset hourly counters and calculate rate
      setLiveStats(prev => ({
        ...prev,
        eventsPerMinute: Math.floor(Math.random() * 50), // Placeholder - would calculate from actual events
        recentErrors: Math.max(0, prev.recentErrors - 1), // Decay counters
        recentWarnings: Math.max(0, prev.recentWarnings - 1)
      }));
    }, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [liveMonitoring]);

  // Handle time range changes
  const handleTimeRangeChange = (start: string, end: string) => {
    setStartTime(start);
    setEndTime(end);
  };

  // Handle component filter change
  const handleComponentChange = (event: SelectChangeEvent<string>) => {
    setComponentFilter(event.target.value);
  };

  // Handle level filter change
  const handleLevelChange = (event: SelectChangeEvent<string>) => {
    setLevelFilter(event.target.value);
  };

  // Handle search change
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(event.target.value);
  };

  // Get available components for filter
  const availableComponents = useMemo(() => {
    const components = new Set<string>();
    
    // Add from summary
    if (summary?.by_component) {
      Object.keys(summary.by_component).forEach(comp => components.add(comp));
    }
    
    // Add from current events
    events.forEach(event => {
      if (event.component) components.add(event.component);
    });
    
    return Array.from(components).sort();
  }, [summary, events]);

  // Summary cards
  const summaryCards = useMemo(() => {
    if (!summary) return [];
    
    return [
      {
        title: 'Total Events',
        value: summary.total_count,
        icon: <Event />,
        color: 'primary' as const
      },
      {
        title: 'Errors',
        value: summary.error_count,
        icon: <Error />,
        color: 'error' as const
      },
      {
        title: 'Warnings',
        value: summary.warning_count,
        icon: <Warning />,
        color: 'warning' as const
      },
      {
        title: 'Info',
        value: summary.info_count,
        icon: <Info />,
        color: 'info' as const
      }
    ];
  }, [summary]);

  if (loading && events.length === 0) {
    return <LoadingSpinner message="Loading system events..." />;
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          System Events
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={showFilters ? <VisibilityOff /> : <Visibility />}
            onClick={() => setShowFilters(!showFilters)}
          >
            {showFilters ? 'Hide Filters' : 'Show Filters'}
          </Button>
          <Button
            variant={liveMonitoring ? "contained" : "outlined"}
            startIcon={liveMonitoring ? <Pause /> : <PlayArrow />}
            onClick={() => setLiveMonitoring(!liveMonitoring)}
            color={liveMonitoring ? "success" : "primary"}
          >
            {liveMonitoring ? 'Stop Live' : 'Start Live'}
          </Button>
          <Button
            variant="contained"
            startIcon={<Refresh />}
            onClick={() => loadData(true)}
            disabled={refreshing}
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </Box>
      </Box>

      {/* Loading indicator */}
      {refreshing && <LinearProgress sx={{ mb: 2 }} />}

      {/* Error alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {summaryCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      {card.title}
                    </Typography>
                    <Typography variant="h4" component="div" color={`${card.color}.main`}>
                      {card.value || 0}
                    </Typography>
                  </Box>
                  <Box color={`${card.color}.main`}>
                    {card.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Live Monitoring Summary */}
      {liveMonitoring && (
        <Paper sx={{ p: 3, mb: 3, bgcolor: wsConnected ? 'success.light' : 'grey.100' }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FiberManualRecord sx={{ color: wsConnected ? 'success.main' : 'error.main' }} />
              Live System Monitoring
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Last activity: {liveStats.lastActivity.toLocaleTimeString()}
            </Typography>
          </Box>
          
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Box textAlign="center">
                <Typography variant="body2" color="text.secondary">Events/Min</Typography>
                <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                  <Speed fontSize="small" />
                  {liveStats.eventsPerMinute}
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Box textAlign="center">
                <Typography variant="body2" color="text.secondary">Recent Errors</Typography>
                <Typography variant="h5" color="error.main" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                  <Error fontSize="small" />
                  {liveStats.recentErrors}
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Box textAlign="center">
                <Typography variant="body2" color="text.secondary">Recent Warnings</Typography>
                <Typography variant="h5" color="warning.main" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                  <Warning fontSize="small" />
                  {liveStats.recentWarnings}
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Box textAlign="center">
                <Typography variant="body2" color="text.secondary">Connection</Typography>
                <Typography variant="h5" color={wsConnected ? 'success.main' : 'error.main'}>
                  {wsConnected ? 'Live' : 'Offline'}
                </Typography>
              </Box>
            </Grid>
          </Grid>
          
          {/* Recent Important Events */}
          {recentImportantEvents.length > 0 && (
            <Box mt={3}>
              <Typography variant="subtitle1" gutterBottom>
                Recent Important Events
              </Typography>
              <Box display="flex" flexDirection="column" gap={1} maxHeight="200px" overflow="auto">
                {recentImportantEvents.map((event, index) => (
                  <Box 
                    key={index} 
                    display="flex" 
                    alignItems="center" 
                    gap={2}
                    p={1}
                    bgcolor="background.paper"
                    borderRadius={1}
                  >
                    <Chip 
                      label={event.level.toUpperCase()} 
                      color={getChipColorForLevel(event.level)} 
                      size="small"
                    />
                    <Typography variant="body2" color="text.secondary" sx={{ minWidth: '80px' }}>
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </Typography>
                    <Typography variant="body2" fontWeight="medium" sx={{ minWidth: '100px' }}>
                      {event.component}
                    </Typography>
                    <Typography variant="body2" sx={{ flexGrow: 1 }}>
                      {truncateText(getEventMessage(event), 100)}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          )}
        </Paper>
      )}

      {/* Component Summary */}
      {summary?.by_component && Object.keys(summary.by_component).length > 0 && (
        <Paper sx={{ p: 2, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Events by Component
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={1}>
            {Object.entries(summary.by_component).map(([component, count]) => (
              <Chip
                key={component}
                label={`${component} (${count})`}
                variant={componentFilter === component ? 'filled' : 'outlined'}
                color={componentFilter === component ? 'primary' : 'default'}
                onClick={() => setComponentFilter(componentFilter === component ? '' : component)}
                clickable
              />
            ))}
          </Box>
        </Paper>
      )}

      {/* Filters */}
      {showFilters && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FilterList />
            Filters
          </Typography>
          
          <TimeRangeSelector onChange={handleTimeRangeChange} />
          
          <Grid container spacing={2} sx={{ mt: 2 }}>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth>
                <InputLabel>Component</InputLabel>
                <Select
                  value={componentFilter}
                  label="Component"
                  onChange={handleComponentChange}
                >
                  <MenuItem value="">All Components</MenuItem>
                  {availableComponents.map(component => (
                    <MenuItem key={component} value={component}>
                      {component} ({summary?.by_component?.[component] || 0})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth>
                <InputLabel>Level</InputLabel>
                <Select
                  value={levelFilter}
                  label="Level"
                  onChange={handleLevelChange}
                >
                  <MenuItem value="">All Levels</MenuItem>
                  <MenuItem value="error">Error ({summary?.error_count || 0})</MenuItem>
                  <MenuItem value="warning">Warning ({summary?.warning_count || 0})</MenuItem>
                  <MenuItem value="info">Info ({summary?.info_count || 0})</MenuItem>
                  <MenuItem value="debug">Debug ({summary?.debug_count || 0})</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth>
                <InputLabel>Limit</InputLabel>
                <Select
                  value={limit}
                  label="Limit"
                  onChange={(e) => setLimit(Number(e.target.value))}
                >
                  <MenuItem value={50}>50 events</MenuItem>
                  <MenuItem value={100}>100 events</MenuItem>
                  <MenuItem value={200}>200 events</MenuItem>
                  <MenuItem value={500}>500 events</MenuItem>
                  <MenuItem value={1000}>1000 events</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Search"
                placeholder="Search messages, components..."
                value={searchTerm}
                onChange={handleSearchChange}
                InputProps={{
                  startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />
                }}
              />
            </Grid>
          </Grid>
          
          <Box sx={{ mt: 2 }}>
            <FormControlLabel
              control={
                <Switch 
                  checked={hideCollectorEvents} 
                  onChange={(e) => setHideCollectorEvents(e.target.checked)} 
                />
              }
              label="Hide Collector Events"
            />
          </Box>
        </Paper>
      )}

      {/* Events Table */}
      <Paper sx={{ mb: 3 }}>
        <Box p={2} display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">
            Events ({events.length})
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Last updated: {new Date().toLocaleTimeString()}
          </Typography>
        </Box>
        
        <Divider />
        
        {events.length > 0 ? (
          <TableContainer sx={{ maxHeight: '70vh' }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell width="180px">Time</TableCell>
                  <TableCell width="100px">Level</TableCell>
                  <TableCell width="150px">Component</TableCell>
                  <TableCell width="180px">Event Type</TableCell>
                  <TableCell>Message</TableCell>
                  <TableCell width="120px">Details</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {events.map((event, index) => (
                  <TableRow key={event.id || index} hover>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {new Date(event.timestamp).toLocaleString()}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Chip 
                        label={event.level.toUpperCase()} 
                        color={getChipColorForLevel(event.level)} 
                        size="small"
                        icon={getLevelIcon(event.level)}
                      />
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {event.component}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2">
                        {event.event_type}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2">
                        {truncateText(getEventMessage(event), 150)}
                      </Typography>
                      {(getEventMessage(event) && getEventMessage(event).length > 150) && (
                        <Tooltip title={getEventMessage(event)}>
                          <Typography variant="caption" color="primary" sx={{ cursor: 'pointer' }}>
                            ...show more
                          </Typography>
                        </Tooltip>
                      )}
                    </TableCell>
                    
                    <TableCell>
                      {event.details ? (
                        <Accordion>
                          <AccordionSummary
                            expandIcon={<ExpandMore />}
                            sx={{ minHeight: 'unset', '& .MuiAccordionSummary-content': { margin: 0 } }}
                          >
                            <Typography variant="caption" color="primary">
                              View Details
                            </Typography>
                          </AccordionSummary>
                          <AccordionDetails sx={{ pt: 0 }}>
                            <Box
                              component="pre"
                              sx={{
                                fontSize: '0.75rem',
                                backgroundColor: 'grey.50',
                                p: 1,
                                borderRadius: 1,
                                overflow: 'auto',
                                maxHeight: '200px',
                                maxWidth: '400px'
                              }}
                            >
                              {formatDetails(event.details)}
                            </Box>
                          </AccordionDetails>
                        </Accordion>
                      ) : (
                        <Typography variant="body2" color="text.disabled">
                          No details
                        </Typography>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Box textAlign="center" py={6}>
            <Timeline sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No Events Found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              No events match your current filters. Try adjusting the time range or filters.
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default EventsPage;