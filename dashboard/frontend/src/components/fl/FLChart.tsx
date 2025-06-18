import React, { useMemo, useState, useCallback, useRef, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Scatter,
  ScatterChart,
  Cell
} from 'recharts';
import { 
  Box, 
  Typography, 
  Chip, 
  IconButton, 
  Menu, 
  MenuItem, 
  Tooltip as MuiTooltip,
  Switch,
  FormControlLabel,
  Button,
  Divider,
  Badge,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Checkbox,
  TextField,
  Stack
} from '@mui/material';
import {
  MoreVert as MoreVertIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  FilterList as FilterListIcon,
  Restore as RestoreIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  RadioButtonUnchecked as DotsIcon,
  Timeline as SmoothLineIcon
} from '@mui/icons-material';

interface FLMetric {
  timestamp: string;
  round: number;
  accuracy: number;
  loss: number;
  clients_connected: number;
  clients_total: number;
  training_complete: boolean;
  model_size_mb: number;
  status: string;
}

interface FLChartProps {
  data: FLMetric[];
  title: string;
  dataKey: 'accuracy' | 'loss' | 'clients_connected' | 'model_size_mb';
  color: string;
  yAxisLabel?: string;
  formatter?: (value: number) => string;
  showTrend?: boolean;
  enableDataPointRemoval?: boolean;
  onDataPointsChanged?: (excludedRounds: number[]) => void;
  showDots?: boolean;
  enableDotToggle?: boolean;
}

interface DataPointFilter {
  excludedRounds: Set<number>;
  showExcluded: boolean;
  filterByValue: {
    enabled: boolean;
    min?: number;
    max?: number;
  };
}

