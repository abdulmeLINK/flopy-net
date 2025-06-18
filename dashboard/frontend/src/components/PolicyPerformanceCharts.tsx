import React, { useMemo } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Paper
} from '@mui/material';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend
} from 'recharts';
import {
  Speed as SpeedIcon,
  AssessmentOutlined as AssessmentIcon
} from '@mui/icons-material';
import { PolicyDecision, PolicyMetrics } from '../services/policyApi';

interface PolicyPerformanceChartsProps {
  decisions: PolicyDecision[];
  metrics: PolicyMetrics[];
  timeRange: {
    start: string;
    end: string;
  };
}

const COLORS = {
  allow: '#4caf50',
  deny: '#f44336',
  modify: '#ff9800',
  primary: '#1976d2',
  secondary: '#dc004e',
  info: '#0288d1',
  warning: '#ed6c02',
  success: '#2e7d32'
};

export const PolicyPerformanceCharts: React.FC<PolicyPerformanceChartsProps> = ({
  decisions
}) => {// Enhanced policy execution time analysis
  const executionTimeData = useMemo(() => {
    return decisions
      .filter(d => d.execution_time !== undefined)
      .map(d => ({
        timestamp: new Date(d.timestamp).getTime(),
        execution_time: d.execution_time || 0,
        policy_name: d.policy_name || 'unknown',
        complexity: 'simple', // Default since complexity doesn't exist in PolicyDecision
        decision: d.result || d.decision || 'unknown'
      }))
      .sort((a, b) => a.timestamp - b.timestamp);
  }, [decisions]);
  // Policy type performance comparison
  const policyTypePerformance = useMemo(() => {
    const typeStats = decisions.reduce((acc, d) => {
      const type = d.policy_name || 'unknown';
      if (!acc[type]) {
        acc[type] = {
          type,
          total_decisions: 0,
          avg_execution_time: 0,
          allow_count: 0,
          deny_count: 0,
          execution_times: []
        };
      }
      
      acc[type].total_decisions++;
      if (d.execution_time) {
        acc[type].execution_times.push(d.execution_time);
      }
      
      const decision = String(d.result || d.decision || '').toLowerCase();
      if (decision === 'allow' || decision === 'allowed') {
        acc[type].allow_count++;
      } else if (decision === 'deny' || decision === 'denied') {
        acc[type].deny_count++;
      }
      
      return acc;
    }, {} as Record<string, any>);

    return Object.values(typeStats).map((stats: any) => ({
      ...stats,
      avg_execution_time: stats.execution_times.length > 0 
        ? stats.execution_times.reduce((sum: number, time: number) => sum + time, 0) / stats.execution_times.length
        : 0,
      allow_rate: (stats.allow_count / stats.total_decisions) * 100
    }));  }, [decisions]);

  // Decision trend analysis (rolling average)
  const decisionTrendData = useMemo(() => {
    if (decisions.length === 0) return [];
    
    const sortedDecisions = [...decisions].sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const windowSize = Math.max(3, Math.floor(sortedDecisions.length / 10));
    const trendData = [];

    for (let i = windowSize - 1; i < sortedDecisions.length; i++) {
      const window = sortedDecisions.slice(i - windowSize + 1, i + 1);
      const allowCount = window.filter(d => {
        const decision = String(d.result || d.decision || '').toLowerCase();
        return decision.includes('allow') || decision === 'true';
      }).length;
        const executionTimes = window
        .filter(d => d.execution_time !== undefined && d.execution_time > 0)
        .map(d => d.execution_time!);
      
      const avgExecutionTime = executionTimes.length > 0 
        ? executionTimes.reduce((sum, time) => sum + time, 0) / executionTimes.length
        : 0;

      trendData.push({
        timestamp: window[window.length - 1].timestamp,
        allow_rate: (allowCount / window.length) * 100,
        avg_execution_time: avgExecutionTime,
        window_size: windowSize,
        total_decisions: window.length
      });
    }

    return trendData;
  }, [decisions]);

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  return (
    <Grid container spacing={3}>
      {/* Policy Execution Time Trend */}
      <Grid item xs={12} lg={8}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <SpeedIcon color="primary" />
              <Typography variant="h6">Policy Execution Performance</Typography>
              <Chip 
                label={`${executionTimeData.length} data points`}
                size="small"
                color="info"
              />
            </Box>
            <Box height={350}>
              {executionTimeData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={executionTimeData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp"
                      tickFormatter={formatTimestamp}
                      domain={['dataMin', 'dataMax']}
                    />
                    <YAxis 
                      label={{ value: 'Execution Time (ms)', angle: -90, position: 'insideLeft' }}
                    />                    <RechartsTooltip 
                      formatter={(value) => [
                        `${value}ms`, 
                        'Execution Time'
                      ]}
                      labelFormatter={(timestamp) => new Date(timestamp).toLocaleString()}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="execution_time" 
                      stroke={COLORS.primary}
                      strokeWidth={2}
                      dot={{ fill: COLORS.primary, strokeWidth: 2, r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                  <Typography color="text.secondary">
                    No execution time data available
                  </Typography>
                </Box>
              )}
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Policy Type Performance Summary */}
      <Grid item xs={12} lg={4}>
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <AssessmentIcon color="secondary" />
              <Typography variant="h6">Policy Type Performance</Typography>
            </Box>
            <Box height={350} sx={{ overflow: 'auto' }}>
              {policyTypePerformance.map((typeData) => (
                <Paper 
                  key={typeData.type}
                  sx={{ p: 2, mb: 1, backgroundColor: 'grey.50' }}
                >
                  <Typography variant="subtitle2" fontWeight="bold">
                    {typeData.type.replace('_', ' ').toUpperCase()}
                  </Typography>
                  <Grid container spacing={1} mt={0.5}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Decisions
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {typeData.total_decisions}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Avg Time
                      </Typography>
                      <Typography variant="body2" fontWeight="medium">
                        {typeData.avg_execution_time.toFixed(1)}ms
                      </Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="caption" color="text.secondary">
                        Allow Rate
                      </Typography>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="body2" fontWeight="medium">
                          {typeData.allow_rate.toFixed(1)}%
                        </Typography>
                        <Chip 
                          label={typeData.allow_rate > 80 ? 'High' : typeData.allow_rate > 50 ? 'Medium' : 'Low'}
                          size="small"
                          color={typeData.allow_rate > 80 ? 'success' : typeData.allow_rate > 50 ? 'warning' : 'error'}
                        />
                      </Box>
                    </Grid>
                  </Grid>
                </Paper>
              ))}
            </Box>
          </CardContent>
        </Card>      </Grid>

      {/* Decision Trend Analysis */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Decision Trend Analysis (Rolling Average)
            </Typography>
            <Box height={300}>
              {decisionTrendData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={decisionTrendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp"
                      tickFormatter={(timestamp) => new Date(timestamp).toLocaleString()}
                    />                    <YAxis yAxisId="rate" orientation="left" domain={['dataMin', 'dataMax']} />
                    <YAxis yAxisId="time" orientation="right" domain={['dataMin', 'dataMax']} />
                    <RechartsTooltip 
                      labelFormatter={(timestamp) => new Date(timestamp).toLocaleString()}
                    />
                    <Legend />
                    <Line 
                      yAxisId="rate"
                      type="monotone" 
                      dataKey="allow_rate" 
                      stroke={COLORS.success}
                      strokeWidth={2}
                      name="Allow Rate (%)"
                    />
                    <Line 
                      yAxisId="time"
                      type="monotone" 
                      dataKey="avg_execution_time" 
                      stroke={COLORS.info}
                      strokeWidth={2}
                      name="Avg Execution Time (ms)"
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Box display="flex" justifyContent="center" alignItems="center" height="100%">
                  <Typography color="text.secondary">
                    Insufficient data for trend analysis
                  </Typography>
                </Box>
              )}
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default PolicyPerformanceCharts;
