import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Chip,
  Alert,
  AlertTitle,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  LinearProgress,
  Tooltip
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  CheckCircle as SuccessIcon,
  Info as InfoIcon,
  Policy as PolicyIcon,
  Timeline as TimelineIcon,
  BugReport as BugIcon
} from '@mui/icons-material';
import { PolicyDecision } from '../services/policyApi';

interface PolicyDecisionAnalysisProps {
  decisions: PolicyDecision[];
  timeRange: {
    start: string;
    end: string;
  };
}

interface PolicyPattern {
  policyId: string;
  policyName: string;
  totalDecisions: number;
  allowedCount: number;
  deniedCount: number;
  denialRate: number;
  commonReasons: Array<{
    reason: string;
    count: number;
  }>;
  recentTrend: 'improving' | 'worsening' | 'stable';
}

interface PolicyIssue {
  type: 'high_denial_rate' | 'multiple_simultaneous_denials' | 'policy_conflict' | 'configuration_issue';
  severity: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  affectedPolicies: string[];
  recommendations: string[];
  count: number;
}

const PolicyDecisionAnalysis: React.FC<PolicyDecisionAnalysisProps> = ({
  decisions,
  timeRange
}) => {
  const [patterns, setPatterns] = useState<PolicyPattern[]>([]);
  const [issues, setIssues] = useState<PolicyIssue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analyzeDecisions();
  }, [decisions]);

  const analyzeDecisions = () => {
    setLoading(true);
    
    // Group decisions by policy
    const policyGroups = decisions.reduce((acc, decision) => {
      const key = decision.policy_id || 'unknown';
      if (!acc[key]) {
        acc[key] = [];
      }
      acc[key].push(decision);
      return acc;
    }, {} as Record<string, PolicyDecision[]>);

    // Analyze patterns for each policy
    const analyzedPatterns: PolicyPattern[] = Object.entries(policyGroups).map(([policyId, policyDecisions]) => {
      const allowedCount = policyDecisions.filter(d => 
        d.decision === 'allow' || d.result === true || d.result === 'allowed'
      ).length;
      const deniedCount = policyDecisions.length - allowedCount;
      const denialRate = policyDecisions.length > 0 ? (deniedCount / policyDecisions.length) * 100 : 0;

      // Count common denial reasons
      const reasonCounts = policyDecisions
        .filter(d => d.decision === 'deny' || d.result === false || d.result === 'denied')
        .reduce((acc, d) => {
          const reason = d.reason || d.action_taken || 'Unknown reason';
          acc[reason] = (acc[reason] || 0) + 1;
          return acc;
        }, {} as Record<string, number>);

      const commonReasons = Object.entries(reasonCounts)
        .map(([reason, count]) => ({ reason, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 3);

      // Determine trend (simplified)
      const recentDecisions = policyDecisions.slice(-10);
      const recentDenialRate = recentDecisions.length > 0 
        ? (recentDecisions.filter(d => d.decision === 'deny' || d.result === false).length / recentDecisions.length) * 100
        : 0;
      
      let recentTrend: 'improving' | 'worsening' | 'stable' = 'stable';
      if (Math.abs(recentDenialRate - denialRate) > 10) {
        recentTrend = recentDenialRate < denialRate ? 'improving' : 'worsening';
      }

      return {
        policyId,
        policyName: policyDecisions[0]?.policy_name || policyId,
        totalDecisions: policyDecisions.length,
        allowedCount,
        deniedCount,
        denialRate,
        commonReasons,
        recentTrend
      };
    });

    // Identify issues
    const identifiedIssues: PolicyIssue[] = [];

    // Check for high denial rates
    analyzedPatterns.forEach(pattern => {
      if (pattern.denialRate > 80 && pattern.totalDecisions > 5) {
        identifiedIssues.push({
          type: 'high_denial_rate',
          severity: 'high',
          title: `High Denial Rate for ${pattern.policyName}`,
          description: `Policy "${pattern.policyName}" has a ${pattern.denialRate.toFixed(1)}% denial rate, which may indicate configuration issues.`,
          affectedPolicies: [pattern.policyId],
          recommendations: [
            'Review policy conditions and thresholds',
            'Check if the policy parameters are too restrictive',
            'Verify that the context data being sent matches policy expectations',
            'Consider adjusting policy priority or conditions'
          ],
          count: pattern.deniedCount
        });
      }
    });

    // Check for multiple simultaneous denials (like your case)
    const simultaneousDenials = decisions.filter(d => {
      const timestamp = new Date(d.timestamp).getTime();
      const sameTimeDecisions = decisions.filter(other => {
        const otherTime = new Date(other.timestamp).getTime();
        return Math.abs(timestamp - otherTime) < 1000; // Within 1 second
      });
      return sameTimeDecisions.length > 1 && (d.decision === 'deny' || d.result === false);
    });

    if (simultaneousDenials.length > 0) {
      const affectedPolicies = [...new Set(simultaneousDenials.map(d => d.policy_id))];
      identifiedIssues.push({
        type: 'multiple_simultaneous_denials',
        severity: 'high',
        title: 'Multiple Simultaneous Policy Denials Detected',
        description: 'Multiple policy denials are occurring at the same time, which may indicate a policy evaluation logic issue or missing context data.',
        affectedPolicies,
        recommendations: [
          'Check if policy conditions are being evaluated correctly',
          'Verify that context data includes all required fields',
          'Review policy engine logs for evaluation errors',
          'Consider adding more specific conditions to avoid conflicts',
          'Check if default values are being used when context data is missing'
        ],
        count: simultaneousDenials.length
      });
    }

    // Check for policies with specific problematic patterns
    const serverControlPattern = analyzedPatterns.find(p => p.policyId.includes('server-control'));
    if (serverControlPattern && serverControlPattern.denialRate > 50) {
      const hasRoundIssue = serverControlPattern.commonReasons.some(r => 
        r.reason.toLowerCase().includes('round') || 
        r.reason.toLowerCase().includes('maximum')
      );
      const hasClientIssue = serverControlPattern.commonReasons.some(r => 
        r.reason.toLowerCase().includes('client') || 
        r.reason.toLowerCase().includes('available')
      );
      const hasConvergenceIssue = serverControlPattern.commonReasons.some(r => 
        r.reason.toLowerCase().includes('convergence') || 
        r.reason.toLowerCase().includes('improvement')
      );

      if (hasRoundIssue || hasClientIssue || hasConvergenceIssue) {
        identifiedIssues.push({
          type: 'configuration_issue',
          severity: 'medium',
          title: 'FL Server Control Policy Configuration Issue',
          description: 'The FL server control policy appears to have configuration issues that are preventing training from starting or continuing.',
          affectedPolicies: [serverControlPattern.policyId],
          recommendations: [
            hasRoundIssue ? 'Check max_rounds parameter - it may be set too low' : '',
            hasClientIssue ? 'Verify min_clients_threshold - ensure enough clients are available' : '',
            hasConvergenceIssue ? 'Review convergence_threshold - it may be too strict for early rounds' : '',
            'Consider adding round-based conditions (e.g., only check convergence after round 5)',
            'Verify that context data includes current_round, available_clients, and accuracy_improvement',
            'Check policy evaluation order and priority'
          ].filter(Boolean),
          count: serverControlPattern.deniedCount
        });
      }
    }

    setPatterns(analyzedPatterns);
    setIssues(identifiedIssues);
    setLoading(false);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high': return <ErrorIcon />;
      case 'medium': return <WarningIcon />;
      case 'low': return <InfoIcon />;
      default: return <InfoIcon />;
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'improving': return 'success';
      case 'worsening': return 'error';
      case 'stable': return 'info';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Box>
        <Typography variant="h6" gutterBottom>
          Analyzing Policy Decisions...
        </Typography>
        <LinearProgress />
      </Box>
    );
  }

  // Check if we have anything meaningful to show
  const hasIssues = issues.length > 0;
  const hasPatterns = patterns.length > 0;
  const hasProblematicPatterns = patterns.some(p => p.denialRate > 10 || p.deniedCount > 0);
  const shouldShowAnalysis = hasIssues || hasProblematicPatterns;

  // If everything is working fine, show a success message instead
  if (!shouldShowAnalysis && decisions.length > 0) {
    return (
      <Box>
        <Alert severity="success" sx={{ mb: 2 }}>
          <AlertTitle>Policy Engine Operating Normally</AlertTitle>
          <Typography variant="body2">
            All policy decisions are being processed successfully with no significant issues detected.
          </Typography>
          <Box mt={2}>
            <Typography variant="body2">
              <strong>Summary:</strong> {decisions.length} decisions processed, {patterns.filter(p => p.denialRate === 0).length} policies with 100% allow rate.
            </Typography>
          </Box>
        </Alert>
        
        {/* Still show patterns if there are any, but with a positive framing */}
        {hasPatterns && (
          <Box>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SuccessIcon color="success" />
              Policy Performance Summary
            </Typography>
            
            <Grid container spacing={2}>
              {patterns.map((pattern, index) => (
                <Grid item xs={12} md={6} lg={4} key={index}>
                  <Card variant="outlined">
                    <CardContent>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                        <Typography variant="h6" noWrap>
                          {pattern.policyName}
                        </Typography>
                        <Chip 
                          label={pattern.recentTrend} 
                          color={getTrendColor(pattern.recentTrend) as any}
                          size="small"
                        />
                      </Box>

                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">
                          Total Decisions: {pattern.totalDecisions}
                        </Typography>
                        <Box display="flex" gap={1} mt={1}>
                          <Chip 
                            label={`${pattern.allowedCount} Allowed`} 
                            color="success" 
                            size="small" 
                            variant="outlined"
                          />
                          {pattern.deniedCount > 0 && (
                            <Chip 
                              label={`${pattern.deniedCount} Denied`} 
                              color="error" 
                              size="small" 
                              variant="outlined"
                            />
                          )}
                        </Box>
                      </Box>

                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          Success Rate: {(100 - pattern.denialRate).toFixed(1)}%
                        </Typography>
                        <LinearProgress 
                          variant="determinate" 
                          value={100 - pattern.denialRate} 
                          color="success"
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}
      </Box>
    );
  }

  // If no decisions at all
  if (decisions.length === 0) {
    return (
      <Box>
        <Alert severity="info">
          <AlertTitle>No Policy Decisions to Analyze</AlertTitle>
          <Typography variant="body2">
            No policy decisions have been made in the selected time range. 
            Try expanding the time range or check if the policy engine is receiving requests.
          </Typography>
        </Alert>
      </Box>
    );
  }

  // Show analysis when there are actual issues
  return (
    <Box>
      <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <BugIcon color="primary" />
        Policy Decision Analysis
      </Typography>

      {/* Issues Section */}
      {hasIssues && (
        <Box mb={3}>
          <Typography variant="h6" gutterBottom color="error">
            Identified Issues ({issues.length})
          </Typography>
          {issues.map((issue, index) => (
            <Alert 
              key={index} 
              severity={getSeverityColor(issue.severity) as any} 
              sx={{ mb: 2 }}
              icon={getSeverityIcon(issue.severity)}
            >
              <AlertTitle>{issue.title}</AlertTitle>
              <Typography variant="body2" paragraph>
                {issue.description}
              </Typography>
              
              <Typography variant="body2" fontWeight="bold" gutterBottom>
                Affected Policies: {issue.affectedPolicies.join(', ')}
              </Typography>
              
              <Typography variant="body2" fontWeight="bold" gutterBottom>
                Recommendations:
              </Typography>
              <List dense>
                {issue.recommendations.map((rec, recIndex) => (
                  <ListItem key={recIndex} sx={{ py: 0 }}>
                    <ListItemText 
                      primary={`• ${rec}`}
                      primaryTypographyProps={{ variant: 'body2' }}
                    />
                  </ListItem>
                ))}
              </List>
            </Alert>
          ))}
        </Box>
      )}

      {/* Policy Patterns - only show problematic ones */}
      {hasProblematicPatterns && (
        <Box>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TimelineIcon color="primary" />
            Policy Decision Patterns
          </Typography>

          <Grid container spacing={2}>
            {patterns
              .filter(pattern => pattern.denialRate > 10 || pattern.deniedCount > 0)
              .map((pattern, index) => (
                <Grid item xs={12} md={6} lg={4} key={index}>
                  <Card>
                    <CardContent>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                        <Typography variant="h6" noWrap>
                          {pattern.policyName}
                        </Typography>
                        <Chip 
                          label={pattern.recentTrend} 
                          color={getTrendColor(pattern.recentTrend) as any}
                          size="small"
                        />
                      </Box>

                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary">
                          Total Decisions: {pattern.totalDecisions}
                        </Typography>
                        <Box display="flex" gap={1} mt={1}>
                          <Chip 
                            label={`${pattern.allowedCount} Allowed`} 
                            color="success" 
                            size="small" 
                            variant="outlined"
                          />
                          <Chip 
                            label={`${pattern.deniedCount} Denied`} 
                            color="error" 
                            size="small" 
                            variant="outlined"
                          />
                        </Box>
                      </Box>

                      <Box mb={2}>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          Denial Rate: {pattern.denialRate.toFixed(1)}%
                        </Typography>
                        <LinearProgress 
                          variant="determinate" 
                          value={pattern.denialRate} 
                          color={pattern.denialRate > 50 ? 'error' : pattern.denialRate > 20 ? 'warning' : 'success'}
                        />
                      </Box>

                      {pattern.commonReasons.length > 0 && (
                        <Accordion>
                          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                            <Typography variant="body2">
                              Common Denial Reasons ({pattern.commonReasons.length})
                            </Typography>
                          </AccordionSummary>
                          <AccordionDetails>
                            <List dense>
                              {pattern.commonReasons.map((reason, reasonIndex) => (
                                <ListItem key={reasonIndex}>
                                  <ListItemIcon>
                                    <ErrorIcon color="error" fontSize="small" />
                                  </ListItemIcon>
                                  <ListItemText 
                                    primary={reason.reason}
                                    secondary={`${reason.count} occurrences`}
                                  />
                                </ListItem>
                              ))}
                            </List>
                          </AccordionDetails>
                        </Accordion>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              ))}
          </Grid>
        </Box>
      )}
    </Box>
  );
};

export default PolicyDecisionAnalysis; 