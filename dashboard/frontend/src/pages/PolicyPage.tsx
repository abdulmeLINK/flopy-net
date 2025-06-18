import { useEffect, useState } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Grid, 
  Card, 
  CardContent, 
  Button, 
  Dialog, 
  DialogActions, 
  DialogContent, 
  DialogContentText, 
  DialogTitle,
  IconButton,
  Switch,
  FormControlLabel,
  Divider,
  Tabs,
  Tab,
  Chip,
  Snackbar,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Pagination,
  CircularProgress,
  Accordion,  AccordionDetails,
  Tooltip as MuiTooltip
} from '@mui/material';
import { 
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Close as CloseIcon,
  History as HistoryIcon,
  Update as UpdateIcon,
  Visibility as ViewIcon,
  VisibilityOff as HideIcon,
  ExpandMore as ExpandMoreIcon,
  Speed as SpeedIcon,
  Security as SecurityIcon
} from '@mui/icons-material';
import { 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer 
} from 'recharts';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorAlert from '../components/common/ErrorAlert';
import DataTable from '../components/common/DataTable';
import TimeRangeSelector from '../components/common/TimeRangeSelector';
import PolicyEditor from '../components/PolicyEditor';
import PolicyDecisionDialog from '../components/PolicyDecisionDialog';
import PolicyDecisionAnalysis from '../components/PolicyDecisionAnalysis';
import PolicyDecisionTrends from '../components/PolicyDecisionTrends';
import { PolicyPerformanceCharts } from '../components/PolicyPerformanceCharts';
import { 
  getPolicies, 
  createPolicy, 
  updatePolicy, 
  deletePolicy,
  enablePolicy,
  disablePolicy,
  getPolicyDecisions,
  getPolicyMetrics,
  getPolicyEngineStatus,
  getPoliciesWithVersionCheck,
  getFreshPolicies,
  getPolicyVersion,
  Policy,
  PolicyRequest,
  PolicyDecision,
  PolicyMetrics,
  PolicyEngineStatus
} from '../services/policyApi';
import React from 'react';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

interface PolicyHistoryEntry {
  action: string;
  policy_id: string;
  policy_name: string;
  policy_type: string;
  timestamp: number;
  timestamp_readable: string;
  version: number;
  old_data?: any;
  new_data?: any;
}

