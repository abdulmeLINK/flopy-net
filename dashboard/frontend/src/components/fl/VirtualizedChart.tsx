import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  ToggleButtonGroup,
  ToggleButton,
  Tooltip,
  IconButton,
  Chip,
  Button,
  ButtonGroup,
  Pagination,
  TextField,
  Stack
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { 
  Timeline,
  ZoomIn,
  ZoomOut,
  CenterFocusStrong,
  FirstPage,
  LastPage,
  NavigateBefore,
  NavigateNext,
  Home,
  Search
} from '@mui/icons-material';

// Simplified FL metric interface
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

interface VirtualizedChartProps {
  data: FLMetric[];
  title: string;
  dataKey: string;
  color: string;
  yAxisLabel?: string;
  formatter?: (value: number) => string;
  onZoomChange?: (startIndex?: number, endIndex?: number) => void;
  onDataRequest?: (startRound: number, endRound: number) => Promise<FLMetric[]>;
  showZoomControls?: boolean;
  showPagination?: boolean;
}

const VirtualizedChart: React.FC<VirtualizedChartProps> = ({
  data,
  title,
  dataKey,
  color,
  yAxisLabel,
  formatter,
  onDataRequest,
  showZoomControls = true,
  showPagination = true
}) => {
  const [xAxisType, setXAxisType] = useState<'time' | 'round'>('round');
  const [loading, setLoading] = useState(false);
  const [jumpToRound, setJumpToRound] = useState<string>('');

  const chartContainerRef = useRef<HTMLDivElement>(null);

  // Calculate available data range
  const dataRange = useMemo(() => {
    console.log('[VirtualizedChart] Input data length:', data.length);
    if (data.length > 0) {
      console.log('[VirtualizedChart] Sample input data[0]:', data[0]);
    }
    if (data.length === 0) return { min: 1, max: 100 }; // Default if no data
    const rounds = data.map(d => d.round).filter(r => typeof r === 'number' && r > 0);
    if (rounds.length === 0) return { min: 1, max: 100 }; // Default if no valid rounds
    const minRound = Math.min(...rounds);
    const maxRound = Math.max(...rounds);
    console.log('[VirtualizedChart] Calculated dataRange:', { min: minRound, max: maxRound });
    return { min: minRound, max: maxRound };
  }, [data]);

  const [viewWindow, setViewWindow] = useState({ start: dataRange.min, end: dataRange.max });

  useEffect(() => {
    // Initialize or update viewWindow when dataRange changes (e.g., initial data load)
    console.log('[VirtualizedChart] useEffect updating viewWindow. Current dataRange:', dataRange, 'Setting viewWindow to:', { start: dataRange.min, end: dataRange.max });
    setViewWindow({ start: dataRange.min, end: dataRange.max });
  }, [dataRange]);

  // Process data for current viewWindow
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];
    
    // Filter data to current viewWindow range
    const windowData = data.filter(item => 
      item.round >= viewWindow.start && item.round <= viewWindow.end && item.round > 0
    );
    
    // Sort and validate data
    const sortedData = windowData.sort((a, b) => a.round - b.round);
    
    // Filter out invalid data points
    const validData = sortedData.filter(item => {
      const value = item[dataKey as keyof FLMetric] as number;
      return (
        item.round > 0 && 
        typeof value === 'number' && 
        !isNaN(value) && 
        isFinite(value) &&
        value !== null &&
        value !== undefined
      );
    });
    
    if (validData.length === 0) return [];
    
    // Process data with proper formatting and time handling
    return validData.map((item, index) => {
      let timestamp;
      try {
        // Handle various timestamp formats
        if (typeof item.timestamp === 'string') {
          timestamp = new Date(item.timestamp);
          if (isNaN(timestamp.getTime())) {
            const unixSeconds = parseInt(item.timestamp);
            if (!isNaN(unixSeconds)) {
              timestamp = new Date(unixSeconds * 1000);
            }
          }
        } else if (typeof item.timestamp === 'number') {
          timestamp = item.timestamp > 1e10 
            ? new Date(item.timestamp) 
            : new Date(item.timestamp * 1000);
        } else {
          // Fallback: create a synthetic timestamp based on round number
          const baseTime = new Date('2024-01-01T00:00:00Z').getTime();
          const roundOffset = (item.round - viewWindow.start) * 60000; // 1 minute per round
          timestamp = new Date(baseTime + roundOffset);
        }
        
        if (isNaN(timestamp.getTime())) {
          const baseTime = new Date().getTime() - (validData.length - index) * 60000;
          timestamp = new Date(baseTime);
        }
      } catch (error) {
        const baseTime = new Date().getTime() - (validData.length - index) * 60000;
        timestamp = new Date(baseTime);
      }
      
      const value = Number(item[dataKey as keyof FLMetric]);
      
      return {
        ...item,
        index,
        timeValue: timestamp.getTime(),
        formattedTime: timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        formattedDateTime: timestamp.toLocaleString(),
        [dataKey]: value,
        displayValue: formatter ? formatter(value) : value.toString()
      };
    });
  }, [data, viewWindow, dataKey, formatter]);

  // Calculate Y-axis domain with proper padding
  const yAxisDomain = useMemo(() => {
    if (!processedData.length) return ['dataMin', 'dataMax'];

    const values = processedData
      .map(d => d[dataKey as keyof typeof d] as number)
      .filter(v => typeof v === 'number' && !isNaN(v) && isFinite(v));
    
    if (values.length === 0) return [0, 1];

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min;
    
    // Smart domain calculation based on data type
    if (dataKey === 'accuracy') {
      const padding = Math.max(0.05, range * 0.1);
      return [Math.max(0, min - padding), Math.min(1, max + padding)];
    } else if (dataKey === 'loss') {
      const padding = range * 0.15;
      return [Math.max(0, min - padding), max + padding];
    } else {
      const padding = Math.max(1, range * 0.1);
      return [Math.max(0, min - padding), max + padding];
    }
  }, [processedData, dataKey]);

  // Y-axis formatter
  const yAxisFormatter = useCallback((value: number) => {
    if (typeof value !== 'number' || !isFinite(value)) return '0';
    
    if (dataKey === 'accuracy') {
      const percentage = value * 100;
      return `${percentage.toFixed(1)}%`;
    } else if (dataKey === 'loss') {
      if (value === 0) return '0';
      if (value >= 1) return value.toFixed(2);
      if (value >= 0.01) return value.toFixed(3);
      if (value >= 0.001) return value.toFixed(4);
      return value.toExponential(2);
    } else if (dataKey === 'clients_connected') {
      return Math.round(value).toString();
    } else if (dataKey === 'model_size_mb') {
      if (value === 0) return '0';
      if (value >= 100) return `${value.toFixed(0)}MB`;
      if (value >= 10) return `${value.toFixed(1)}MB`;
      return `${value.toFixed(2)}MB`;
    } else {
      if (value === 0) return '0';
      if (Math.abs(value) >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
      if (Math.abs(value) >= 1000) return `${(value / 1000).toFixed(1)}K`;
      if (Math.abs(value) >= 10) return value.toFixed(1);
      if (Math.abs(value) >= 1) return value.toFixed(2);
      return value.toFixed(3);
    }
  }, [dataKey]);

  // X-axis configuration
  const xAxisConfig = useMemo(() => {
    if (xAxisType === 'round') {
      const rangeSize = viewWindow.end - viewWindow.start + 1;
      let tickInterval = Math.max(1, Math.ceil(rangeSize / 6));
      
      const ticks = [];
      if (rangeSize > 0) {
        for (let i = viewWindow.start; i <= viewWindow.end; i += tickInterval) {
          ticks.push(i);
        }
        if (ticks.length > 1 && ticks[ticks.length - 1] < viewWindow.end && viewWindow.end - ticks[ticks.length - 1] < tickInterval / 2) {
          ticks[ticks.length -1] = viewWindow.end;
        } else if (ticks[ticks.length - 1] !== viewWindow.end) {
           ticks.push(viewWindow.end);
        }
        if (ticks.length === 0 || (ticks.length > 0 && ticks[0] > viewWindow.start)) {
            ticks.unshift(viewWindow.start);
        }
      } else if (rangeSize === 1) {
        ticks.push(viewWindow.start);
      }
      
      return {
        dataKey: 'round',
        type: 'number' as const,
        domain: [viewWindow.start, viewWindow.end],
        ticks: ticks.filter((t, i, arr) => arr.indexOf(t) === i).slice(0,7),
        tickFormatter: (value: number) => `R${Math.round(value)}`,
        allowDataOverflow: false,
        scale: 'linear' as const,
        interval: 0
      };
    } else {
      if (processedData.length === 0) {
        return {
          dataKey: 'timeValue',
          type: 'number' as const,
          domain: ['dataMin', 'dataMax'],
          scale: 'time' as const,
          tickCount: 5,
          tickFormatter: () => '',
          allowDataOverflow: false
        };
      }
      
      const minTime = processedData[0].timeValue;
      const maxTime = processedData[processedData.length - 1].timeValue;
      const timeSpan = maxTime - minTime;
      
      let tickFormatter;
      if (timeSpan < 30 * 60 * 1000) {
        tickFormatter = (timestamp: number) => 
          new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } else if (timeSpan < 24 * 60 * 60 * 1000) {
        tickFormatter = (timestamp: number) => 
          new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } else {
        tickFormatter = (timestamp: number) => 
          new Date(timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' });
      }
      
      return {
        dataKey: 'timeValue',
        type: 'number' as const,
        domain: [minTime, maxTime],
        scale: 'time' as const,
        tickCount: 5,
        tickFormatter,
        allowDataOverflow: false,
        tick: { fontSize: 10, angle: -30, textAnchor: 'end' }
      };
    }
  }, [xAxisType, viewWindow, processedData]);

  const handleJumpToRound = useCallback(() => {
    const targetRound = parseInt(jumpToRound);
    if (!isNaN(targetRound) && targetRound >= dataRange.min && targetRound <= dataRange.max) {
      // Adjust viewWindow to center on the targetRound, or simply jump if it's too complex initially
      // For now, let's set the view to a window around the targetRound
      const windowSize = viewWindow.end - viewWindow.start; // Maintain current window size
      let newStart = Math.max(dataRange.min, targetRound - Math.floor(windowSize / 2));
      let newEnd = Math.min(dataRange.max, newStart + windowSize);
      // Adjust if newEnd pushes newStart out of bounds
      if (newEnd === dataRange.max) {
        newStart = Math.max(dataRange.min, newEnd - windowSize);
      }
      setViewWindow({ start: newStart, end: newEnd });
      setJumpToRound('');
    }
  }, [jumpToRound, dataRange, viewWindow, setViewWindow]);

  // Shared zoom/pan logic helper
  const updateViewWindow = (
    prev: { start: number; end: number },
    direction: -1 | 1, // -1 for zoom-in/pan-left, 1 for zoom-out/pan-right
    mode: 'zoom' | 'pan',
    factor: number,
    dataRange: { min: number; max: number },
    zoomCenterDataValue?: number
  ): { start: number; end: number } => {
    let newStart = prev.start;
    let newEnd = prev.end;
    const currentSpan = Math.max(0, prev.end - prev.start);

    if (mode === 'zoom') {
      const center = zoomCenterDataValue !== undefined ? zoomCenterDataValue : prev.start + currentSpan / 2;
      let targetSpan;

      if (direction === -1) { // Zoom In
        if (currentSpan === 0) return prev; // Already at max zoom
        targetSpan = currentSpan * (1 - factor);
        if (targetSpan < 1) targetSpan = 0; // Zoom to single point if span gets too small
      } else { // Zoom Out
        if (currentSpan >= (dataRange.max - dataRange.min)) return prev; // Already max unzoomed

        if (currentSpan === 0) { // Zooming out from a single point
          targetSpan = Math.max(Math.min(10, dataRange.max - dataRange.min), 
                                Math.floor((dataRange.max - dataRange.min) * 0.05));
          if (targetSpan <=0 && dataRange.max > dataRange.min) targetSpan = 1; // Ensure at least a 2-point window (span of 1)
        } else {
          targetSpan = currentSpan * (1 + factor);
        }
        targetSpan = Math.min(targetSpan, dataRange.max - dataRange.min);
      }

      newStart = Math.round(center - targetSpan / 2);
      newEnd = newStart + Math.round(targetSpan); // end is start + span
    
    } else { // Pan
      if (currentSpan === 0 && (dataRange.max - dataRange.min > 0)) {
        // Optionally, disallow panning a single point or reset view. For now, just return.
        return prev; 
      } else if (currentSpan === 0) return prev; // No range to pan
      
      const panAmount = Math.max(1, Math.round(currentSpan * factor));
      if (direction === -1) { // Pan Left
        newStart = prev.start - panAmount;
        newEnd = prev.end - panAmount;
      } else { // Pan Right
        newStart = prev.start + panAmount;
        newEnd = prev.end + panAmount;
      }
    }

    // Clamp to dataRange boundaries
    newStart = Math.max(dataRange.min, newStart);
    newEnd = Math.min(dataRange.max, newEnd);

    // Ensure start <= end. If clamping made end < start, adjust.
    if (newEnd < newStart) {
      if (mode === 'pan' && direction === -1) { // Panned left too far
        newEnd = newStart; // or newStart = newEnd - currentSpan, then re-clamp newStart
      } else if (mode === 'pan' && direction === 1) { // Panned right too far
        newStart = newEnd;
      } else { // Zoom might have inverted it
        newEnd = newStart; // Default to a single point if zoom logic fails badly
      }
    }
    
    // If mode is pan, try to maintain the window span after clamping
    if (mode === 'pan') {
        if (direction === -1) { // Panning Left
            newEnd = Math.min(dataRange.max, newStart + currentSpan);
        } else { // Panning Right
            newStart = Math.max(dataRange.min, newEnd - currentSpan);
        }
         // Re-clamp after span preservation
        newStart = Math.max(dataRange.min, newStart);
        newEnd = Math.min(dataRange.max, newEnd);
        if (newEnd < newStart) newEnd = newStart; // Final check
    }

    // Final check: if it resulted in a single point but data range is larger, and we were zooming out.
    if (mode === 'zoom' && direction === 1 && newStart === newEnd && currentSpan === 0 && (dataRange.max - dataRange.min > 0)) {
        if (newStart === dataRange.min) newEnd = Math.min(dataRange.max, newStart + 1);
        else newStart = Math.max(dataRange.min, newEnd - 1);
    }
    // Ensure at least a single point span if start becomes greater than end somehow
    if (newStart > newEnd) newEnd = newStart;

    return { start: newStart, end: newEnd };
  };

  // Keyboard and Wheel navigation
  useEffect(() => {
    const chartElement = chartContainerRef.current;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (!data || data.length === 0) return;
      let preventDefault = true; // Default to preventing, unless unhandled
      const zoomFactor = 0.1;
      const panFactor = 0.1;

      switch (event.key) {
        case '+':
        case 'ArrowUp':
          setViewWindow(prev => updateViewWindow(prev, -1, 'zoom', zoomFactor, dataRange));
          break;
        case '-':
        case 'ArrowDown':
          setViewWindow(prev => updateViewWindow(prev, 1, 'zoom', zoomFactor, dataRange));
          break;
        case 'ArrowLeft':
          setViewWindow(prev => updateViewWindow(prev, -1, 'pan', panFactor, dataRange));
          break;
        case 'ArrowRight':
          setViewWindow(prev => updateViewWindow(prev, 1, 'pan', panFactor, dataRange));
          break;
        default:
          preventDefault = false; // Don't prevent default for unhandled keys
          break;
      }
      if (preventDefault) event.preventDefault();
    };

    const handleWheel = (event: WheelEvent) => {
      if (!data || data.length === 0 || !chartElement || !chartElement.contains(event.target as Node)) return;
      event.preventDefault();
      const zoomFactor = 0.1;
      const direction = event.deltaY < 0 ? -1 : 1;

      // Calculate zoom center based on cursor position
      let zoomCenterDataValue: number | undefined = undefined;
      if (chartElement) {
        const rect = chartElement.getBoundingClientRect();
        // This gets cursor position relative to the chart container, not necessarily the plot area.
        // For simplicity, we'll use it. A more accurate way involves knowing plot area offsets.
        const mouseX = event.clientX - rect.left;
        const chartWidth = rect.width; // Assuming chart plot area takes most of the width
        
        if (chartWidth > 0) {
          const relativeMouseX = mouseX / chartWidth;
          const currentSpan = viewWindow.end - viewWindow.start;
          zoomCenterDataValue = viewWindow.start + (currentSpan * relativeMouseX);
          
          // If time axis, need to ensure zoomCenterDataValue is also a time value if different logic path used.
          // For now, this assumes round-based numeric calculation is fine for both.
        }
      }

      setViewWindow(prev => updateViewWindow(prev, direction, 'zoom', zoomFactor, dataRange, zoomCenterDataValue));
    };

    document.addEventListener('keydown', handleKeyDown);
    if (chartElement) chartElement.addEventListener('wheel', handleWheel, { passive: false });
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (chartElement) chartElement.removeEventListener('wheel', handleWheel);
    };
  }, [data, dataRange, viewWindow, setViewWindow, updateViewWindow]); // Added updateViewWindow to dependencies

  const handleXAxisChange = useCallback((
    event: React.MouseEvent<HTMLElement>,
    newXAxisType: 'time' | 'round'
  ) => {
    if (newXAxisType !== null) {
      setXAxisType(newXAxisType);
    }
  }, []);

  const tooltipFormatter = useCallback((value: any, name: string) => {
    if (typeof value === 'number' && !isNaN(value)) {
      return [formatter ? formatter(value) : yAxisFormatter(value), name];
    }
    return [value, name];
  }, [formatter, yAxisFormatter]);

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header with controls */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          {title}
        </Typography>
        
        {showZoomControls && (
          <Stack direction="row" spacing={1} alignItems="center">
            {/* X-axis type toggle */}
            <ToggleButtonGroup
              value={xAxisType}
              exclusive
              onChange={handleXAxisChange}
              size="small"
            >
              <ToggleButton value="round">
                <Tooltip title="Show by round number">
                  <Typography variant="body2">Rounds</Typography>
                </Tooltip>
              </ToggleButton>
              <ToggleButton value="time">
                <Tooltip title="Show by time">
                  <Timeline />
                </Tooltip>
              </ToggleButton>
            </ToggleButtonGroup>

            {/* Jump to round */}
            <TextField
              size="small"
              placeholder="Round"
              value={jumpToRound}
              onChange={(e) => setJumpToRound(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleJumpToRound()}
              sx={{ width: 80 }}
            />
            <IconButton size="small" onClick={handleJumpToRound}>
              <Search />
            </IconButton>
          </Stack>
        )}
      </Box>

      {/* Chart */}
      <Box sx={{ flex: 1, minHeight: 300 }} ref={chartContainerRef}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={processedData} margin={{ top: 5, right: 30, left: 20, bottom: 60 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
            <XAxis {...xAxisConfig} />
            <YAxis 
              domain={yAxisDomain}
              tickFormatter={yAxisFormatter}
              label={{ value: yAxisLabel, angle: -90, position: 'insideLeft' }}
            />
            <RechartsTooltip
              formatter={tooltipFormatter}
              labelFormatter={(label) => 
                xAxisType === 'round' ? `Round ${label}` : new Date(label).toLocaleString()
              }
              contentStyle={{
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                border: '1px solid #ccc',
                borderRadius: '4px'
              }}
            />
            <Line 
              type="monotone" 
              dataKey={dataKey} 
              stroke={color} 
              strokeWidth={2}
              dot={{ fill: color, strokeWidth: 2, r: 3 }}
              activeDot={{ r: 5, fill: color }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>

      {/* Footer with pagination and controls - MODIFY TO REMOVE PAGINATION */}
      {showPagination && ( // This prop might be re-evaluated; for now, we keep the footer for other controls.
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2, px:1 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography variant="body2" color="text.secondary">
              Rounds {viewWindow.start}-{viewWindow.end} of {dataRange.min}-{dataRange.max}
            </Typography>
            <Chip 
              size="small" 
              label={`${processedData.length} points displayed`} 
              variant="outlined"
            />
          </Stack>
          
          <Stack direction="row" spacing={2} alignItems="center">
            {/* All old pagination, page size, and navigation buttons are removed here */}
          </Stack>
        </Box>
      )}
      
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
          <Typography variant="body2" color="text.secondary">Loading...</Typography>
        </Box>
      )}
    </Box>
  );
};

export default VirtualizedChart; 