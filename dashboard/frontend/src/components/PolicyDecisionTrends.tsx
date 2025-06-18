import React, { useMemo } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip
} from '@mui/material';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ScatterChart,
  Scatter
} from 'recharts';
import {
  Timeline as TimelineIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Remove as StableIcon
} from '@mui/icons-material';
import { PolicyDecision } from '../services/policyApi';

interface PolicyDecisionTrendsProps {
  decisions: PolicyDecision[];
  timeRange: {
    start: string;
    end: string;
  };
}

interface TrendDataPoint {
  timestamp: string;
  hour: string;
  allowed: number;
  denied: number;
  total: number;
  denialRate: number;
  decisionIndex?: number;
  policyId?: string;
  policyName?: string;
  component?: string;
  executionTime?: number;
  isAllowed?: boolean;
  yPosition?: number;
}

interface PolicyTrendSummary {
  policy: string;
  trend: 'improving' | 'worsening' | 'stable';
  totalDecisions: number;
  currentDenialRate: number;
  previousDenialRate: number;
  change: number;
}

const PolicyDecisionTrends: React.FC<PolicyDecisionTrendsProps> = ({
  decisions
}) => {
  // Process data into individual decision points with separate Y positions
  const trendData = useMemo(() => {
    if (!decisions || !Array.isArray(decisions) || decisions.length === 0) return [];

    try {
      // Convert each decision to a chart data point with separate Y positions for allowed/denied
      const chartData: TrendDataPoint[] = decisions
        .filter(decision => decision && decision.timestamp) // Filter out invalid decisions
        .map((decision, index) => {
          const timestamp = new Date(decision.timestamp);
          if (isNaN(timestamp.getTime())) {
            console.warn('Invalid timestamp in decision:', decision);
            return null;
          }
          
          const isAllowed = decision.decision === 'allow' || decision.result === true || decision.result === 'allowed';
          
          return {
            timestamp: decision.timestamp,
            hour: timestamp.toLocaleTimeString('en-US', { 
              hour: '2-digit', 
              minute: '2-digit',
              second: '2-digit',
              hour12: false 
            }),
            allowed: isAllowed ? 1 : 0,
            denied: isAllowed ? 0 : 1,
            total: 1,
            denialRate: isAllowed ? 0 : 100,
            decisionIndex: index + 1,
            policyId: decision.policy_id || 'unknown',
            policyName: decision.policy_name || 'Unknown Policy',
            component: decision.component || 'unknown',
            executionTime: decision.execution_time || 0,
            isAllowed: isAllowed,
            yPosition: isAllowed ? 1 : 0  // Allowed at top (1), denied at bottom (0)
          };
        })
        .filter(Boolean) // Remove null entries
        .sort((a, b) => new Date(a!.timestamp).getTime() - new Date(b!.timestamp).getTime()) as TrendDataPoint[];

      return chartData;
    } catch (error) {
      console.error('Error processing decision trend data:', error);
      return [];
    }
  }, [decisions]);
  // Calculate policy-specific trends
  const policyTrends = useMemo(() => {
    if (!decisions || !Array.isArray(decisions) || decisions.length === 0) return [];

    try {
      const policyGroups = decisions.reduce((acc, decision) => {
        if (!decision) return acc;
        const key = decision.policy_id || 'unknown';
        if (!acc[key]) {
          acc[key] = [];
        }
        acc[key].push(decision);
        return acc;
      }, {} as Record<string, PolicyDecision[]>);

      const trends: PolicyTrendSummary[] = Object.entries(policyGroups).map(([policyId, policyDecisions]) => {
        if (!policyDecisions || policyDecisions.length === 0) {
          return null;
        }

        try {
          // Sort by timestamp
          const sortedDecisions = policyDecisions
            .filter(d => d && d.timestamp)
            .sort((a, b) => {
              const timeA = new Date(a.timestamp).getTime();
              const timeB = new Date(b.timestamp).getTime();
              return isNaN(timeA) || isNaN(timeB) ? 0 : timeA - timeB;
            });

          if (sortedDecisions.length === 0) return null;

          // Split into first and second half for trend calculation
          const midpoint = Math.floor(sortedDecisions.length / 2);
          const firstHalf = sortedDecisions.slice(0, midpoint);
          const secondHalf = sortedDecisions.slice(midpoint);

          const calculateDenialRate = (decisions: PolicyDecision[]) => {
            if (!decisions || decisions.length === 0) return 0;
            const denied = decisions.filter(d => 
              d && (d.decision === 'deny' || d.result === false || d.result === 'denied')
            ).length;
            return (denied / decisions.length) * 100;
          };

          const previousDenialRate = calculateDenialRate(firstHalf);
          const currentDenialRate = calculateDenialRate(secondHalf);
          const change = currentDenialRate - previousDenialRate;

          let trend: 'improving' | 'worsening' | 'stable' = 'stable';
          if (Math.abs(change) > 10) {
            trend = change < 0 ? 'improving' : 'worsening';
          }

          return {
            policy: policyDecisions[0]?.policy_name || policyId,
            trend,
            totalDecisions: policyDecisions.length,
            currentDenialRate: isNaN(currentDenialRate) ? 0 : currentDenialRate,
            previousDenialRate: isNaN(previousDenialRate) ? 0 : previousDenialRate,
            change: isNaN(change) ? 0 : change
          };
        } catch (error) {
          console.error('Error processing trend for policy:', policyId, error);
          return null;
        }
      }).filter(Boolean) as PolicyTrendSummary[];

      return trends.sort((a, b) => b.totalDecisions - a.totalDecisions);
    } catch (error) {
      console.error('Error calculating policy trends:', error);
      return [];
    }
  }, [decisions]);

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving': return <TrendingUpIcon color="success" />;
      case 'worsening': return <TrendingDownIcon color="error" />;
      default: return <StableIcon color="disabled" />;
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'improving': return 'success';
      case 'worsening': return 'error';
      default: return 'default';
    }
  };
  const customTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length > 0) {
      const data = payload[0].payload;
      if (!data) return null;
      
      const isAllowed = data.isAllowed;
      
      return (
        <Box sx={{ 
          backgroundColor: 'rgba(255, 255, 255, 0.98)', 
          border: '1px solid #ccc',
          borderRadius: 1,
          p: 2,
          boxShadow: 3,
          minWidth: 200
        }}>
          <Typography variant="body2" fontWeight="bold" sx={{ mb: 1 }}>
            Decision #{data.decisionIndex || 'N/A'}
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Time:</strong> {data.hour || 'N/A'}
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Result:</strong> 
            <Chip 
              label={isAllowed ? 'Allowed' : 'Denied'} 
              color={isAllowed ? 'success' : 'error'} 
              size="small" 
              sx={{ ml: 1, height: 20 }}
            />
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Policy:</strong> {data.policyName || 'Unknown'}
          </Typography>
          <Typography variant="body2" sx={{ mb: 0.5 }}>
            <strong>Component:</strong> {data.component || 'Unknown'}
          </Typography>
          {data.executionTime && data.executionTime > 0 && (
            <Typography variant="body2">
              <strong>Execution:</strong> {data.executionTime.toFixed(2)}ms
            </Typography>
          )}
        </Box>
      );
    }
    return null;
  };
  const renderChart = () => {
    if (!trendData.length) {
      return (
        <Box display="flex" alignItems="center" justifyContent="center" height="100%">
          <Typography variant="body2" color="text.secondary">
            No decision data to display
          </Typography>
        </Box>
      );
    }

    // Convert data to scatter format with proper X and Y coordinates
    const scatterData = trendData.map((point, index) => ({
      x: index, // Use index for X position for even spacing
      y: point.yPosition, // Use yPosition (0 for denied, 1 for allowed)
      timestamp: point.timestamp,
      hour: point.hour,
      isAllowed: point.isAllowed,
      policyName: point.policyName,
      component: point.component,
      executionTime: point.executionTime,
      decisionIndex: point.decisionIndex
    }));

    return (
      <ScatterChart 
        data={scatterData}
        margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
        width={800}
        height={400}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis 
          type="number"
          dataKey="x"
          domain={[0, Math.max(1, trendData.length - 1)]}
          tickFormatter={(value) => {
            const index = Math.floor(value);
            const dataPoint = trendData[index];
            return dataPoint ? dataPoint.hour : '';
          }}
          interval={Math.max(1, Math.floor(trendData.length / 10))}
          angle={-45}
          textAnchor="end"
          height={80}
        />
        <YAxis 
          type="number"
          dataKey="y"
          domain={[-0.2, 1.2]}
          tickFormatter={(value) => {
            if (Math.abs(value - 0) < 0.1) return 'Denied';
            if (Math.abs(value - 1) < 0.1) return 'Allowed';
            return '';
          }}
          ticks={[0, 1]}
        />
        <Tooltip content={customTooltip} />
        <Legend />
        {/* Allowed decisions */}
        <Scatter 
          dataKey="y"
          data={scatterData.filter(d => d.isAllowed)}
          fill="#4caf50"
          name="Allowed"
        />
        {/* Denied decisions */}
        <Scatter 
          dataKey="y"
          data={scatterData.filter(d => !d.isAllowed)}
          fill="#f44336"
          name="Denied"
        />
      </ScatterChart>
    );
  };

  if (!decisions.length) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TimelineIcon color="primary" />
            Policy Decision Trends Over Time
          </Typography>
          <Typography color="text.secondary">
            No policy decisions available for the selected time range.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box>
      <Grid container spacing={3}>
        {/* Main Trends Chart */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TimelineIcon color="primary" />
                  Policy Decision Trends Over Time
                </Typography>
                
                <Box display="flex" gap={2} alignItems="center">
                  <Typography variant="body2" color="text.secondary">
                    Individual policy decisions shown chronologically
                  </Typography>
                </Box>
              </Box>

              <Box height={400}>
                <ResponsiveContainer width="100%" height="100%">
                  {renderChart()}
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Policy-Specific Trends */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Policy Trend Summary
              </Typography>
              <Grid container spacing={2}>
                {policyTrends.slice(0, 6).map((trend, index) => (
                  <Grid item xs={12} md={6} lg={4} key={index}>
                    <Box p={2} border={1} borderColor="divider" borderRadius={1}>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                        <Typography variant="subtitle2" noWrap>
                          {trend.policy}
                        </Typography>
                        <Box display="flex" alignItems="center" gap={0.5}>
                          {getTrendIcon(trend.trend)}
                          <Chip 
                            label={trend.trend} 
                            color={getTrendColor(trend.trend) as any}
                            size="small"
                          />
                        </Box>
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary">
                        {trend.totalDecisions} total decisions
                      </Typography>
                      
                      <Box display="flex" justifyContent="space-between" mt={1}>
                        <Typography variant="body2">
                          Current: {trend.currentDenialRate.toFixed(1)}% denied
                        </Typography>
                        <Typography 
                          variant="body2" 
                          color={trend.change > 0 ? 'error' : trend.change < 0 ? 'success' : 'text.secondary'}
                        >
                          {trend.change > 0 ? '+' : ''}{trend.change.toFixed(1)}%
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default PolicyDecisionTrends; 