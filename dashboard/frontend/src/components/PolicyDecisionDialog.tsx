import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Chip,
  Divider,
  Grid,
  Paper,
  IconButton,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  AlertTitle,
  LinearProgress
} from '@mui/material';
import {
  Close as CloseIcon,
  AccessTime as TimeIcon,
  Policy as PolicyIcon,
  Computer as ComponentIcon,
  CheckCircle as AllowIcon,
  Cancel as DenyIcon,
  Warning as WarningIcon,
  ExpandMore as ExpandMoreIcon,
  Rule as RuleIcon,
  PlayArrow as ActionIcon,
  Timeline as PathIcon,
  Error as ViolationIcon,
  Speed as PerformanceIcon,
  Info as InfoIcon,
  Check as CheckIcon,
  Clear as ClearIcon
} from '@mui/icons-material';
import { PolicyDecision } from '../services/policyApi';

interface PolicyDecisionDialogProps {
  open: boolean;
  onClose: () => void;
  decision: PolicyDecision | null;
}

const PolicyDecisionDialog: React.FC<PolicyDecisionDialogProps> = ({
  open,
  onClose,
  decision
}) => {
  if (!decision) {
    return null;
  }

  // Helper function to format timestamp
  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
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
  };

  // Helper function to get decision details
  const getDecisionDetails = () => {
    let decision_result = 'unknown';
    let isAllowed = false;
    
    if (typeof decision.result === 'boolean') {
      isAllowed = decision.result;
      decision_result = decision.result ? 'allow' : 'deny';
    } else if (typeof decision.result === 'string') {
      decision_result = decision.result.toLowerCase();
      isAllowed = decision_result === 'allowed' || decision_result === 'allow';
    } else if (decision.decision) {
      decision_result = decision.decision.toLowerCase();
      isAllowed = decision_result === 'allow';
    }
    
    switch (decision_result) {
      case 'allow':
      case 'allowed':
        return { 
          label: 'Allowed', 
          color: 'success', 
          icon: <AllowIcon />,
          bgColor: '#e8f5e8',
          textColor: '#2e7d32'
        };
      case 'deny':
      case 'denied':
        return { 
          label: 'Denied', 
          color: 'error', 
          icon: <DenyIcon />,
          bgColor: '#ffebee',
          textColor: '#c62828'
        };
      case 'modify':
      case 'modified':
        return { 
          label: 'Modified', 
          color: 'warning', 
          icon: <WarningIcon />,
          bgColor: '#fff3e0',
          textColor: '#ef6c00'
        };
      default:
        return { 
          label: 'Unknown', 
          color: 'default', 
          icon: <WarningIcon />,
          bgColor: '#f5f5f5',
          textColor: '#757575'
        };
    }
  };

  const decisionDetails = getDecisionDetails();

  // Helper function to format context
  const formatContext = (context: any) => {
    if (!context) return 'No context provided';
    if (typeof context === 'string') return context;
    if (typeof context === 'object') {
      return JSON.stringify(context, null, 2);
    }
    return String(context);
  };

  // Helper function to get policy name
  const getPolicyName = () => {
    return decision.policy_name || decision.policy_id || 'Unknown Policy';
  };

  // Helper function to get component name
  const getComponentName = () => {
    return decision.component || 'Unknown Component';
  };

  // Helper function to get complexity color
  const getComplexityColor = (complexity?: string) => {
    switch (complexity) {
      case 'simple': return 'success';
      case 'moderate': return 'info';
      case 'complex': return 'warning';
      case 'very_complex': return 'error';
      default: return 'default';
    }
  };

  // Helper function to format evaluation time
  const formatEvaluationTime = (timeMs?: number) => {
    if (!timeMs) return 'N/A';
    if (timeMs < 1) return '<1ms';
    if (timeMs < 1000) return `${timeMs.toFixed(1)}ms`;
    return `${(timeMs / 1000).toFixed(2)}s`;
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
          maxHeight: '95vh'
        }
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={2}>
            <Box
              sx={{
                p: 1,
                borderRadius: 1,
                backgroundColor: decisionDetails.bgColor,
                color: decisionDetails.textColor,
                display: 'flex',
                alignItems: 'center'
              }}
            >
              {decisionDetails.icon}
            </Box>
            <Box>
              <Typography variant="h6" component="div">
                Policy Decision Details
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {formatTimestamp(decision.timestamp)}
              </Typography>
            </Box>
          </Box>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ p: 3 }}>
        <Grid container spacing={3}>
          {/* Quick Summary for Denials */}
          {(decision.result === false || decision.decision === 'deny') && (
            <Grid item xs={12}>
              <Alert 
                severity="error" 
                sx={{ 
                  mb: 2,
                  '& .MuiAlert-message': { width: '100%' }
                }}
              >
                <AlertTitle sx={{ fontWeight: 'bold' }}>Request Denied</AlertTitle>
                <Grid container spacing={2} sx={{ mt: 0.5 }}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" fontWeight="medium">What was requested:</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {decision.context?.action && `${decision.context.action} `}
                      {decision.context?.operation && `(${decision.context.operation})`}
                      {!decision.context?.action && !decision.context?.operation && 'Policy evaluation'}
                      {decision.context?.client_id && ` by ${decision.context.client_id}`}
                      {decision.context?.server_id && ` by ${decision.context.server_id}`}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="body2" fontWeight="medium">Why it was denied:</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {decision.violations && decision.violations.length > 0 ? 
                        `${decision.violations[0].policy_name} - ${decision.violations[0].reason}` :
                        decision.reason || 'Policy violation detected'
                      }
                    </Typography>
                  </Grid>
                </Grid>
              </Alert>
            </Grid>
          )}

          {/* Decision Result */}
          <Grid item xs={12}>
            <Paper sx={{ p: 2, backgroundColor: decisionDetails.bgColor }}>
              <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
                <Box display="flex" alignItems="center" gap={2}>
                  {decisionDetails.icon}
                  <Typography variant="h6" sx={{ color: decisionDetails.textColor }}>
                    Decision: {decisionDetails.label}
                  </Typography>
                </Box>
                {decision.complexity && (
                  <Chip 
                    label={decision.complexity}
                    color={getComplexityColor(decision.complexity) as any}
                    size="small"
                    variant="outlined"
                    sx={{ 
                      backgroundColor: 'rgba(255, 255, 255, 0.8)',
                      fontWeight: 'medium'
                    }}
                  />
                )}
              </Box>
              
              {/* Enhanced reason display */}
              {decision.reason && (
                <Box mb={2}>
                  <Typography variant="body1" sx={{ color: decisionDetails.textColor, opacity: 0.9, fontWeight: 'medium' }}>
                    {decision.reason}
                  </Typography>
                </Box>
              )}

              {/* Show specific rule that caused denial */}
              {(decision.result === false || decision.decision === 'deny') && decision.violations && decision.violations.length > 0 && (
                <Alert 
                  severity="error" 
                  sx={{ 
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    color: 'error.main',
                    mb: 1,
                    '& .MuiAlert-icon': { color: 'error.main' }
                  }}
                >
                  <Typography variant="body2" fontWeight="medium">
                    Denied by: {decision.violations[0].policy_name} - Rule {decision.violations[0].rule_index}
                  </Typography>
                  <Typography variant="body2">
                    {decision.violations[0].reason}
                  </Typography>
                </Alert>
              )}

              {/* Show quick summary for denials */}
              {(decision.result === false || decision.decision === 'deny') && decision.context && (
                <Box 
                  sx={{ 
                    backgroundColor: 'rgba(255, 255, 255, 0.8)', 
                    p: 1.5, 
                    borderRadius: 1, 
                    border: '1px solid rgba(211, 47, 47, 0.3)'
                  }}
                >
                  <Typography variant="body2" color="text.primary" fontWeight="medium" gutterBottom>
                    Request Summary:
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {decision.context.action && `Action: ${decision.context.action}`}
                    {decision.context.operation && decision.context.action && ' • '}
                    {decision.context.operation && `Operation: ${decision.context.operation}`}
                    {(decision.context.client_id || decision.context.server_id) && 
                     (decision.context.action || decision.context.operation) && ' • '}
                    {(decision.context.client_id || decision.context.server_id) && 
                     `Requester: ${decision.context.client_id || decision.context.server_id}`}
                  </Typography>
                </Box>
              )}
            </Paper>
          </Grid>

          {/* Basic Information */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, height: '100%' }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <InfoIcon color="primary" />
                Basic Information
              </Typography>
              
              <Box mb={2}>
                <Typography variant="body2" color="text.secondary">Policy</Typography>
                <Typography variant="body1" fontWeight="medium">
                  {getPolicyName()}
                </Typography>
                {decision.policy_id && decision.policy_id !== decision.policy_name && (
                  <Typography variant="caption" color="text.secondary">
                    ID: {decision.policy_id}
                  </Typography>
                )}
              </Box>
              
              <Box mb={2}>
                <Typography variant="body2" color="text.secondary">Component</Typography>
                <Chip 
                  icon={<ComponentIcon />}
                  label={getComponentName()}
                  variant="outlined"
                  size="small"
                />
              </Box>

              {/* Enhanced Request Information */}
              {decision.context && (
                <>
                  {decision.context.action && (
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">Requested Action</Typography>
                      <Chip 
                        label={decision.context.action}
                        color={decision.result === false || decision.decision === 'deny' ? 'error' : 'default'}
                        size="small"
                        sx={{ fontWeight: 'medium' }}
                      />
                    </Box>
                  )}
                  
                  {decision.context.operation && (
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">Operation</Typography>
                      <Typography variant="body1" fontWeight="medium">
                        {decision.context.operation}
                      </Typography>
                    </Box>
                  )}

                  {(decision.context.client_id || decision.context.server_id) && (
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">Requester</Typography>
                      <Typography variant="body1" sx={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                        {decision.context.client_id || decision.context.server_id}
                      </Typography>
                    </Box>
                  )}

                  {/* Show key request parameters */}
                  {Object.keys(decision.context).some(key => 
                    ['resource', 'endpoint', 'method', 'training_type', 'model_name', 'dataset'].includes(key)
                  ) && (
                    <Box mb={2}>
                      <Typography variant="body2" color="text.secondary">Request Details</Typography>
                      <Box sx={{ pl: 1, mt: 0.5 }}>
                        {decision.context.resource && (
                          <Typography variant="body2">
                            <strong>Resource:</strong> {decision.context.resource}
                          </Typography>
                        )}
                        {decision.context.endpoint && (
                          <Typography variant="body2">
                            <strong>Endpoint:</strong> {decision.context.endpoint}
                          </Typography>
                        )}
                        {decision.context.method && (
                          <Typography variant="body2">
                            <strong>Method:</strong> {decision.context.method}
                          </Typography>
                        )}
                        {decision.context.training_type && (
                          <Typography variant="body2">
                            <strong>Training Type:</strong> {decision.context.training_type}
                          </Typography>
                        )}
                        {decision.context.model_name && (
                          <Typography variant="body2">
                            <strong>Model:</strong> {decision.context.model_name}
                          </Typography>
                        )}
                        {decision.context.dataset && (
                          <Typography variant="body2">
                            <strong>Dataset:</strong> {decision.context.dataset}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  )}
                </>
              )}
              
              {decision.request_id && (
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">Request ID</Typography>
                  <Typography variant="body1" sx={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                    {decision.request_id}
                  </Typography>
                </Box>
              )}
              
              {decision.execution_time && (
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">Execution Time</Typography>
                  <Typography variant="body1">
                    {formatEvaluationTime(decision.execution_time)}
                  </Typography>
                </Box>
              )}
            </Paper>
          </Grid>

          {/* Performance Metrics */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2, height: '100%' }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <PerformanceIcon color="primary" />
                Performance Metrics
              </Typography>
              
              {/* Check if we have any metrics data */}
              {(decision.evaluation_details || decision.total_rules_evaluated || decision.policies_involved || decision.actions_count || 
                decision.rule_evaluations || decision.violations) ? (
                <>
                  {decision.evaluation_details && (
                    <>
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Policies Evaluated</Typography>
                        <Typography variant="h6">
                          {decision.evaluation_details.total_policies || 0}
                        </Typography>
                      </Box>
                      
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Rules Evaluated</Typography>
                        <Typography variant="h6">
                          {decision.evaluation_details.evaluated_rules || 0}
                        </Typography>
                      </Box>
                      
                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">Matched Rules</Typography>
                        <Typography variant="h6" color={decision.evaluation_details.matched_rules > 0 ? 'warning.main' : 'success.main'}>
                          {decision.evaluation_details.matched_rules || 0}
                        </Typography>
                      </Box>
                      
                      {decision.evaluation_details.matched_rules > 0 && decision.evaluation_details.evaluated_rules > 0 && (
                        <Box mb={2}>
                          <Typography variant="body2" color="text.secondary">Match Rate</Typography>
                          <Box display="flex" alignItems="center" gap={1}>
                            <LinearProgress 
                              variant="determinate" 
                              value={(decision.evaluation_details.matched_rules / decision.evaluation_details.evaluated_rules) * 100}
                              sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                            />
                            <Typography variant="body2">
                              {((decision.evaluation_details.matched_rules / decision.evaluation_details.evaluated_rules) * 100).toFixed(1)}%
                            </Typography>
                          </Box>
                        </Box>
                      )}
                    </>
                  )}
                  
                  {(decision.total_rules_evaluated || decision.policies_involved || decision.actions_count) && (
                    <>
                      <Divider sx={{ my: 2 }} />
                      <Grid container spacing={2}>
                        {decision.total_rules_evaluated && (
                          <Grid item xs={4}>
                            <Typography variant="body2" color="text.secondary" align="center">Rules</Typography>
                            <Typography variant="h6" align="center">{decision.total_rules_evaluated}</Typography>
                          </Grid>
                        )}
                        {decision.policies_involved && (
                          <Grid item xs={4}>
                            <Typography variant="body2" color="text.secondary" align="center">Policies</Typography>
                            <Typography variant="h6" align="center">{decision.policies_involved}</Typography>
                          </Grid>
                        )}
                        {decision.actions_count && (
                          <Grid item xs={4}>
                            <Typography variant="body2" color="text.secondary" align="center">Actions</Typography>
                            <Typography variant="h6" align="center">{decision.actions_count}</Typography>
                          </Grid>
                        )}
                      </Grid>
                    </>
                  )}

                  {/* Basic decision metrics even without full evaluation details */}
                  {!decision.evaluation_details && (decision.rule_evaluations || decision.violations) && (
                    <>
                      <Divider sx={{ my: 2 }} />
                      <Grid container spacing={2}>
                        {decision.rule_evaluations && (
                          <Grid item xs={4}>
                            <Typography variant="body2" color="text.secondary" align="center">Policies</Typography>
                            <Typography variant="h6" align="center">{decision.rule_evaluations.length}</Typography>
                          </Grid>
                        )}
                        {decision.violations && (
                          <Grid item xs={4}>
                            <Typography variant="body2" color="text.secondary" align="center">Violations</Typography>
                            <Typography variant="h6" align="center" color="error.main">{decision.violations.length}</Typography>
                          </Grid>
                        )}
                        {decision.execution_time && (
                          <Grid item xs={4}>
                            <Typography variant="body2" color="text.secondary" align="center">Time</Typography>
                            <Typography variant="h6" align="center">{formatEvaluationTime(decision.execution_time)}</Typography>
                          </Grid>
                        )}
                      </Grid>
                    </>
                  )}
                </>
              ) : (
                /* Show helpful message when no metrics are available */
                <Box 
                  display="flex" 
                  flexDirection="column" 
                  alignItems="center" 
                  justifyContent="center" 
                  sx={{ 
                    minHeight: 120, 
                    textAlign: 'center',
                    color: 'text.secondary',
                    backgroundColor: 'grey.50',
                    borderRadius: 1,
                    p: 2
                  }}
                >
                  <PerformanceIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
                  <Typography variant="body2" sx={{ mb: 1 }}>
                    Limited metrics available
                  </Typography>
                  <Typography variant="caption">
                    {decision.execution_time ? 
                      `Processed in ${formatEvaluationTime(decision.execution_time)}` :
                      'This decision was processed without detailed evaluation metrics'
                    }
                  </Typography>
                </Box>
              )}
            </Paper>
          </Grid>

          {/* Violations */}
          {decision.violations && decision.violations.length > 0 && (
            <Grid item xs={12}>
              <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ViolationIcon color="error" />
                    Violations ({decision.violations.length})
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {decision.violations.map((violation, index) => (
                    <Alert key={index} severity="error" sx={{ mb: 2 }}>
                      <AlertTitle>
                        Policy: {violation.policy_name} (Rule {violation.rule_index})
                      </AlertTitle>
                      <Typography variant="body2" paragraph>
                        <strong>Action:</strong> {violation.action}
                      </Typography>
                      <Typography variant="body2" paragraph>
                        <strong>Reason:</strong> {violation.reason}
                      </Typography>
                      {violation.details && violation.details.length > 0 && (
                        <Typography variant="body2">
                          <strong>Details:</strong> {violation.details.join(', ')}
                        </Typography>
                      )}
                      {violation.parameters && Object.keys(violation.parameters).length > 0 && (
                        <Box mt={1}>
                          <Typography variant="body2" fontWeight="bold">Parameters:</Typography>
                          <Box component="pre" sx={{ fontSize: '0.8rem', mt: 1, p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
                            {JSON.stringify(violation.parameters, null, 2)}
                          </Box>
                        </Box>
                      )}
                    </Alert>
                  ))}
                </AccordionDetails>
              </Accordion>
            </Grid>
          )}

          {/* Rule Evaluations */}
          {decision.rule_evaluations && decision.rule_evaluations.length > 0 && (
            <Grid item xs={12}>
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <RuleIcon color="primary" />
                    Rule Evaluations ({decision.rule_evaluations.length} policies)
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {decision.rule_evaluations.map((policyEval, policyIndex) => (
                    <Paper key={policyIndex} sx={{ p: 2, mb: 2 }}>
                      <Typography variant="h6" gutterBottom>
                        {policyEval.policy_name}
                        <Chip 
                          label={`Priority: ${policyEval.priority}`}
                          size="small"
                          sx={{ ml: 2 }}
                        />
                        <Chip 
                          label={policyEval.result}
                          color={policyEval.result === 'allow' ? 'success' : 'error'}
                          size="small"
                          sx={{ ml: 1 }}
                        />
                      </Typography>
                      
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        Evaluation Time: {formatEvaluationTime(policyEval.evaluation_time_ms)}
                      </Typography>
                      
                      {policyEval.rules_evaluated && policyEval.rules_evaluated.length > 0 && (
                        <TableContainer component={Paper} variant="outlined" sx={{ mt: 2 }}>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell>Rule</TableCell>
                                <TableCell>Type</TableCell>
                                <TableCell>Matched</TableCell>
                                <TableCell>Action</TableCell>
                                <TableCell>Reason</TableCell>
                                <TableCell>Time</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {policyEval.rules_evaluated.map((rule, ruleIndex) => (
                                <TableRow key={ruleIndex}>
                                  <TableCell>{rule.rule_index}</TableCell>
                                  <TableCell>
                                    <Chip label={rule.rule_type} size="small" variant="outlined" />
                                  </TableCell>
                                  <TableCell>
                                    {rule.matched ? (
                                      <CheckIcon color="success" />
                                    ) : (
                                      <ClearIcon color="disabled" />
                                    )}
                                  </TableCell>
                                  <TableCell>
                                    <Chip 
                                      label={rule.action}
                                      size="small"
                                      color={rule.action === 'deny' ? 'error' : rule.action === 'allow' ? 'success' : 'default'}
                                    />
                                  </TableCell>
                                  <TableCell sx={{ maxWidth: 200 }}>
                                    <Tooltip title={rule.reason}>
                                      <Typography variant="body2" noWrap>
                                        {rule.reason}
                                      </Typography>
                                    </Tooltip>
                                  </TableCell>
                                  <TableCell>{formatEvaluationTime(rule.evaluation_time_ms)}</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      )}
                    </Paper>
                  ))}
                </AccordionDetails>
              </Accordion>
            </Grid>
          )}

          {/* Applied Actions */}
          {decision.applied_actions && decision.applied_actions.length > 0 && (
            <Grid item xs={12}>
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ActionIcon color="primary" />
                    Applied Actions ({decision.applied_actions.length})
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <TableContainer component={Paper} variant="outlined">
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Action</TableCell>
                          <TableCell>Policy</TableCell>
                          <TableCell>Rule</TableCell>
                          <TableCell>Reason</TableCell>
                          <TableCell>Parameters</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {decision.applied_actions.map((action, index) => (
                          <TableRow key={index}>
                            <TableCell>
                              <Chip 
                                label={action.action}
                                color={action.action === 'deny' ? 'error' : action.action === 'allow' ? 'success' : 'default'}
                              />
                            </TableCell>
                            <TableCell>{action.policy_name}</TableCell>
                            <TableCell>{action.rule_index}</TableCell>
                            <TableCell sx={{ maxWidth: 250 }}>
                              <Tooltip title={action.reason}>
                                <Typography variant="body2" noWrap>
                                  {action.reason}
                                </Typography>
                              </Tooltip>
                            </TableCell>
                            <TableCell>
                              {action.parameters && Object.keys(action.parameters).length > 0 ? (
                                <Tooltip title={JSON.stringify(action.parameters, null, 2)}>
                                  <Chip label={`${Object.keys(action.parameters).length} params`} size="small" />
                                </Tooltip>
                              ) : (
                                <Typography variant="body2" color="text.secondary">None</Typography>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </AccordionDetails>
              </Accordion>
            </Grid>
          )}

          {/* Decision Path */}
          {decision.decision_path && decision.decision_path.length > 0 && (
            <Grid item xs={12}>
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <PathIcon color="primary" />
                    Decision Path ({decision.decision_path.length} steps)
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <List>
                    {decision.decision_path.map((step, index) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          <Typography variant="body2" color="primary" fontWeight="bold">
                            {index + 1}
                          </Typography>
                        </ListItemIcon>
                        <ListItemText 
                          primary={step}
                          primaryTypographyProps={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </AccordionDetails>
              </Accordion>
            </Grid>
          )}

          {/* Context Information */}
          <Grid item xs={12}>
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <InfoIcon color="primary" />
                  Context Information
                  {decision.context && Object.keys(decision.context).length > 0 && (
                    <Chip label={`${Object.keys(decision.context).length} fields`} size="small" color="info" />
                  )}
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                {decision.context && Object.keys(decision.context).length > 0 ? (
                  <>
                    {/* Structured context display */}
                    <Grid container spacing={2} sx={{ mb: 2 }}>
                      {Object.entries(decision.context).map(([key, value]) => (
                        <Grid item xs={12} sm={6} md={4} key={key}>
                          <Paper variant="outlined" sx={{ p: 1.5 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 'bold' }}>
                              {key.replace(/_/g, ' ')}
                            </Typography>
                            <Typography variant="body2" sx={{ mt: 0.5, wordBreak: 'break-word' }}>
                              {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                            </Typography>
                          </Paper>
                        </Grid>
                      ))}
                    </Grid>

                    {/* Show denial-specific context if available */}
                    {(decision.result === false || decision.decision === 'deny') && (
                      <Alert severity="info" sx={{ mb: 2 }}>
                        <Typography variant="body2" fontWeight="medium" gutterBottom>
                          Denial Analysis:
                        </Typography>
                        <Typography variant="body2">
                          The request was evaluated against policy conditions and found to violate one or more rules. 
                          {decision.violations && decision.violations.length > 0 && 
                            ` Specifically, the "${decision.violations[0].policy_name}" policy blocked this action.`}
                        </Typography>
                      </Alert>
                    )}

                    <Divider sx={{ my: 2 }} />
                    
                    {/* Raw context data */}
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      Raw Context Data:
                    </Typography>
                    <Box component="pre" sx={{ 
                      fontSize: '0.75rem', 
                      backgroundColor: 'grey.50', 
                      p: 2, 
                      borderRadius: 1,
                      overflow: 'auto',
                      maxHeight: 200,
                      border: '1px solid',
                      borderColor: 'grey.300'
                    }}>
                      {JSON.stringify(decision.context, null, 2)}
                    </Box>
                  </>
                ) : (
                  <Box 
                    display="flex" 
                    flexDirection="column" 
                    alignItems="center" 
                    sx={{ py: 4, color: 'text.secondary' }}
                  >
                    <InfoIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
                    <Typography variant="body2">
                      No context information available for this decision
                    </Typography>
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>
          </Grid>
        </Grid>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="contained">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PolicyDecisionDialog; 