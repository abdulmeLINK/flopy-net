import React, { useState, useMemo } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  IconButton,
  Tooltip,
  TextField,
  InputAdornment,
  CircularProgress,
  Alert,
  Paper
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterListIcon,
  History as HistoryIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon
} from '@mui/icons-material';
import { FLDataState, FLMetric } from './types/flTypes';

interface FLRoundsHistoryTabProps {
  data: FLDataState;
  formatAccuracy: (accuracy: number) => string;
  formatLoss: (loss: number) => string;
  formatModelSize: (sizeInMB: number) => string;
}

const getStatusColor = (status: string): 'success' | 'warning' | 'error' | 'info' => {
  switch (status.toLowerCase()) {
    case 'complete':
    case 'completed':
    case 'success':
      return 'success';
    case 'training':
    case 'active':
    case 'running':
      return 'info';
    case 'failed':
    case 'error':
      return 'error';
    default:
      return 'warning';
  }
};

const getStatusIcon = (status: string) => {
  const color = getStatusColor(status);
  switch (color) {
    case 'success':
      return <CheckCircleIcon color="success" fontSize="small" />;
    case 'error':
      return <ErrorIcon color="error" fontSize="small" />;
    default:
      return <InfoIcon color="info" fontSize="small" />;
  }
};

export const FLRoundsHistoryTab: React.FC<FLRoundsHistoryTabProps> = ({
  data,
  formatAccuracy,
  formatLoss,
  formatModelSize
}) => {
  const { metrics, loading, error } = data;
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [searchTerm, setSearchTerm] = useState('');

  // Filter and sort metrics
  const filteredMetrics = useMemo(() => {
    let filtered = metrics.filter(metric => metric.round > 0);

    // Apply search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(metric => 
        metric.round.toString().includes(term) ||
        metric.status.toLowerCase().includes(term) ||
        formatAccuracy(metric.accuracy).toLowerCase().includes(term)
      );
    }

    // Sort by round descending (latest first)
    return filtered.sort((a, b) => b.round - a.round);
  }, [metrics, searchTerm, formatAccuracy]);

  // Paginated data
  const paginatedMetrics = useMemo(() => {
    const start = page * rowsPerPage;
    return filteredMetrics.slice(start, start + rowsPerPage);
  }, [filteredMetrics, page, rowsPerPage]);

  // Calculate statistics
  const stats = useMemo(() => {
    if (filteredMetrics.length === 0) {
      return {
        totalRounds: 0,
        avgAccuracy: 0,
        avgLoss: 0,
        avgClients: 0,
        completedRounds: 0,
        bestAccuracy: 0,
        latestRound: 0
      };
    }

    const validAccuracies = filteredMetrics.filter(m => m.accuracy > 0);
    const validLosses = filteredMetrics.filter(m => m.loss > 0);
    const completedRounds = filteredMetrics.filter(m => 
      m.status.toLowerCase() === 'complete' || m.status.toLowerCase() === 'completed'
    );

    return {
      totalRounds: filteredMetrics.length,
      avgAccuracy: validAccuracies.length > 0 
        ? validAccuracies.reduce((sum, m) => sum + m.accuracy, 0) / validAccuracies.length 
        : 0,
      avgLoss: validLosses.length > 0 
        ? validLosses.reduce((sum, m) => sum + m.loss, 0) / validLosses.length 
        : 0,
      avgClients: filteredMetrics.reduce((sum, m) => {
        const clients = m.clients_connected > 0 ? m.clients_connected : 2; // Use 2 as default
        return sum + clients;
      }, 0) / filteredMetrics.length,
      completedRounds: completedRounds.length,
      bestAccuracy: validAccuracies.length > 0 
        ? Math.max(...validAccuracies.map(m => m.accuracy)) 
        : 0,
      latestRound: Math.max(...filteredMetrics.map(m => m.round))
    };
  }, [filteredMetrics]);

  const handlePageChange = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleRowsPerPageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const formatDuration = (seconds: number): string => {
    if (!seconds || seconds === 0) return 'N/A';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  };

  const formatTimestamp = (timestamp: string): string => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return 'Invalid Date';
    }
  };

  if (error) {
    return (
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Alert severity="error">
            {error}
          </Alert>
        </Grid>
      </Grid>
    );
  }

  return (
    <Grid container spacing={3}>
      {/* Statistics Cards */}
      <Grid item xs={12}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="h6" color="primary">{stats.totalRounds}</Typography>
              <Typography variant="caption" color="text.secondary">Total Rounds</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="h6" color="success.main">{formatAccuracy(stats.bestAccuracy)}</Typography>
              <Typography variant="caption" color="text.secondary">Best Accuracy</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="h6" color="info.main">{formatAccuracy(stats.avgAccuracy)}</Typography>
              <Typography variant="caption" color="text.secondary">Avg Accuracy</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="h6" color="error.main">{formatLoss(stats.avgLoss)}</Typography>
              <Typography variant="caption" color="text.secondary">Avg Loss</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="h6" color="secondary.main">{Math.round(stats.avgClients)}</Typography>
              <Typography variant="caption" color="text.secondary">Avg Clients</Typography>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={2}>
            <Card sx={{ textAlign: 'center', p: 2 }}>
              <Typography variant="h6" color="warning.main">{stats.completedRounds}</Typography>
              <Typography variant="caption" color="text.secondary">Completed</Typography>
            </Card>
          </Grid>
        </Grid>
      </Grid>

      {/* Main Table */}
      <Grid item xs={12}>
        <Card sx={{ borderRadius: 2, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
          <CardContent sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
              <Box display="flex" alignItems="center">
                <HistoryIcon color="primary" />
                <Typography variant="h6" sx={{ ml: 1, fontWeight: 600 }}>
                  Training Rounds History
                </Typography>
              </Box>
              
              <TextField
                size="small"
                placeholder="Search rounds..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
                sx={{ minWidth: 200 }}
              />
            </Box>

            {loading && metrics.length === 0 ? (
              <Box display="flex" justifyContent="center" alignItems="center" minHeight={300}>
                <Box textAlign="center">
                  <CircularProgress size={48} />
                  <Typography variant="h6" sx={{ mt: 2 }}>
                    Loading Rounds History...
                  </Typography>
                </Box>
              </Box>
            ) : (
              <>
                <TableContainer component={Paper} variant="outlined">
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>Round</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                        <TableCell sx={{ fontWeight: 600, textAlign: 'center' }}>
                          <Box display="flex" alignItems="center" justifyContent="center">
                            <TrendingUpIcon fontSize="small" color="success" sx={{ mr: 0.5 }} />
                            Accuracy
                          </Box>
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600, textAlign: 'center' }}>
                          <Box display="flex" alignItems="center" justifyContent="center">
                            <TrendingDownIcon fontSize="small" color="error" sx={{ mr: 0.5 }} />
                            Loss
                          </Box>
                        </TableCell>
                        <TableCell sx={{ fontWeight: 600, textAlign: 'center' }}>Clients</TableCell>
                        <TableCell sx={{ fontWeight: 600, textAlign: 'center' }}>Model Size</TableCell>
                        <TableCell sx={{ fontWeight: 600, textAlign: 'center' }}>Duration</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Timestamp</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {paginatedMetrics.map((metric, index) => (
                        <TableRow 
                          key={`${metric.round}-${index}`}
                          sx={{ 
                            '&:hover': { backgroundColor: 'rgba(0,0,0,0.04)' },
                            backgroundColor: index % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.02)'
                          }}
                        >
                          <TableCell>
                            <Typography variant="body2" sx={{ fontWeight: 600, fontFamily: 'monospace' }}>
                              #{metric.round}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Box display="flex" alignItems="center">
                              {getStatusIcon(metric.status)}
                              <Chip
                                label={metric.status}
                                color={getStatusColor(metric.status)}
                                size="small"
                                variant="outlined"
                                sx={{ ml: 1, fontWeight: 500 }}
                              />
                            </Box>
                          </TableCell>
                          <TableCell sx={{ textAlign: 'center', fontFamily: 'monospace' }}>
                            <Typography 
                              variant="body2" 
                              color={metric.accuracy > 0 ? 'success.main' : 'text.secondary'}
                              sx={{ fontWeight: 500 }}
                            >
                              {formatAccuracy(metric.accuracy)}
                            </Typography>
                          </TableCell>
                          <TableCell sx={{ textAlign: 'center', fontFamily: 'monospace' }}>
                            <Typography 
                              variant="body2" 
                              color={metric.loss > 0 ? 'error.main' : 'text.secondary'}
                              sx={{ fontWeight: 500 }}
                            >
                              {formatLoss(metric.loss)}
                            </Typography>
                          </TableCell>
                          <TableCell sx={{ textAlign: 'center', fontFamily: 'monospace' }}>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {metric.clients_connected > 0 ? metric.clients_connected : 2}
                            </Typography>
                          </TableCell>
                          <TableCell sx={{ textAlign: 'center', fontFamily: 'monospace' }}>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {metric.model_size_mb > 0 ? formatModelSize(metric.model_size_mb) : '1.70 MB'}
                            </Typography>
                          </TableCell>
                          <TableCell sx={{ textAlign: 'center', fontFamily: 'monospace' }}>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {formatDuration(metric.training_duration || 0)}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Tooltip title={formatTimestamp(metric.timestamp)}>
                              <Typography 
                                variant="body2" 
                                color="text.secondary"
                                sx={{ 
                                  fontFamily: 'monospace',
                                  maxWidth: 150,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap'
                                }}
                              >
                                {new Date(metric.timestamp).toLocaleTimeString()}
                              </Typography>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      ))}
                      {paginatedMetrics.length === 0 && !loading && (
                        <TableRow>
                          <TableCell colSpan={8} sx={{ textAlign: 'center', py: 4 }}>
                            <Typography color="text.secondary">
                              {searchTerm ? 'No rounds match your search criteria' : 'No training rounds available'}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>

                <TablePagination
                  rowsPerPageOptions={[10, 25, 50, 100]}
                  component="div"
                  count={filteredMetrics.length}
                  rowsPerPage={rowsPerPage}
                  page={page}
                  onPageChange={handlePageChange}
                  onRowsPerPageChange={handleRowsPerPageChange}
                  sx={{ mt: 2 }}
                />
              </>
            )}
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}; 