interface PolicyHistoryResponse {
  history: PolicyHistoryEntry[];
  total_count: number;
  page: number;
  limit: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`policy-tabpanel-${index}`}
      aria-labelledby={`policy-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `policy-tab-${index}`,
    'aria-controls': `policy-tabpanel-${index}`,
  };
}

const PolicyPage = () => {
  const [tabValue, setTabValue] = useState(0);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [decisions, setDecisions] = useState<PolicyDecision[]>([]);
  const [metrics, setMetrics] = useState<PolicyMetrics[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<PolicyEngineStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [policyVersion, setPolicyVersion] = useState<number | null>(null);
  const [renderKey, setRenderKey] = useState(0); // Force re-render key
  const [startTime, setStartTime] = useState<string>(
    new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
  );
  const [endTime, setEndTime] = useState<string>(new Date().toISOString());
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null);
  const [selectedDecision, setSelectedDecision] = useState<PolicyDecision | null>(null);
  const [selectedPolicyRowId, setSelectedPolicyRowId] = useState<string | null>(null);
  const [selectedDecisionRowId, setSelectedDecisionRowId] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [decisionDialogOpen, setDecisionDialogOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<'create' | 'edit'>('create');
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'success'
  });

  // Policy History states
  const [historyData, setHistoryData] = useState<PolicyHistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyLimit] = useState(20);
  const [policyIdFilter, setPolicyIdFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  // Fetch all policies with version checking
  const fetchPolicies = async (forceRefresh: boolean = false) => {
    try {
      setLoading(true);
      
      if (forceRefresh) {
        // Force refresh: get fresh policies directly bypassing all cache logic
        console.log('Force refresh: fetching fresh policies...');
        const policiesData = await getFreshPolicies();
        const validPolicies = Array.isArray(policiesData) ? policiesData.filter(p => p && p.id) : [];
        setPolicies(validPolicies);
        setRenderKey(prev => prev + 1); // Force table re-render
        
        // Also get fresh version info
        try {
          const versionInfo = await getPolicyVersion();
          setPolicyVersion(versionInfo.version);
        } catch (versionErr) {
          console.warn('Failed to get policy version:', versionErr);
        }
        
        setError(null);
        console.log('Force refresh completed with', validPolicies.length, 'policies');
        return;
      }
      
      // Normal fetch with version checking for cache optimization
      const versionToCheck = policyVersion || undefined;
      
      const { policies: policiesData, version, fromCache } = await getPoliciesWithVersionCheck(undefined, versionToCheck);
      
      // Only update policies if we got new data (not from cache)
      if (!fromCache || policiesData.length > 0) {
        const validPolicies = Array.isArray(policiesData) ? policiesData.filter(p => p && p.id) : [];
        setPolicies(validPolicies);
        setRenderKey(prev => prev + 1); // Force table re-render
        
        // Log data refresh for debugging
        console.log('Policies refreshed from server, new version:', version);
      } else {
        // Cache was valid, no need to update policies
        console.log('Policies cache still valid, version:', version);
      }
      
      // Always update the version even if data came from cache
      setPolicyVersion(version);
      setError(null);
      
    } catch (err) {
      // Fallback to regular policy fetching if version checking fails
      try {
        console.warn('Version-aware fetch failed, falling back to regular fetch:', err);
        const policiesData = await getPolicies();
        const validPolicies = Array.isArray(policiesData) ? policiesData.filter(p => p && p.id) : [];
        setPolicies(validPolicies);
        setRenderKey(prev => prev + 1); // Force table re-render
        setError(null);
      } catch (fallbackErr) {
        setError('Failed to load policies. Please check the policy engine connection.');
        console.error('Error fetching policies:', fallbackErr);
        setPolicies([]);
      }
    } finally {
      setLoading(false);
    }
  };

  // Fetch connection status
  const fetchConnectionStatus = async () => {
    try {
      const status = await getPolicyEngineStatus();
      setConnectionStatus(status);
    } catch (err) {
      console.error('Error fetching connection status:', err);
      setConnectionStatus({
        connected: false,
        status: 'error',
        url: 'unknown',
        error: 'Failed to check connection'
      });
    }
  };

  // Fetch policy history
  const fetchPolicyHistory = async () => {
    try {
      setHistoryLoading(true);
      setHistoryError(null);
      
      const params = new URLSearchParams({
        limit: historyLimit.toString(),
        offset: ((historyPage - 1) * historyLimit).toString(),
      });
      
      if (policyIdFilter) {
        params.append('policy_id', policyIdFilter);
      }
      
      if (actionFilter) {
        params.append('action', actionFilter);
      }

      const response = await fetch(`/api/policy-engine/history?${params}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setHistoryData(data);
    } catch (err) {
      console.error('Error fetching policy history:', err);
      setHistoryError(err instanceof Error ? err.message : 'Failed to fetch policy history');
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
    fetchConnectionStatus();
    
    // Set up more frequent version checking (every 10 seconds) to detect policy changes quickly
    const versionCheckInterval = setInterval(() => {
      fetchPolicies(); // This will check version and only fetch if changed
    }, 10000);
    
    // Keep the longer interval for connection status
    const statusInterval = setInterval(() => {
      fetchConnectionStatus();
    }, 60000);
    
    return () => {
      clearInterval(versionCheckInterval);
      clearInterval(statusInterval);
    };
  }, [policyVersion]);

  useEffect(() => {
    if (tabValue === 4) { // Only fetch if on history tab
      fetchPolicyHistory();
    }
  }, [historyPage, policyIdFilter, actionFilter]); // Re-run when policy version changes

  // Fetch policy decisions
  useEffect(() => {
    const fetchDecisions = async () => {
      try {
        const decisionsData = await getPolicyDecisions({
          start_time: startTime,
          end_time: endTime
        });
        const validDecisions = Array.isArray(decisionsData) ? decisionsData.filter(d => d && d.timestamp) : [];
        setDecisions(validDecisions);
      } catch (err) {
        console.error('Error fetching policy decisions:', err);
        setDecisions([]);
      }
    };

    fetchDecisions();
  }, [startTime, endTime]);

  // Fetch policy metrics
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const metricsData = await getPolicyMetrics({
          start_time: startTime,
          end_time: endTime
        });
        const validMetrics = Array.isArray(metricsData) ? metricsData.filter(m => m && m.timestamp) : [];
        setMetrics(validMetrics);
      } catch (err) {
        console.error('Error fetching policy metrics:', err);
        setMetrics([]);
      }
    };

    fetchMetrics();
  }, [startTime, endTime]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    // Clear selections when switching tabs
    setSelectedPolicy(null);
    setSelectedPolicyRowId(null);
    setSelectedDecision(null);
    setSelectedDecisionRowId(null);
    
    // Fetch data for specific tabs
    if (newValue === 4) { // History tab
      fetchPolicyHistory();
    }
  };

  const handleTimeRangeChange = (start: string, end: string) => {
    setStartTime(start);
    setEndTime(end);
  };

  const handlePolicyClick = (policy: Policy) => {
    // If clicking on the same policy, deselect it
    if (selectedPolicy?.id === policy.id) {
      setSelectedPolicy(null);
      setSelectedPolicyRowId(null);
    } else {
      setSelectedPolicy(policy);
      setSelectedPolicyRowId(policy.id);
    }
  };

  const handleDecisionClick = (decision: PolicyDecision) => {
    setSelectedDecision(decision);
    setSelectedDecisionRowId(decision.id || decision.timestamp);
    setDecisionDialogOpen(true);
  };

  const handleCreatePolicy = () => {
    setSelectedPolicy(null);
    setEditorMode('create');
    setEditorOpen(true);
  };

  const handleEditPolicy = (policy: Policy) => {
    setSelectedPolicy(policy);
    setEditorMode('edit');
    setEditorOpen(true);
  };

  const handleDeleteClick = (policy: Policy) => {
    setSelectedPolicy(policy);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (selectedPolicy) {
      try {
        await deletePolicy(selectedPolicy.id);
        setSelectedPolicy(null);
        setDeleteDialogOpen(false);
        showSnackbar('Policy deleted successfully', 'success');
        // Force refresh to get the latest policy data immediately
        await fetchPolicies(true);
      } catch (err) {
        console.error('Error deleting policy:', err);
        showSnackbar('Failed to delete policy', 'error');
      }
    }
  };

  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setSelectedPolicy(null);
  };

  const handlePolicyToggle = async (policy: Policy) => {
    try {
      if (policy.status === 'active') {
        await disablePolicy(policy.id);
        showSnackbar('Policy disabled successfully', 'success');
      } else {
        await enablePolicy(policy.id);
        showSnackbar('Policy enabled successfully', 'success');
      }
      // Force refresh to get the latest policy data immediately
      await fetchPolicies(true);
    } catch (err) {
      console.error('Error toggling policy:', err);
      showSnackbar('Failed to toggle policy status', 'error');
    }
  };

  const handleSavePolicy = async (policyData: PolicyRequest) => {
    try {
      if (editorMode === 'create') {
        await createPolicy(policyData);
        showSnackbar('Policy created successfully', 'success');
      } else if (selectedPolicy) {
        await updatePolicy(selectedPolicy.id, policyData);
        showSnackbar('Policy updated successfully', 'success');
      }
      // Force refresh to get the latest policy data immediately
      await fetchPolicies(true);
      // Clear selected policy to prevent stale data
      setSelectedPolicy(null);
      setEditorOpen(false);
    } catch (err) {
      console.error('Error saving policy:', err);
      showSnackbar('Failed to save policy', 'error');
      throw err; // Re-throw to let the editor handle it
    }
  };

  const showSnackbar = (message: string, severity: 'success' | 'error' | 'warning' | 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  // Policy history helper functions
  const handleHistoryPageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setHistoryPage(value);
  };

  const getActionColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'create':
        return 'success';
      case 'update':
        return 'primary';
      case 'delete':
        return 'error';
      case 'enable':
        return 'info';
      case 'disable':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getActionIcon = (action: string) => {
    switch (action.toLowerCase()) {
      case 'create':
        return <AddIcon fontSize="small" />;
      case 'update':
        return <UpdateIcon fontSize="small" />;
      case 'delete':
        return <DeleteIcon fontSize="small" />;
      case 'enable':
        return <ViewIcon fontSize="small" />;
      case 'disable':
        return <HideIcon fontSize="small" />;
      default:
        return <HistoryIcon fontSize="small" />;
    }
  };

  const toggleRowExpansion = (entryId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(entryId)) {
      newExpanded.delete(entryId);
    } else {
      newExpanded.add(entryId);
    }
    setExpandedRows(newExpanded);
  };

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const renderPolicyData = (data: any, title: string) => {
    if (!data || Object.keys(data).length === 0) {
      return <Typography variant="body2" color="text.secondary">No data</Typography>;
    }

    return (
      <Box>
        <Typography variant="subtitle2" gutterBottom>{title}</Typography>
        <Box component="pre" sx={{ 
          fontSize: '0.75rem', 
          backgroundColor: 'grey.100', 
          p: 1, 
          borderRadius: 1,
          overflow: 'auto',
          maxHeight: '200px'
        }}>
          {JSON.stringify(data, null, 2)}
        </Box>
      </Box>
    );
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'allow':
        return 'success';
      case 'deny':
        return 'error';
      case 'modify':
        return 'warning';
      default:
        return 'default';
    }
  };
  
  // Define columns for the policies table
  const policyColumns = [
    { 
      id: 'name', 
      label: 'Name', 
      minWidth: 170,
      format: (value: any, row?: Policy) => {
        if (!row) return value || 'Unknown';
        return (
          <Box>
            <Typography variant="body2" fontWeight="medium">
              {row.name || 'Unknown'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              ID: {row.id || 'N/A'}
            </Typography>
          </Box>
        );
      }
    },
    { 
      id: 'type', 
      label: 'Type', 
      minWidth: 120,
      format: (value: any) => (
        <Chip 
          label={value || 'Unknown'} 
          variant="outlined" 
          size="small"
          color="primary"
        />
      )
    },
    { 
      id: 'status', 
      label: 'Status', 
      minWidth: 100,
      format: (value: any, row?: Policy) => {
        if (!row) {
          return (
            <Chip 
              label={value || 'Unknown'} 
              size="small"
              color="default"
            />
          );
        }
        return (
          <FormControlLabel
            control={
              <Switch
                checked={row.status === 'active'}
                onChange={() => handlePolicyToggle(row)}
                size="small"
              />
            }
            label={row.status === 'active' ? 'Active' : 'Inactive'}
            sx={{ m: 0 }}
          />
        );
      }
    },
    { 
      id: 'priority', 
      label: 'Priority', 
      minWidth: 80,
      align: 'center' as const,
      format: (value: any) => value || 0
    },
    { 
      id: 'rules', 
      label: 'Rules', 
      minWidth: 80,
      align: 'center' as const,
      format: (value: any, row?: Policy) => {
        const rulesCount = row?.rules?.length || 0;
        return (
          <Chip 
            label={rulesCount} 
            size="small"
            color={rulesCount > 0 ? 'default' : 'warning'}
          />
        );
      }
    },
    {
      id: 'actions',
      label: 'Actions',
      minWidth: 120,
      align: 'center' as const,
      format: (value: any, row?: Policy) => {
        if (!row) return null;
        return (
          <Box>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                handleEditPolicy(row);
              }}
              color="primary"
            >
              <EditIcon />
            </IconButton>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteClick(row);
              }}
              color="error"
            >
              <DeleteIcon />
            </IconButton>
          </Box>
        );
      }
    }
  ];

  // Define columns for the decisions table
  const decisionColumns = [
    { 
      id: 'timestamp', 
      label: 'Date & Time', 
      minWidth: 170,
      format: (value: any) => {
        if (!value) return 'Unknown';
        try {
          // Handle different timestamp formats
          let date: Date;
          if (typeof value === 'number') {
            // Unix timestamp (seconds or milliseconds)
            date = new Date(value < 1e12 ? value * 1000 : value);
          } else if (typeof value === 'string') {
            date = new Date(value);
          } else {
            return 'Invalid Date';
          }
          
          // Check if date is valid
          if (isNaN(date.getTime())) {
            return 'Invalid Date';
          }
          
          return date.toLocaleString('en-US', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
          });
        } catch {
          return 'Invalid Date';
        }
      }
    },
    { 
      id: 'policy_name', 
      label: 'Policy', 
      minWidth: 170,
      format: (value: any, row?: any) => {
        return (
          <Box>
            <Typography variant="body2" fontWeight="medium">
              {value || 'Unknown Policy'}
            </Typography>
            {row?.policy_id && (
              <Typography variant="caption" color="text.secondary">
                ID: {row.policy_id}
              </Typography>
            )}
            {row?.complexity && (
              <Chip 
                label={row.complexity}
                size="small"
                color={
                  row.complexity === 'simple' ? 'success' :
                  row.complexity === 'moderate' ? 'info' :
                  row.complexity === 'complex' ? 'warning' : 'error'
                }
                sx={{ mt: 0.5, fontSize: '0.7rem' }}
              />
            )}
          </Box>
        );
      }
    },
    { 
      id: 'component', 
      label: 'Component', 
      minWidth: 120,
      format: (value: any) => (
        <Chip 
          label={value || 'Unknown'} 
          variant="outlined" 
          size="small"
          color="info"
        />
      )
    },
    { 
      id: 'result', 
      label: 'Decision', 
      minWidth: 150,
      format: (value: any, row?: any) => {
        // Handle both boolean and string values
        let decision = 'unknown';
        let isAllowed = false;
          if (typeof value === 'boolean') {
          isAllowed = value;
          decision = value ? 'allow' : 'deny';
        } else if (typeof value === 'string') {
          decision = value.toLowerCase();
          isAllowed = decision === 'allowed' || decision === 'allow';
        } else if (row?.decision && typeof row.decision === 'string') {
          decision = row.decision.toLowerCase();
          isAllowed = decision === 'allow';
        }
        
        const getDecisionDetails = (decision: string) => {
          switch (decision) {
            case 'allow':
            case 'allowed':
              return { label: 'Allowed', color: 'success', icon: '✓' };
            case 'deny':
            case 'denied':
              return { label: 'Denied', color: 'error', icon: '✗' };
            case 'modify':
            case 'modified':
              return { label: 'Modified', color: 'warning', icon: '⚠' };
            default:
              return { label: 'Unknown', color: 'default', icon: '?' };
          }
        };
        
        const details = getDecisionDetails(decision);
        
        return (
          <Box display="flex" alignItems="center" gap={1}>
            <Typography sx={{ fontSize: '1.2em' }}>{details.icon}</Typography>
            <Box>
              <Chip 
                label={details.label} 
                color={details.color as any} 
                size="small"
                variant="filled"
              />
              {row?.violations && row.violations.length > 0 && (
                <Chip 
                  label={`${row.violations.length} violations`}
                  color="error"
                  size="small"
                  variant="outlined"
                  sx={{ ml: 0.5, fontSize: '0.7rem' }}
                />
              )}
            </Box>
          </Box>
        );
      }
    },
    {
      id: 'evaluation_summary',
      label: 'Evaluation Summary',
      minWidth: 200,
      format: (value: any, row?: any) => {
        if (!row) return 'No data';
        
        const rulesEvaluated = row.total_rules_evaluated || row.evaluation_details?.evaluated_rules || 0;
        const matchedRules = row.matched_rules_count || row.evaluation_details?.matched_rules || 0;
        const policiesInvolved = row.policies_involved || row.evaluation_details?.total_policies || 0;
        const actionsCount = row.actions_count || (row.applied_actions ? row.applied_actions.length : 0);
        
        return (
          <Box>
            <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
              <strong>Policies:</strong> {policiesInvolved} | <strong>Rules:</strong> {rulesEvaluated}
            </Typography>
            <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>
              <strong>Matched:</strong> {matchedRules} | <strong>Actions:</strong> {actionsCount}
            </Typography>
            {row.execution_time && (
              <Typography variant="caption" color="text.secondary">
                {row.execution_time < 1 ? '<1ms' : 
                 row.execution_time < 1000 ? `${row.execution_time.toFixed(1)}ms` : 
                 `${(row.execution_time / 1000).toFixed(2)}s`}
              </Typography>
            )}
          </Box>
        );
      }
    },
    { 
      id: 'reason', 
      label: 'Reason & Details', 
      minWidth: 300,
      format: (value: any, row?: any) => {
        const reason = value || row?.action_taken || 'No reason provided';
        const primaryAction = row?.primary_action;
        
        return (
          <Box>
            <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
              {reason}
            </Typography>
            
            {primaryAction && (
              <Chip 
                label={`Primary: ${primaryAction}`}
                size="small"
                variant="outlined"
                sx={{ mt: 0.5, fontSize: '0.7rem' }}
              />
            )}
            
            {row?.rule_evaluations && row.rule_evaluations.length > 0 && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                Evaluated {row.rule_evaluations.length} policies
              </Typography>
            )}
            
            {row?.decision_path && row.decision_path.length > 0 && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                Path: {row.decision_path.length} steps
              </Typography>
            )}
            
            {row?.context && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                Context: {typeof row.context === 'object' ? 
                  `${Object.keys(row.context).length} fields` : 
                  String(row.context).substring(0, 30) + '...'}
              </Typography>
            )}
          </Box>
        );
      }
    }
  ];

  if (loading && !policies.length) {
    return <LoadingSpinner message="Loading policy data..." />;
  }

  if (error && !policies.length) {
    return <ErrorAlert message={error} />;
  }

  // Group metrics for easier charting
  const policyCountMetrics = metrics.filter(m => m.metric_type === 'policy_count');
  const decisionCountMetrics = metrics.filter(m => m.metric_type === 'decision_count');
  // Calculate decision statistics
  const allowDecisions = decisions.filter(d => {
    const decision = d.decision?.toLowerCase() || (d.result ? String(d.result).toLowerCase() : '');
    return decision === 'allow' || decision === 'allowed' || decision === 'true';
  }).length;
  
  const denyDecisions = decisions.filter(d => {
    const decision = d.decision?.toLowerCase() || (d.result ? String(d.result).toLowerCase() : '');
    return decision === 'deny' || decision === 'denied' || decision === 'false';
  }).length;
  
  const modifyDecisions = decisions.filter(d => {
    const decision = d.decision?.toLowerCase() || '';
    return decision === 'modify' || decision === 'modified';
  }).length;

  const activePolicies = policies.filter(p => p.status === 'active').length;
  const inactivePolicies = policies.filter(p => p.status === 'inactive').length;

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ color: 'primary.main', fontWeight: 'bold' }}>
        Policy Engine
      </Typography>
      
      <Typography variant="body1" paragraph sx={{ color: 'text.secondary', fontSize: '1.1rem', mb: 4 }}>
        Monitor and manage your <strong>Policy Engine</strong> policies, decisions, and enforcement in real-time.
      </Typography>

      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center" gap={2}>
          {/* Connection Status Indicator */}
          {connectionStatus && (
            <Box display="flex" alignItems="center" gap={1}>
              <Typography variant="body2" color="text.secondary">Status:</Typography>
              <Chip 
                label={connectionStatus.connected ? 'Connected' : 'Disconnected'}
                color={connectionStatus.connected ? 'success' : 'error'}
                size="small"
                sx={{ fontWeight: 'bold' }}
              />
            </Box>
          )}
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="body2" color="text.secondary">Total:</Typography>
            <Chip 
              label={decisions.length}
              color="primary"
              size="small"
              sx={{ fontWeight: 'bold' }}
            />
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="body2" color="text.secondary">Allowed:</Typography>
            <Chip 
              label={allowDecisions}
              color="success"
              size="small"
              sx={{ fontWeight: 'bold' }}
            />
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="body2" color="text.secondary">Denied:</Typography>
            <Chip 
              label={denyDecisions}
              color="error"
              size="small"
              sx={{ fontWeight: 'bold' }}
            />
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="body2" color="text.secondary">Policies:</Typography>
            <Chip 
              label={activePolicies}
              color="info"
              size="small"
              sx={{ fontWeight: 'bold' }}
            />
          </Box>
        </Box>
        <Box>
          <IconButton 
            onClick={() => { 
              fetchPolicies(true); // Force refresh
              fetchConnectionStatus(); 
            }} 
            sx={{ mr: 1 }}
            title="Force refresh policies"
          >
            <RefreshIcon />
          </IconButton>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreatePolicy}
          >
            Create Policy
          </Button>
        </Box>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
                    <Tabs value={tabValue} onChange={handleTabChange} aria-label="policy tabs">
              <Tab label="Policies" {...a11yProps(0)} />
              <Tab label="Decisions" {...a11yProps(1)} />
              <Tab label="Analysis" {...a11yProps(2)} />
              <Tab label="Trends & Metrics" {...a11yProps(3)} />
              <Tab label="History" {...a11yProps(4)} />
            </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={selectedPolicy ? 8 : 12}>
            <DataTable
              columns={policyColumns as any}
              data={policies}
              title={`Policies (${policies.length})`}
              onRowClick={handlePolicyClick}
              getRowId={(row) => row.id}
              selectedRowId={selectedPolicyRowId}
              onRowSelect={setSelectedPolicyRowId}
              emptyMessage="No policies found. Create your first policy to get started."
              key={`policies-table-${renderKey}-${policies.length}`}
            />
          </Grid>

          {selectedPolicy && (
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, position: 'sticky', top: 20 }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">Policy Details</Typography>
                  <Box>
                    <IconButton 
                      size="small"
                      onClick={() => handleEditPolicy(selectedPolicy)}
                      color="primary"
                      sx={{ mr: 1 }}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton 
                      size="small"
                      onClick={() => handleDeleteClick(selectedPolicy)}
                      color="error"
                      sx={{ mr: 1 }}
                    >
                      <DeleteIcon />
                    </IconButton>
                    <IconButton 
                      size="small"
                      onClick={() => {
                        setSelectedPolicy(null);
                        setSelectedPolicyRowId(null);
                      }}
                      color="default"
                    >
                      <CloseIcon />
                    </IconButton>
                  </Box>
                </Box>
                
                <Divider sx={{ mb: 2 }} />
                
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">Name</Typography>
                  <Typography variant="body1">{selectedPolicy.name}</Typography>
                </Box>
                
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">ID</Typography>
                  <Typography variant="body1" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                    {selectedPolicy.id}
                  </Typography>
                </Box>
                
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">Description</Typography>
                  <Typography variant="body1">
                    {selectedPolicy.description || 'No description provided'}
                  </Typography>
                </Box>
                
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">Type</Typography>
                  <Chip 
                    label={selectedPolicy.type} 
                    variant="outlined" 
                    size="small" 
                    color="primary"
                  />
                </Box>
                
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">Priority</Typography>
                  <Typography variant="body1">{selectedPolicy.priority}</Typography>
                </Box>
                
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">Status</Typography>
                  <Chip 
                    label={selectedPolicy.status === 'active' ? 'Active' : 'Inactive'} 
                    color={selectedPolicy.status === 'active' ? 'success' : 'default'} 
                    size="small"
                  />
                </Box>

                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">Rules</Typography>
                  <Typography variant="body1">
                    {selectedPolicy.rules?.length || 0} rule(s) defined
                  </Typography>
                </Box>
                
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">Created</Typography>
                  <Typography variant="body1">
                    {selectedPolicy.created_at 
                      ? new Date(selectedPolicy.created_at).toLocaleString() 
                      : 'Unknown'}
                  </Typography>
                </Box>
                
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">Last Updated</Typography>
                  <Typography variant="body1">
                    {selectedPolicy.updated_at 
                      ? new Date(selectedPolicy.updated_at).toLocaleString() 
                      : 'Unknown'}
                  </Typography>
                </Box>
              </Paper>
            </Grid>
          )}
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <TimeRangeSelector onChange={handleTimeRangeChange} />
        
        <Box mt={3}>
          <DataTable
            columns={decisionColumns as any}
            data={decisions}
            title={`Policy Decisions (${decisions.length})`}
            onRowClick={handleDecisionClick}
            getRowId={(row) => row.id || row.timestamp}
            selectedRowId={selectedDecisionRowId}
            onRowSelect={setSelectedDecisionRowId}
            emptyMessage="No policy decisions in the selected time range"
          />
        </Box>
      </TabPanel>      <TabPanel value={tabValue} index={2}>
        <TimeRangeSelector onChange={handleTimeRangeChange} />
        
        {/* Policy Analysis Section */}
        <Box mt={3}>
          <PolicyDecisionAnalysis
            decisions={decisions}
            timeRange={{
              start: startTime,
              end: endTime
            }}
          />
        </Box>

        {/* Additional Policy Insights */}
        <Box mt={4}>
          <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
            Policy Performance Insights
          </Typography>
          
          <Grid container spacing={3}>
            {/* Policy Efficiency Metrics */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Policy Efficiency Summary
                  </Typography>
                  {(() => {
                    const totalDecisions = decisions.length;                    const avgExecutionTime = decisions
                      .filter(d => d.execution_time !== undefined)
                      .reduce((sum, d) => sum + (d.execution_time || 0), 0) / 
                      Math.max(1, decisions.filter(d => d.execution_time !== undefined).length);
                    
                    const complexityCount = decisions.reduce((acc, d) => {
                      const complexity = d.complexity || 'unknown';
                      acc[complexity] = (acc[complexity] || 0) + 1;
                      return acc;
                    }, {} as Record<string, number>);                    const policyTypeCount = decisions.reduce((acc, d) => {
                      const type = d.policy_name || 'unknown'; // Use policy_name since policy_type doesn't exist
                      acc[type] = (acc[type] || 0) + 1;
                      return acc;
                    }, {} as Record<string, number>);

                    return (
                      <Grid container spacing={2}>
                        <Grid item xs={12}>
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="body2" color="text.secondary">
                              Average Execution Time
                            </Typography>                            <Typography variant="h6" color="primary">
                              {avgExecutionTime && !isNaN(avgExecutionTime) ? (
                                avgExecutionTime < 1 ? '<1ms' : 
                                avgExecutionTime < 1000 ? `${avgExecutionTime.toFixed(1)}ms` : 
                                `${(avgExecutionTime / 1000).toFixed(2)}s`
                              ) : 'N/A'}
                            </Typography>
                          </Box>
                        </Grid>
                          <Grid item xs={12}>
                          <Typography variant="subtitle2" gutterBottom>
                            Policy Distribution
                          </Typography>
                          {Object.entries(policyTypeCount).map(([type, count]) => (
                            <Box key={type} sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                              <Typography variant="body2">{type.replace('_', ' ').toUpperCase()}</Typography>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="body2" fontWeight="bold">{count}</Typography>
                                <Typography variant="caption" color="text.secondary">
                                  ({((count / totalDecisions) * 100).toFixed(1)}%)
                                </Typography>
                              </Box>
                            </Box>
                          ))}
                        </Grid>

                        <Grid item xs={12}>
                          <Typography variant="subtitle2" gutterBottom>
                            Complexity Distribution
                          </Typography>
                          {Object.entries(complexityCount).map(([complexity, count]) => (
                            <Box key={complexity} sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                              <Chip 
                                label={complexity} 
                                size="small"
                                color={
                                  complexity === 'simple' ? 'success' :
                                  complexity === 'moderate' ? 'info' :
                                  complexity === 'complex' ? 'warning' : 'default'
                                }
                              />
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="body2" fontWeight="bold">{count}</Typography>
                                <Typography variant="caption" color="text.secondary">
                                  ({((count / totalDecisions) * 100).toFixed(1)}%)
                                </Typography>
                              </Box>
                            </Box>
                          ))}
                        </Grid>
                      </Grid>
                    );
                  })()}
                </CardContent>
              </Card>
            </Grid>

            {/* Policy Recommendations */}
            <Grid item xs={12} md={6}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Optimization Recommendations
                  </Typography>
                  {(() => {
                    const recommendations = [];                    const slowDecisions = decisions.filter(d => 
                      d.execution_time && d.execution_time > 100
                    );
                    const complexDecisions = decisions.filter(d => 
                      d.complexity === 'complex' || d.complexity === 'very_complex'
                    );                    const denyRate = decisions.filter(d => {
                      const decision = (d.result || d.decision || '');
                      return typeof decision === 'string' && decision.toLowerCase().includes('deny');
                    }).length / Math.max(1, decisions.length);

                    if (slowDecisions.length > decisions.length * 0.2) {
                      recommendations.push({
                        type: 'performance',
                        title: 'High Execution Times Detected',
                        description: `${slowDecisions.length} decisions (${((slowDecisions.length / decisions.length) * 100).toFixed(1)}%) took >100ms to execute.`,
                        suggestion: 'Consider optimizing policy rules or adding caching mechanisms.',
                        severity: 'warning'
                      });
                    }

                    if (complexDecisions.length > decisions.length * 0.3) {
                      recommendations.push({
                        type: 'complexity',
                        title: 'High Policy Complexity',
                        description: `${complexDecisions.length} decisions involved complex policies.`,
                        suggestion: 'Review and simplify complex policies where possible.',
                        severity: 'info'
                      });
                    }

                    if (denyRate > 0.5) {
                      recommendations.push({
                        type: 'security',
                        title: 'High Denial Rate',
                        description: `${(denyRate * 100).toFixed(1)}% of decisions resulted in denial.`,
                        suggestion: 'Review security policies to ensure they are not overly restrictive.',
                        severity: 'error'
                      });
                    }

                    if (recommendations.length === 0) {
                      recommendations.push({
                        type: 'success',
                        title: 'System Running Optimally',
                        description: 'No performance or configuration issues detected.',
                        suggestion: 'Continue monitoring for any changes in policy performance.',
                        severity: 'success'
                      });
                    }

                    return recommendations.map((rec, index) => (
                      <Alert 
                        key={index} 
                        severity={rec.severity as any} 
                        sx={{ mb: 2 }}
                        icon={
                          rec.type === 'performance' ? <SpeedIcon /> :
                          rec.type === 'complexity' ? <SecurityIcon /> :
                          rec.type === 'security' ? <SecurityIcon /> :
                          undefined
                        }
                      >
                        <Typography variant="subtitle2" fontWeight="bold">
                          {rec.title}
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1 }}>
                          {rec.description}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          💡 {rec.suggestion}
                        </Typography>
                      </Alert>
                    ));
                  })()}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Box>
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        <TimeRangeSelector onChange={handleTimeRangeChange} />
          {/* Policy Decision Trends */}
        <Box mt={3}>
          <PolicyDecisionTrends
            decisions={decisions}
            timeRange={{
              start: startTime,
              end: endTime
            }}
          />
        </Box>

        {/* Policy Performance Charts */}
        <Box mt={3}>
          <PolicyPerformanceCharts
            decisions={decisions}
            metrics={metrics}
            timeRange={{
              start: startTime,
              end: endTime
            }}
          />
        </Box>        {/* Policy Metrics Charts */}
        {metrics.length === 0 && decisions.length === 0 ? (
          <Box mt={3}>
            <Alert severity="info">
              <Typography variant="h6" gutterBottom>No Policy Metrics Available</Typography>
              <Typography variant="body2">
                Policy metrics are not currently being collected or the policy engine is not sending metrics data.
                This could be because:
              </Typography>
              <ul>
                <li>The policy engine is not configured to send metrics</li>
                <li>The collector service is not receiving policy metrics</li>
                <li>No policy decisions have been made in the selected time range</li>
              </ul>
              <Typography variant="body2" sx={{ mt: 2 }}>
                <strong>Debug Info:</strong> Found {metrics.length} metrics, {decisions.length} decisions in time range.
              </Typography>
            </Alert>
          </Box>
        ) : (          <Grid container spacing={3} mt={1}>
            {/* Policy Count Chart - Removed as requested */}
                {/* Average Execution Time Chart - Removed as requested */}            {/* Decision Summary Chart - Removed as requested */}
          </Grid>        )}
      </TabPanel>

      <TabPanel value={tabValue} index={4}>
        <Box>
          <Typography variant="h6" gutterBottom>
            Policy History
          </Typography>
          
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Filters
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField
                    fullWidth
                    label="Policy ID"
                    value={policyIdFilter}
                    onChange={(e) => setPolicyIdFilter(e.target.value)}
                    placeholder="Filter by policy ID"
                    size="small"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <FormControl fullWidth size="small">
                    <InputLabel>Action</InputLabel>
                    <Select
                      value={actionFilter}
                      label="Action"
                      onChange={(e) => setActionFilter(e.target.value)}
                    >
                      <MenuItem value="">All Actions</MenuItem>
                      <MenuItem value="create">Create</MenuItem>
                      <MenuItem value="update">Update</MenuItem>
                      <MenuItem value="delete">Delete</MenuItem>
                      <MenuItem value="enable">Enable</MenuItem>
                      <MenuItem value="disable">Disable</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {historyLoading && !historyData ? (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
              <CircularProgress />
            </Box>
          ) : historyError ? (
            <Alert severity="error">
              Error loading policy history: {historyError}
            </Alert>
          ) : historyData ? (
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">
                    Policy Modifications ({historyData.total_count} total)
                  </Typography>
                  {historyLoading && <CircularProgress size={20} />}
                </Box>

                {historyData.history.length === 0 ? (
                  <Alert severity="info">
                    No policy history found matching the current filters.
                  </Alert>
                ) : (
                  <>
                    <TableContainer component={Paper}>
                      <Table>
                        <TableHead>
                          <TableRow>
                            <TableCell>Timestamp</TableCell>
                            <TableCell>Action</TableCell>
                            <TableCell>Policy</TableCell>
                            <TableCell>Type</TableCell>
                            <TableCell>Version</TableCell>
                            <TableCell>Details</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {historyData.history.map((entry, index) => {
                            const entryId = `${entry.policy_id}-${entry.timestamp}-${index}`;
                            const isExpanded = expandedRows.has(entryId);
                            
                            return (
                              <React.Fragment key={entryId}>
                                <TableRow>
                                  <TableCell>
                                    <Typography variant="body2">
                                      {formatTimestamp(entry.timestamp)}
                                    </Typography>
                                  </TableCell>
                                  <TableCell>
                                    <Chip
                                      icon={getActionIcon(entry.action)}
                                      label={entry.action}
                                      color={getActionColor(entry.action) as any}
                                      size="small"
                                    />
                                  </TableCell>
                                  <TableCell>
                                    <Box>
                                      <Typography variant="body2" fontWeight="medium">
                                        {entry.policy_name || 'Unknown'}
                                      </Typography>
                                      <Typography variant="caption" color="text.secondary">
                                        {entry.policy_id}
                                      </Typography>
                                    </Box>
                                  </TableCell>
                                  <TableCell>
                                    <Chip
                                      label={entry.policy_type || 'Unknown'}
                                      variant="outlined"
                                      size="small"
                                    />
                                  </TableCell>
                                  <TableCell>
                                    <Typography variant="body2">
                                      v{entry.version}
                                    </Typography>
                                  </TableCell>
                                  <TableCell>
                                    {(entry.old_data || entry.new_data) && (
                                      <MuiTooltip title={isExpanded ? "Hide details" : "Show details"}>
                                        <IconButton
                                          size="small"
                                          onClick={() => toggleRowExpansion(entryId)}
                                        >
                                          <ExpandMoreIcon 
                                            sx={{ 
                                              transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                                              transition: 'transform 0.2s'
                                            }}
                                          />
                                        </IconButton>
                                      </MuiTooltip>
                                    )}
                                  </TableCell>
                                </TableRow>
                                {isExpanded && (
                                  <TableRow>
                                    <TableCell colSpan={6}>
                                      <Accordion expanded={true}>
                                        <AccordionDetails>
                                          <Grid container spacing={2}>
                                            {entry.old_data && (
                                              <Grid item xs={12} md={6}>
                                                {renderPolicyData(entry.old_data, "Previous Data")}
                                              </Grid>
                                            )}
                                            {entry.new_data && (
                                              <Grid item xs={12} md={6}>
                                                {renderPolicyData(entry.new_data, "New Data")}
                                              </Grid>
                                            )}
                                          </Grid>
                                        </AccordionDetails>
                                      </Accordion>
                                    </TableCell>
                                  </TableRow>
                                )}
                              </React.Fragment>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </TableContainer>

                    {historyData.total_count > historyLimit && (
                      <Box display="flex" justifyContent="center" mt={3}>
                        <Pagination
                          count={Math.ceil(historyData.total_count / historyLimit)}
                          page={historyPage}
                          onChange={handleHistoryPageChange}
                          color="primary"
                        />
                      </Box>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          ) : null}
        </Box>
      </TabPanel>

      {/* Policy Editor Dialog */}
      <PolicyEditor
        open={editorOpen}
        onClose={() => {
          setEditorOpen(false);
          setSelectedPolicy(null);
        }}
        onSave={handleSavePolicy}
        policy={selectedPolicy}
        mode={editorMode}
      />

      {/* Policy Decision Detail Dialog */}
      <PolicyDecisionDialog
        open={decisionDialogOpen}
        onClose={() => setDecisionDialogOpen(false)}
        decision={selectedDecision}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={handleDeleteCancel}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          {`Delete policy "${selectedPolicy?.name}"?`}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            This action cannot be undone. Are you sure you want to delete this policy?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDeleteCancel}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" autoFocus>
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default PolicyPage; 