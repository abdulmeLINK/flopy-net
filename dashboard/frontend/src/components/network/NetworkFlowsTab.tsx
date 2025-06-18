import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Box,
  Grid,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import { ExpandMore as ExpandMoreIcon } from '@mui/icons-material';

interface NetworkFlowsTabProps {
  flowsData: {
    flows?: any[];
    summary?: {
      total_flows?: number;
      switches_with_flows?: number;
      policy_flows?: number | any[];
      qos_flows?: number;
      table_stats?: Record<string, number>;
    };
  };
  refreshing?: boolean;
}

export const NetworkFlowsTab: React.FC<NetworkFlowsTabProps> = ({
  flowsData,
  refreshing = false
}) => {
  const flows = flowsData?.flows || [];
  const summary = flowsData?.summary || {};
  const getActionColor = (actionsOrInstructions: any[]) => {
    if (!actionsOrInstructions || actionsOrInstructions.length === 0) return 'default';
    
    // Helper function to check if an action is a DROP action
    const isDropAction = (action: any) => {
      // Check for explicit drop type
      if (action.type === 'drop') return true;
      
      // Check for OpenFlow drop patterns (no output actions)
      if (action.OFPActionOutput) return false;
      
      // If no recognized output action, might be drop
      return false;
    };
    
    // Helper function to check if an action is an OUTPUT action
    const isOutputAction = (action: any) => {
      if (action.type === 'output') return true;
      if (action.OFPActionOutput) return true;
      return false;
    };
    
    let hasOutput = false;
    let hasDrop = false;
    
    // Check if this is an instructions array (OpenFlow 1.3+)
    if (actionsOrInstructions[0] && actionsOrInstructions[0].OFPInstructionActions) {
      // Extract actions from instructions
      for (const instruction of actionsOrInstructions) {
        if (instruction.OFPInstructionActions && instruction.OFPInstructionActions.actions) {
          for (const action of instruction.OFPInstructionActions.actions) {
            if (isDropAction(action)) hasDrop = true;
            if (isOutputAction(action)) hasOutput = true;
          }
        }
      }
    } else {
      // Handle direct actions array (OpenFlow 1.0)
      for (const action of actionsOrInstructions) {
        if (isDropAction(action)) hasDrop = true;
        if (isOutputAction(action)) hasOutput = true;
      }
    }
    
    if (hasDrop) return 'error';
    if (hasOutput) return 'success';
    return 'primary';
  };

  const formatMatch = (match: any) => {
    if (!match) return 'Any';
    const matchParts = [];
    if (match.in_port) matchParts.push(`in_port=${match.in_port}`);
    if (match.eth_dst) matchParts.push(`eth_dst=${match.eth_dst}`);
    if (match.eth_src) matchParts.push(`eth_src=${match.eth_src}`);
    if (match.ipv4_dst) matchParts.push(`ipv4_dst=${match.ipv4_dst}`);
    if (match.ipv4_src) matchParts.push(`ipv4_src=${match.ipv4_src}`);
    return matchParts.length > 0 ? matchParts.join(', ') : 'Any';
  };  const formatActions = (actionsOrInstructions: any[]) => {
    if (!actionsOrInstructions || actionsOrInstructions.length === 0) return 'No actions';
    
    // Helper function to format a single OpenFlow action
    const formatSingleAction = (action: any) => {
      // Check if action has a description field (from enhanced serialization)
      if (action.description) {
        return action.description;
      }
      
      // Handle OpenFlow action objects (e.g., {"OFPActionOutput": {...}})
      if (action.OFPActionOutput) {
        const output = action.OFPActionOutput;
        const port = output.port;
        
        // Handle special port values
        switch (port) {
          case 4294967293: // 0xFFFFFFFD - OFPP_CONTROLLER
            return 'Send to controller';
          case 4294967292: // 0xFFFFFFFC - OFPP_ANY
            return 'Output to any port';
          case 4294967291: // 0xFFFFFFFB - OFPP_ALL
            return 'Flood to all ports';
          case 4294967290: // 0xFFFFFFFA - OFPP_FLOOD
            return 'Flood (excluding input port)';
          case 4294967289: // 0xFFFFFFF9 - OFPP_NORMAL
            return 'Normal L2/L3 processing';
          case 4294967288: // 0xFFFFFFF8 - OFPP_IN_PORT
            return 'Send out input port';
          default:
            return `Output to port ${port}`;
        }
      }
      
      // Handle other OpenFlow action types
      if (action.OFPActionSetField) {
        return `Set field: ${JSON.stringify(action.OFPActionSetField)}`;
      }
      
      if (action.OFPActionSetQueue) {
        return `Set queue ${action.OFPActionSetQueue.queue_id}`;
      }
      
      if (action.OFPActionGroup) {
        return `Execute group ${action.OFPActionGroup.group_id}`;
      }
      
      if (action.OFPActionPushVlan) {
        return 'Push VLAN tag';
      }
      
      if (action.OFPActionPopVlan) {
        return 'Pop VLAN tag';
      }
      
      // Handle normalized action format with type field
      switch (action.type) {
        case 'OUTPUT':
          if (action.port !== undefined && action.port !== null) {
            // Handle special port values
            switch (action.port) {
              case 4294967293: return 'Send to controller';
              case 4294967290: return 'Flood (excluding input port)';
              case 4294967289: return 'Normal L2/L3 processing';
              default: return `Output to port ${action.port}`;
            }
          }
          return 'Output action';
        case 'SET_FIELD': return action.field && action.value ? `Set ${action.field} = ${action.value}` : 'Set field action';
        case 'SET_QUEUE': return action.queue_id !== undefined ? `Set queue ${action.queue_id}` : 'Set queue action';
        case 'GROUP': return action.group_id !== undefined ? `Execute group ${action.group_id}` : 'Group action';
        case 'PUSH_VLAN': return 'Push VLAN tag';
        case 'POP_VLAN': return 'Pop VLAN tag';
        case 'SET_MPLS_TTL': return 'Set MPLS TTL';
        case 'DEC_MPLS_TTL': return 'Decrement MPLS TTL';
        case 'PUSH_MPLS': return 'Push MPLS tag';
        case 'POP_MPLS': return 'Pop MPLS tag';
        case 'SET_NW_TTL': return 'Set network TTL';
        case 'DEC_NW_TTL': return 'Decrement network TTL';
        case 'COPY_TTL_OUT': return 'Copy TTL outwards';
        case 'COPY_TTL_IN': return 'Copy TTL inwards';
        default:
          return action.type || 'Unknown action';
      }
      
      // Fallback for completely unknown action format
      return 'Unknown action';
    };
    
    // Check if this is an instructions array (OpenFlow 1.3+)
    if (actionsOrInstructions[0] && actionsOrInstructions[0].OFPInstructionActions) {
      // Extract actions from instructions
      const allActions = [];
      for (const instruction of actionsOrInstructions) {
        if (instruction.OFPInstructionActions && instruction.OFPInstructionActions.actions) {
          allActions.push(...instruction.OFPInstructionActions.actions);
        }
      }
      return allActions.map(formatSingleAction).join(', ');
    }
    
    // Handle direct actions array (OpenFlow 1.0)
    return actionsOrInstructions.map(formatSingleAction).join(', ');
  };

  return (
    <Box>
      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" color="primary" gutterBottom>
              {summary.total_flows || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Total Flows
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" color="secondary" gutterBottom>
              {summary.switches_with_flows || 0}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Active Switches
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>            <Typography variant="h4" color="success.main" gutterBottom>
              {Array.isArray(summary.policy_flows) ? summary.policy_flows.length : (summary.policy_flows || 0)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Policy Flows
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, textAlign: 'center' }}>
            <Typography variant="h4" color="warning.main" gutterBottom>
              {Object.keys(summary.table_stats || {}).length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Flow Tables
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Flow Tables Breakdown */}
      {Object.keys(summary.table_stats || {}).length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Flow Distribution by Table
            </Typography>
            <Grid container spacing={2}>
              {Object.entries(summary.table_stats || {}).map(([tableId, count]) => (
                <Grid item xs={6} sm={4} md={3} key={tableId}>
                  <Paper variant="outlined" sx={{ p: 1, textAlign: 'center' }}>
                    <Typography variant="body2" color="text.secondary">
                      Table {tableId}
                    </Typography>
                    <Typography variant="h6">
                      {count as number}
                    </Typography>
                  </Paper>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Flows List */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            OpenFlow Rules ({flows.length})
          </Typography>
          
          {flows.length === 0 ? (
            <Typography variant="body1" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
              No flow rules found. This could mean the SDN controller is not connected or no flows have been installed.
            </Typography>
          ) : (
            <Box>
              {/* Group flows by switch */}
              {Object.entries(
                flows.reduce((acc: any, flow: any) => {
                  const switchKey = flow.switch_name || flow.switch_dpid || 'Unknown';
                  if (!acc[switchKey]) acc[switchKey] = [];
                  acc[switchKey].push(flow);
                  return acc;
                }, {})
              ).map(([switchName, switchFlows]: [string, any]) => (
                <Accordion key={switchName} defaultExpanded={Object.keys(flows.reduce((acc: any, flow: any) => {
                  const switchKey = flow.switch_name || flow.switch_dpid || 'Unknown';
                  if (!acc[switchKey]) acc[switchKey] = [];
                  acc[switchKey].push(flow);
                  return acc;
                }, {})).length === 1}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="subtitle1">
                      {switchName} ({switchFlows.length} flows)
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Table</TableCell>
                            <TableCell>Priority</TableCell>
                            <TableCell>Match</TableCell>
                            <TableCell>Actions</TableCell>
                            <TableCell>Stats</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {switchFlows.map((flow: any, index: number) => (
                            <TableRow key={`${switchName}-${index}`}>
                              <TableCell>
                                <Chip 
                                  label={flow.table_id || 0} 
                                  size="small" 
                                  variant="outlined"
                                />
                              </TableCell>
                              <TableCell>
                                <Chip 
                                  label={flow.priority || 0} 
                                  size="small"
                                  color={flow.priority > 100 ? 'primary' : 'default'}
                                />
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                                  {formatMatch(flow.match)}
                                </Typography>
                              </TableCell>
                              <TableCell>
                                <Chip 
                                  label={formatActions(flow.instructions || flow.actions)}
                                  size="small"
                                  color={getActionColor(flow.instructions || flow.actions)}
                                />
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2" color="text.secondary">
                                  {flow.byte_count ? `${flow.byte_count} bytes` : 'N/A'}
                                  {flow.packet_count && ` / ${flow.packet_count} pkts`}
                                </Typography>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Box>
          )}        </CardContent>
      </Card>
    </Box>
  );
};