const FLChart: React.FC<FLChartProps> = ({
  data,
  title,
  dataKey,
  color,
  yAxisLabel,
  formatter = (value) => value?.toString() || '0',
  showTrend = true,
  enableDataPointRemoval = false,
  onDataPointsChanged,
  showDots = true,
  enableDotToggle = true
}) => {
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [filterDialogOpen, setFilterDialogOpen] = useState(false);
  const [dotsVisible, setDotsVisible] = useState(showDots);
  const [filter, setFilter] = useState<DataPointFilter>({
    excludedRounds: new Set(),
    showExcluded: false,
    filterByValue: {
      enabled: false
    }
  });
  const [valueFilterMin, setValueFilterMin] = useState<string>('');
  const [valueFilterMax, setValueFilterMax] = useState<string>('');
  
  // Zoom state
  const [zoomDomain, setZoomDomain] = useState<{x?: [number, number], y?: [number, number]} | null>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const [isZooming, setIsZooming] = useState(false);

  const yAxisTickFormatter = (value: any) => {
    if (typeof value === 'number') {
      if (Number.isInteger(value)) {
        return value.toString();
      }
      return value.toFixed(3);
    }
    return value;
  };

  const { processedData, excludedData, trendInfo } = useMemo(() => {
    if (!data || data.length === 0) {
      return { processedData: [], excludedData: [], trendInfo: null };
    }

    // Sort data by round and filter valid values
    const sortedData = [...data]
      .filter(d => d.round > 0 && d[dataKey] != null && !isNaN(d[dataKey] as number))
      .sort((a, b) => a.round - b.round);
    
    // Apply value-based filtering if enabled
    let filteredData = sortedData;
    if (filter.filterByValue.enabled) {
      const min = filter.filterByValue.min;
      const max = filter.filterByValue.max;
      filteredData = sortedData.filter(d => {
        const value = d[dataKey] as number;
        if (min !== undefined && value < min) return false;
        if (max !== undefined && value > max) return false;
        return true;
      });
    }

    // Separate excluded and included data points
    const includedData = filteredData.filter(d => !filter.excludedRounds.has(d.round));
    const excludedDataPoints = filteredData.filter(d => filter.excludedRounds.has(d.round));
    
    // Calculate trend information based on included data only
    const values = includedData.map(d => d[dataKey] as number);
    let trend = null;
    
    if (values.length >= 2) {
      const firstValue = values[0];
      const lastValue = values[values.length - 1];
      const improvement = lastValue - firstValue;
      const improvementPercent = firstValue !== 0 ? (improvement / firstValue) * 100 : 0;
      
      trend = {
        improvement,
        improvementPercent,
        direction: improvement >= 0 ? 'up' : 'down',
        best: dataKey === 'loss' ? Math.min(...values) : Math.max(...values),
        latest: lastValue,
        includedDataPoints: includedData.length,
        excludedDataPoints: excludedDataPoints.length
      };
    }

    return {
      processedData: includedData,
      excludedData: excludedDataPoints,
      trendInfo: trend
    };
  }, [data, dataKey, filter]);

  // Add wheel event listener for zoom functionality
  useEffect(() => {
    const chartElement = chartRef.current;
    if (!chartElement) return;

    const handleWheel = (event: WheelEvent) => {
      // Only zoom when Ctrl key is pressed
      if (event.ctrlKey) {
        event.preventDefault();
        
        const delta = event.deltaY;
        const zoomIn = delta < 0;
        const zoomFactor = 1.1;
        
        if (processedData.length === 0) return;
        
        // Get current domain or calculate from data
        const currentXDomain = zoomDomain?.x || [
          Math.min(...processedData.map(d => d.round)),
          Math.max(...processedData.map(d => d.round))
        ];
        
        const values = processedData.map(d => d[dataKey] as number);
        const currentYDomain = zoomDomain?.y || [
          Math.min(...values),
          Math.max(...values)
        ];
        
        // Calculate zoom center (mouse position would be ideal, but use center for simplicity)
        const xCenter = (currentXDomain[0] + currentXDomain[1]) / 2;
        const yCenter = (currentYDomain[0] + currentYDomain[1]) / 2;
        
        // Calculate new domain
        const xRange = currentXDomain[1] - currentXDomain[0];
        const yRange = currentYDomain[1] - currentYDomain[0];
        
        const newXRange = zoomIn ? xRange / zoomFactor : xRange * zoomFactor;
        const newYRange = zoomIn ? yRange / zoomFactor : yRange * zoomFactor;
        
        const newXDomain: [number, number] = [
          xCenter - newXRange / 2,
          xCenter + newXRange / 2
        ];
        
        const newYDomain: [number, number] = [
          yCenter - newYRange / 2,
          yCenter + newYRange / 2
        ];
        
        // Constrain to data bounds
        const dataXMin = Math.min(...processedData.map(d => d.round));
        const dataXMax = Math.max(...processedData.map(d => d.round));
        const dataYMin = Math.min(...values);
        const dataYMax = Math.max(...values);
        
        const constrainedXDomain: [number, number] = [
          Math.max(newXDomain[0], dataXMin - (dataXMax - dataXMin) * 0.1),
          Math.min(newXDomain[1], dataXMax + (dataXMax - dataXMin) * 0.1)
        ];
        
        const constrainedYDomain: [number, number] = [
          Math.max(newYDomain[0], dataYMin - (dataYMax - dataYMin) * 0.1),
          Math.min(newYDomain[1], dataYMax + (dataYMax - dataYMin) * 0.1)
        ];
        
        setZoomDomain({
          x: constrainedXDomain,
          y: constrainedYDomain
        });
        
        setIsZooming(true);
        setTimeout(() => setIsZooming(false), 100);
      }
    };

    chartElement.addEventListener('wheel', handleWheel, { passive: false });
    
    return () => {
      chartElement.removeEventListener('wheel', handleWheel);
    };
  }, [processedData, dataKey, zoomDomain]);

  // Reset zoom function
  const handleResetZoom = useCallback(() => {
    setZoomDomain(null);
  }, []);

  // Handle data point exclusion/inclusion
  const toggleDataPoint = useCallback((round: number) => {
    setFilter(prev => {
      const newExcluded = new Set(prev.excludedRounds);
      if (newExcluded.has(round)) {
        newExcluded.delete(round);
      } else {
        newExcluded.add(round);
      }
      
      const newFilter = {
        ...prev,
        excludedRounds: newExcluded
      };
      
      // Notify parent component
      if (onDataPointsChanged) {
        onDataPointsChanged(Array.from(newExcluded));
      }
      
      return newFilter;
    });
  }, [onDataPointsChanged]);

  // Handle bulk operations
  const handleRestoreAll = useCallback(() => {
    setFilter(prev => ({
      ...prev,
      excludedRounds: new Set()
    }));
    if (onDataPointsChanged) {
      onDataPointsChanged([]);
    }
  }, [onDataPointsChanged]);

  const handleExcludeOutliers = useCallback(() => {
    if (!data || data.length === 0) return;
    
    const values = data.map(d => d[dataKey] as number).filter(v => !isNaN(v));
    if (values.length < 4) return; // Need at least 4 points to identify outliers
    
    // Calculate quartiles and IQR
    const sorted = [...values].sort((a, b) => a - b);
    const q1 = sorted[Math.floor(sorted.length * 0.25)];
    const q3 = sorted[Math.floor(sorted.length * 0.75)];
    const iqr = q3 - q1;
    const lowerBound = q1 - 1.5 * iqr;
    const upperBound = q3 + 1.5 * iqr;
    
    // Find outlier rounds
    const outlierRounds = data
      .filter(d => {
        const value = d[dataKey] as number;
        return !isNaN(value) && (value < lowerBound || value > upperBound);
      })
      .map(d => d.round);
    
    setFilter(prev => ({
      ...prev,
      excludedRounds: new Set([...prev.excludedRounds, ...outlierRounds])
    }));
    
    if (onDataPointsChanged) {
      onDataPointsChanged(Array.from(new Set([...filter.excludedRounds, ...outlierRounds])));
    }
  }, [data, dataKey, filter.excludedRounds, onDataPointsChanged]);

  // Apply value-based filtering
  const handleApplyValueFilter = useCallback(() => {
    const min = valueFilterMin ? parseFloat(valueFilterMin) : undefined;
    const max = valueFilterMax ? parseFloat(valueFilterMax) : undefined;
    
    setFilter(prev => ({
      ...prev,
      filterByValue: {
        enabled: true,
        min: isNaN(min!) ? undefined : min,
        max: isNaN(max!) ? undefined : max
      }
    }));
    setFilterDialogOpen(false);
  }, [valueFilterMin, valueFilterMax]);

  const handleClearValueFilter = useCallback(() => {
    setFilter(prev => ({
      ...prev,
      filterByValue: { enabled: false }
    }));
    setValueFilterMin('');
    setValueFilterMax('');
  }, []);

  // Toggle dots visibility
  const handleToggleDots = useCallback(() => {
    setDotsVisible(prev => !prev);
  }, []);

  if (!processedData || processedData.length === 0) {
    return (
      <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" height="100%">
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {filter.excludedRounds.size > 0 || filter.filterByValue.enabled
            ? 'No data points match current filters'
            : `No data available for ${title}`
          }
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {filter.excludedRounds.size > 0 || filter.filterByValue.enabled
            ? 'Try adjusting your filters to show more data'
            : 'Data will appear here once training begins'
          }
        </Typography>
        {(filter.excludedRounds.size > 0 || filter.filterByValue.enabled) && (
          <Button
            size="small"
            onClick={handleRestoreAll}
            startIcon={<RestoreIcon />}
            sx={{ mt: 1 }}
          >
            Clear All Filters
          </Button>
        )}
      </Box>
    );
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const value = payload[0].value;
      const dataPoint = payload[0].payload;
      const isExcluded = filter.excludedRounds.has(dataPoint.round);
      
      return (
        <Box
          sx={{
            backgroundColor: 'rgba(255,255,255,0.95)',
            border: '1px solid #ccc',
            borderRadius: 1,
            p: 1,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
          }}
        >
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            Round {label} {isExcluded && '(Excluded)'}
          </Typography>
          <Typography variant="body2" color="primary">
            {yAxisLabel || dataKey}: {formatter(value)}
          </Typography>
          {enableDataPointRemoval && (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
              Click to {isExcluded ? 'include' : 'exclude'} this point
            </Typography>
          )}
        </Box>
      );
    }
    return null;
  };

  const handleDataPointClick = useCallback((data: any) => {
    if (enableDataPointRemoval && data && data.round) {
      toggleDataPoint(data.round);
    }
  }, [enableDataPointRemoval, toggleDataPoint]);

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header with trend info and controls */}
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="h6" sx={{ fontWeight: 500, color: 'text.primary' }}>
          {title}
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {/* Zoom controls */}
          {zoomDomain && (
            <MuiTooltip title="Reset zoom (or use Ctrl+Mouse Wheel to zoom)">
              <IconButton
                size="small"
                onClick={handleResetZoom}
                sx={{ 
                  color: 'primary.main',
                  '&:hover': { backgroundColor: 'rgba(0,0,0,0.04)' }
                }}
              >
                <RestoreIcon />
              </IconButton>
            </MuiTooltip>
          )}

          {/* Dot visibility toggle */}
          {enableDotToggle && (
            <MuiTooltip title={dotsVisible ? 'Hide dots for smoother line' : 'Show data point dots'}>
              <IconButton
                size="small"
                onClick={handleToggleDots}
                sx={{ 
                  color: dotsVisible ? 'primary.main' : 'text.secondary',
                  '&:hover': { backgroundColor: 'rgba(0,0,0,0.04)' }
                }}
              >
                {dotsVisible ? <DotsIcon /> : <SmoothLineIcon />}
              </IconButton>
            </MuiTooltip>
          )}

          {/* Filter status indicators */}
          {filter.excludedRounds.size > 0 && (
            <Badge badgeContent={filter.excludedRounds.size} color="warning">
              <Chip
                label="Points Excluded"
                color="warning"
                size="small"
                variant="outlined"
                icon={<VisibilityOffIcon />}
              />
            </Badge>
          )}
          
          {filter.filterByValue.enabled && (
            <Chip
              label="Value Filter"
              color="info"
              size="small"
              variant="outlined"
              icon={<FilterListIcon />}
            />
          )}

          {/* Trend info */}
          {showTrend && trendInfo && (
            <>
              <Chip
                label={`${trendInfo.improvementPercent >= 0 ? '+' : ''}${trendInfo.improvementPercent.toFixed(1)}%`}
                color={trendInfo.direction === 'up' ? 'success' : 'error'}
                size="small"
                variant="outlined"
              />
              <Typography variant="caption" color="text.secondary">
                Latest: {formatter(trendInfo.latest)}
              </Typography>
            </>
          )}

          {/* Chart controls menu */}
          {(enableDataPointRemoval || enableDotToggle) && (
            <MuiTooltip title="Chart Options">
              <IconButton
                size="small"
                onClick={(e) => setMenuAnchor(e.currentTarget)}
              >
                <MoreVertIcon />
              </IconButton>
            </MuiTooltip>
          )}
        </Box>
      </Box>

      {/* Zoom instructions */}
      {!zoomDomain && (
        <Typography variant="caption" color="text.secondary" sx={{ mb: 1, textAlign: 'center' }}>
          Hold Ctrl + Mouse Wheel to zoom • Click and drag on chart to pan
        </Typography>
      )}

      {/* Chart */}
      <Box 
        ref={chartRef}
        sx={{ 
          flex: 1, 
          minHeight: 250,
          cursor: isZooming ? 'zoom-in' : 'default',
          '&:hover': {
            '& .recharts-surface': {
              cursor: 'crosshair'
            }
          }
        }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={processedData}
            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.1)" />
            <XAxis 
              dataKey="round"
              tick={{ fontSize: 12 }}
              stroke="#666"
              label={{ value: 'Round', position: 'insideBottom', offset: -5, style: { textAnchor: 'middle' } }}
              domain={zoomDomain?.x || ['dataMin', 'dataMax']}
              type="number"
              scale="linear"
            />
            <YAxis
              dataKey={dataKey}
              axisLine={false}
              tickLine={false}
              tick={{ fill: '#6c757d', fontSize: 12 }}
              domain={zoomDomain?.y || ['auto', 'auto']}
              width={80}
              tickFormatter={yAxisTickFormatter}
            />
            <Tooltip content={<CustomTooltip />} />
            
            {/* Reference line for best value */}
            {trendInfo && (
              <ReferenceLine 
                y={trendInfo.best} 
                stroke={color} 
                strokeDasharray="5 5" 
                strokeOpacity={0.5}
                label={{ value: `Best: ${formatter(trendInfo.best)}`, position: 'top' }}
              />
            )}
            
            {/* Main data line */}
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot={dotsVisible ? { 
                fill: color, 
                strokeWidth: 2, 
                r: 4,
                cursor: enableDataPointRemoval ? 'pointer' : 'default'
              } : false}
              activeDot={dotsVisible ? { 
                r: 6, 
                stroke: color, 
                strokeWidth: 2,
                cursor: enableDataPointRemoval ? 'pointer' : 'default',
                onClick: handleDataPointClick
              } : {
                r: 6, 
                stroke: color, 
                strokeWidth: 2,
                fill: color,
                cursor: enableDataPointRemoval ? 'pointer' : 'default',
                onClick: handleDataPointClick
              }}
            />
            
            {/* Excluded data points overlay (if showing excluded) */}
            {filter.showExcluded && excludedData.length > 0 && (
              <Line
                type="monotone"
                dataKey={dataKey}
                data={excludedData}
                stroke="rgba(255,0,0,0.3)"
                strokeWidth={1}
                strokeDasharray="3 3"
                dot={dotsVisible ? { 
                  fill: 'rgba(255,0,0,0.5)', 
                  strokeWidth: 1, 
                  r: 3,
                  cursor: 'pointer'
                } : false}
                activeDot={{ 
                  r: 5, 
                  stroke: 'red', 
                  strokeWidth: 2,
                  cursor: 'pointer',
                  onClick: handleDataPointClick
                }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </Box>

      {/* Chart Options Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={() => setMenuAnchor(null)}
      >
        {enableDotToggle && (
          <MenuItem onClick={handleToggleDots}>
            {dotsVisible ? <SmoothLineIcon sx={{ mr: 1 }} /> : <DotsIcon sx={{ mr: 1 }} />}
            {dotsVisible ? 'Hide Dots (Smooth Line)' : 'Show Dots'}
          </MenuItem>
        )}
        {enableDotToggle && enableDataPointRemoval && <Divider />}
        {enableDataPointRemoval && (
          <>
            <MenuItem onClick={() => setFilterDialogOpen(true)}>
              <FilterListIcon sx={{ mr: 1 }} />
              Value Filter
            </MenuItem>
            <MenuItem onClick={handleExcludeOutliers}>
              <DeleteIcon sx={{ mr: 1 }} />
              Exclude Outliers
            </MenuItem>
            <MenuItem onClick={() => setFilter(prev => ({ ...prev, showExcluded: !prev.showExcluded }))}>
              {filter.showExcluded ? <VisibilityOffIcon sx={{ mr: 1 }} /> : <VisibilityIcon sx={{ mr: 1 }} />}
              {filter.showExcluded ? 'Hide' : 'Show'} Excluded Points
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleRestoreAll} disabled={filter.excludedRounds.size === 0 && !filter.filterByValue.enabled}>
              <RestoreIcon sx={{ mr: 1 }} />
              Restore All Points
            </MenuItem>
            <MenuItem onClick={() => setFilterDialogOpen(true)}>
              <EditIcon sx={{ mr: 1 }} />
              Manage Exclusions
            </MenuItem>
          </>
        )}
      </Menu>

      {/* Filter Dialog */}
      <Dialog
        open={filterDialogOpen}
        onClose={() => setFilterDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Chart Data Filters</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            {/* Value-based filtering */}
            <Box>
              <Typography variant="subtitle1" gutterBottom>
                Filter by Value Range
              </Typography>
              <Stack direction="row" spacing={2} alignItems="center">
                <TextField
                  label="Min Value"
                  type="number"
                  size="small"
                  value={valueFilterMin}
                  onChange={(e) => setValueFilterMin(e.target.value)}
                  placeholder="No minimum"
                />
                <Typography>to</Typography>
                <TextField
                  label="Max Value"
                  type="number"
                  size="small"
                  value={valueFilterMax}
                  onChange={(e) => setValueFilterMax(e.target.value)}
                  placeholder="No maximum"
                />
              </Stack>
              {filter.filterByValue.enabled && (
                <Typography variant="caption" color="primary" sx={{ mt: 1, display: 'block' }}>
                  Active: {filter.filterByValue.min ?? 'No min'} to {filter.filterByValue.max ?? 'No max'}
                </Typography>
              )}
            </Box>

            {/* Manual data point exclusions */}
            {data && data.length > 0 && (
              <Box>
                <Typography variant="subtitle1" gutterBottom>
                  Individual Data Points ({filter.excludedRounds.size} excluded)
                </Typography>
                <Box sx={{ maxHeight: 200, overflow: 'auto', border: '1px solid #ddd', borderRadius: 1 }}>
                  <List dense>
                    {data
                      .filter(d => d.round > 0 && d[dataKey] != null && !isNaN(d[dataKey] as number))
                      .sort((a, b) => a.round - b.round)
                      .map((dataPoint) => (
                        <ListItem key={dataPoint.round} dense>
                          <ListItemText
                            primary={`Round ${dataPoint.round}`}
                            secondary={`${yAxisLabel || dataKey}: ${formatter(dataPoint[dataKey] as number)}`}
                          />
                          <ListItemSecondaryAction>
                            <Checkbox
                              checked={!filter.excludedRounds.has(dataPoint.round)}
                              onChange={() => toggleDataPoint(dataPoint.round)}
                              color="primary"
                            />
                          </ListItemSecondaryAction>
                        </ListItem>
                      ))}
                  </List>
                </Box>
              </Box>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClearValueFilter}>
            Clear Value Filter
          </Button>
          <Button onClick={handleRestoreAll}>
            Restore All
          </Button>
          <Button onClick={() => setFilterDialogOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleApplyValueFilter} variant="contained">
            Apply Value Filter
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default FLChart; 