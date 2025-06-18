import { Box, Card, CardContent, Typography, Tooltip, SxProps, Theme } from '@mui/material';
import { Area, AreaChart, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis } from 'recharts';
import React from 'react';

interface MetricsCardProps {
  title: string | React.ReactNode;
  value: string | number;
  unit?: string;
  change?: {
    value: number;
    isPositive: boolean;
  };
  chartData?: Array<{
    timestamp: string;
    value: number;
  }>;
  onClick?: () => void;
  sx?: SxProps<Theme>;
}

// Define tooltip content prop types
interface TooltipContentProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    payload: {
      timestamp: string;
      [key: string]: any;
    };
  }>;
}

const MetricsCard = ({ title, value, unit, change, chartData, onClick, sx }: MetricsCardProps) => {
  // Custom tooltip component
  const CustomTooltip = ({ active, payload }: TooltipContentProps) => {
    if (active && payload && payload.length) {
      return (
        <Box sx={{ bgcolor: 'background.paper', p: 1, border: '1px solid #ccc' }}>
          <Typography variant="body2">
            {payload[0].value} {unit}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {new Date(payload[0].payload.timestamp).toLocaleString()}
          </Typography>
        </Box>
      );
    }
    return null;
  };

  // Helper function to generate a chart ID from title
  const getChartId = () => {
    if (typeof title === 'string') {
      return title.replace(/\s+/g, '-');
    }
    return 'chart';
  };

  return (
    <Card 
      sx={{ 
        height: '100%', 
        display: 'flex', 
        flexDirection: 'column',
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': {
          boxShadow: onClick ? 6 : 1
        },
        ...sx
      }} 
      onClick={onClick}
    >
      <CardContent sx={{ flexGrow: 1, pb: 1 }}>
        <Typography variant="h6" component="div" color="text.secondary" gutterBottom>
          {title}
        </Typography>
        <Box display="flex" alignItems="baseline">
          <Typography variant="h4" component="div">
            {value}
          </Typography>
          {unit && (
            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
              {unit}
            </Typography>
          )}
        </Box>

        {change && (
          <Box sx={{ mt: 1 }}>
            <Typography 
              variant="body2" 
              color={change.isPositive ? 'success.main' : 'error.main'}
            >
              {change.isPositive ? '↑' : '↓'} {Math.abs(change.value)}%
            </Typography>
          </Box>
        )}
        
        {chartData && chartData.length > 0 && (
          <Box sx={{ height: 100, mt: 2 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 5, right: 0, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id={`gradient-${getChartId()}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#8884d8" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis 
                  dataKey="timestamp" 
                  hide
                />
                <YAxis hide />
                <RechartsTooltip content={<CustomTooltip />} />
                <Area 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#8884d8" 
                  fillOpacity={1} 
                  fill={`url(#gradient-${getChartId()})`} 
                />
              </AreaChart>
            </ResponsiveContainer>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default MetricsCard; 