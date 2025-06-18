import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  TextField,
  Alert,
  Tab,
  Tabs,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Tooltip,
  Divider
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  Code as CodeIcon,
  Visibility as PreviewIcon,
  Info as InfoIcon,
  Security as SecurityIcon,
  NetworkCheck as NetworkCheckIcon,
  Storage as StorageIcon
} from '@mui/icons-material';
import { Policy, PolicyRequest, PolicyRule, validatePolicy, ValidationResult } from '../services/policyApi';

interface PolicyEditorProps {
  open: boolean;
  onClose: () => void;
  onSave: (policy: PolicyRequest) => Promise<void>;
  policy?: Policy | null;
  mode: 'create' | 'edit';
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`policy-editor-tabpanel-${index}`}
      aria-labelledby={`policy-editor-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 0 }}>{children}</Box>}
    </div>
  );
}

// Enhanced tooltip component for policy information
const PolicyInfoTooltip: React.FC<{
  children: React.ReactElement;
  title: string;
  description: string;
  policyType?: string;
  additionalInfo?: string;
}> = ({ children, title, description, policyType, additionalInfo }) => {
  
  const getPolicyTypeColor = (type: string): string => {
    switch (type) {
      case 'network_security': return '#f44336';
      case 'fl_security': return '#e91e63';
      case 'fl_client_start':
      case 'fl_client_evaluation':
      case 'fl_client_training': return '#2196f3';
      case 'fl_server_control': return '#3f51b5';
      case 'data_privacy': return '#9c27b0';
      case 'resource_control': return '#ff9800';
      case 'reliability': return '#4caf50';
      case 'demonstration': return '#607d8b';
      default: return '#757575';
    }
  };

  const getPolicyTypeDescription = (type: string): string => {
    switch (type) {
      case 'network_security': return 'Network-level security policies';
      case 'fl_security': return 'Federated learning security rules';
      case 'fl_client_start': return 'Client initialization policies';
      case 'fl_client_evaluation': return 'Client evaluation controls';
      case 'fl_client_training': return 'Client training restrictions';
      case 'fl_server_control': return 'Server operation policies';
      case 'fl_training_parameters': return 'Training parameter controls';
      case 'fl_server_client_filter': return 'Client filtering rules';
      case 'data_privacy': return 'Data privacy and protection';
      case 'resource_control': return 'Resource usage limitations';
      case 'reliability': return 'System reliability policies';
      case 'demonstration': return 'Demo and testing policies';
      default: return 'General policy rules';
    }
  };

  const tooltipContent = (
    <Box sx={{ p: 1, maxWidth: 400 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        {title}
      </Typography>
      {policyType && (
        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
          <Chip 
            label={policyType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            size="small"
            sx={{ 
              bgcolor: getPolicyTypeColor(policyType),
              color: 'white',
              fontSize: '0.7rem'
            }}
          />
          <Chip 
            label={getPolicyTypeDescription(policyType)}
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.7rem' }}
          />
        </Box>
      )}
      <Typography variant="body2" sx={{ mb: 1 }}>
        {description}
      </Typography>
      {additionalInfo && (
        <Typography variant="caption" color="text.secondary">
          {additionalInfo}
        </Typography>
      )}
    </Box>
  );

  return (
    <Tooltip title={tooltipContent} arrow placement="top">
      {children}
    </Tooltip>
  );
};

const PolicyEditor: React.FC<PolicyEditorProps> = ({
  open,
  onClose,
  onSave,
  policy,
  mode
}) => {
  const [tabValue, setTabValue] = useState(0);
  const [formData, setFormData] = useState<PolicyRequest>({
    name: '',
    type: '',
    description: '',
    priority: 100,
    rules: []
  });
  const [jsonText, setJsonText] = useState('');
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [saving, setSaving] = useState(false);

  // Policy types for dropdown
  const policyTypes = [
    'network_security',
    'fl_security',
    'fl_client_start',
    'fl_client_evaluation',
    'fl_client_training',
    'fl_server_control',
    'fl_training_parameters',
    'fl_server_client_filter',
    'data_privacy',
    'resource_control',
    'reliability',
    'demonstration'
  ];

  // Rule actions for dropdown
  const ruleActions = [
    'allow',
    'deny',
    'modify',
    'verify',
    'configure',
    'filter',
    'enforce',
    'limit',
    'prioritize',
    'retry',
    'checkpoint',
    'failover',
    'log',
    'simulate',
    'monitor'
  ];

  // Initialize form data
  useEffect(() => {
    if (policy && mode === 'edit') {
      const initialData: PolicyRequest = {
        id: policy.id,
        name: policy.name,
        type: policy.type,
        description: policy.description || '',
        priority: policy.priority,
        rules: policy.rules || []
      };
      setFormData(initialData);
      setJsonText(JSON.stringify(initialData, null, 2));
    } else {
      const emptyData: PolicyRequest = {
        name: '',
        type: '',
        description: '',
        priority: 100,
        rules: []
      };
      setFormData(emptyData);
      setJsonText(JSON.stringify(emptyData, null, 2));
    }
  }, [policy, mode, open]);

  // Validate policy when form data changes
  useEffect(() => {
    if (formData.name && formData.type) {
      const validateAsync = async () => {
        try {
          const result = await validatePolicy(formData);
          setValidation(result);
        } catch (error) {
          console.error('Validation error:', error);
          setValidation({
            valid: false,
            errors: ['Validation service unavailable'],
            warnings: []
          });
        }
      };
      validateAsync();
    } else {
      // Clear validation if required fields are empty
      setValidation(null);
    }
  }, [formData]);

  // Update form data when JSON changes
  const handleJsonChange = (value: string) => {
    setJsonText(value);
    try {
      const parsed = JSON.parse(value);
      if (parsed && typeof parsed === 'object') {
        setFormData(parsed);
      }
    } catch (error) {
      // Invalid JSON - validation will catch this
      console.debug('Invalid JSON in editor:', error);
    }
  };

  // Update JSON when form data changes
  const updateJson = (newData: PolicyRequest) => {
    setFormData(newData);
    setJsonText(JSON.stringify(newData, null, 2));
  };

  const handleFieldChange = (field: keyof PolicyRequest, value: any) => {
    const newData = { ...formData, [field]: value };
    updateJson(newData);
  };

  const handleRuleChange = (index: number, field: keyof PolicyRule, value: any) => {
    const newRules = [...formData.rules];
    newRules[index] = { ...newRules[index], [field]: value };
    updateJson({ ...formData, rules: newRules });
  };

  const addRule = () => {
    const newRule: PolicyRule = {
      action: 'allow',
      description: '',
      match: {},
      parameters: {}
    };
    updateJson({ ...formData, rules: [...formData.rules, newRule] });
  };

  const removeRule = (index: number) => {
    const newRules = formData.rules.filter((_, i) => i !== index);
    updateJson({ ...formData, rules: newRules });
  };

  const handleSave = async () => {
    if (!validation?.valid) {
      return;
    }

    setSaving(true);
    try {
      await onSave(formData);
      onClose();
    } catch (error) {
      console.error('Error saving policy:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setTabValue(0);
    setValidation(null);
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="lg"
      fullWidth
      PaperProps={{
        sx: { height: '90vh' }
      }}
    >
      <DialogTitle>
        {mode === 'create' ? 'Create New Policy' : `Edit Policy: ${policy?.name}`}
      </DialogTitle>

      <DialogContent sx={{ p: 0 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={(_, value) => setTabValue(value)}>
            <Tab
              label="Form Editor"
              icon={<PreviewIcon />}
              iconPosition="start"
            />
            <Tab
              label="JSON Editor"
              icon={<CodeIcon />}
              iconPosition="start"
            />
          </Tabs>
        </Box>

        <Box sx={{ p: 3, height: 'calc(90vh - 200px)', overflow: 'auto' }}>
          <TabPanel value={tabValue} index={0}>            <Grid container spacing={3}>
              {/* Enhanced Header with Policy Information */}
              <Grid item xs={12}>
                <Box sx={{ mb: 3 }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h5" component="h2" sx={{ fontWeight: 600 }}>
                      {mode === 'create' ? 'Create New Policy' : 'Edit Policy'}
                    </Typography>
                    {formData.type && (
                      <Chip 
                        label={formData.type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        color={
                          formData.type.includes('security') ? 'error' :
                          formData.type.includes('fl_') ? 'primary' :
                          formData.type.includes('data_privacy') ? 'secondary' :
                          formData.type.includes('resource') ? 'warning' : 'default'
                        }
                        size="small"
                        sx={{ fontWeight: 500 }}
                      />
                    )}
                  </Box>

                  {/* Policy Information Panel */}
                  <Accordion defaultExpanded={mode === 'create'}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <InfoIcon color="primary" />
                        <Typography variant="h6">Policy Configuration Guide</Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                            Policy Types
                          </Typography>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                            <Typography variant="body2" color="text.secondary">
                              <SecurityIcon fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
                              <strong>Security:</strong> network_security, fl_security, data_privacy
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              <NetworkCheckIcon fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
                              <strong>FL Control:</strong> fl_client_*, fl_server_*, fl_training_*
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              <StorageIcon fontSize="small" sx={{ mr: 1, verticalAlign: 'middle' }} />
                              <strong>Operations:</strong> resource_control, reliability
                            </Typography>
                          </Box>
                        </Grid>
                        <Grid item xs={12} md={6}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                            Configuration Tips
                          </Typography>
                          <Typography variant="body2" color="text.secondary" paragraph>
                            • <strong>Priority:</strong> Lower numbers = higher priority (0-1000)
                          </Typography>
                          <Typography variant="body2" color="text.secondary" paragraph>
                            • <strong>Rules:</strong> Define specific conditions and actions
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            • <strong>JSON View:</strong> Advanced editing with validation
                          </Typography>
                        </Grid>
                      </Grid>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="body2" color="text.secondary">
                        <strong>Policy Engine Integration:</strong> Policies are evaluated in priority order and can control FL training processes, network access, client behavior, and system security measures.
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                </Box>
              </Grid>

              {/* Basic Information */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Basic Information
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <PolicyInfoTooltip
                  title="Policy Name"
                  description="Unique identifier for this policy. Should be descriptive and follow naming conventions for easy identification."
                  additionalInfo="Example: 'client_authentication_required' or 'max_training_rounds_limit'"
                >
                  <TextField
                    fullWidth
                    label="Name"
                    value={formData.name}
                    onChange={(e) => handleFieldChange('name', e.target.value)}
                    required
                    placeholder="e.g., client_authentication_policy"
                  />
                </PolicyInfoTooltip>
              </Grid>

              <Grid item xs={12} md={6}>
                <PolicyInfoTooltip
                  title="Policy Type"
                  description="Categorizes the policy for proper handling by the policy engine. Different types control different aspects of the FL system."
                  policyType={formData.type}
                  additionalInfo="Select the appropriate type based on what system component this policy should control"
                >
                  <FormControl fullWidth required>
                    <InputLabel>Type</InputLabel>
                    <Select
                      value={formData.type}
                      onChange={(e) => handleFieldChange('type', e.target.value)}
                      label="Type"
                    >
                      {policyTypes.map((type) => (
                        <MenuItem key={type} value={type}>
                          {type}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </PolicyInfoTooltip>
              </Grid>

              <Grid item xs={12}>
                <PolicyInfoTooltip
                  title="Policy Description"
                  description="Human-readable explanation of what this policy does and when it applies. Include conditions and expected behavior."
                  additionalInfo="Good descriptions help with policy management and debugging"
                >
                  <TextField
                    fullWidth
                    label="Description"
                    value={formData.description}
                    onChange={(e) => handleFieldChange('description', e.target.value)}
                    multiline
                    rows={3}
                    placeholder="Describe what this policy controls and under what conditions it applies..."
                  />
                </PolicyInfoTooltip>
              </Grid>              <Grid item xs={12} md={6}>
                <PolicyInfoTooltip
                  title="Policy Priority"
                  description="Execution priority for this policy. Lower numbers mean higher priority. Policies are evaluated in priority order."
                  additionalInfo="Range: 0-1000. Critical policies: 0-100, Important: 101-500, Standard: 501-1000"
                >
                  <TextField
                    fullWidth
                    label="Priority"
                    type="number"
                    value={formData.priority}
                    onChange={(e) => handleFieldChange('priority', parseInt(e.target.value) || 0)}
                    required
                    inputProps={{ min: 0, max: 1000 }}
                    helperText={`Priority level: ${formData.priority <= 100 ? 'Critical' : formData.priority <= 500 ? 'Important' : 'Standard'}`}
                  />
                </PolicyInfoTooltip>
              </Grid>

              {/* Rules Section */}
              <Grid item xs={12}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="h6">Policy Rules</Typography>
                    <PolicyInfoTooltip
                      title="Policy Rules"
                      description="Individual rules that define specific conditions and actions for this policy. Each rule is evaluated independently."
                      additionalInfo="Rules are processed in order and can have different conditions and actions"
                    >
                      <InfoIcon fontSize="small" color="primary" sx={{ cursor: 'help' }} />
                    </PolicyInfoTooltip>
                  </Box>
                  <Button
                    startIcon={<AddIcon />}
                    onClick={addRule}
                    variant="outlined"
                    size="small"
                  >
                    Add Rule
                  </Button>
                </Box>

                {formData.rules.map((rule, index) => (
                  <Accordion key={index} sx={{ mb: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box display="flex" alignItems="center" justifyContent="space-between" width="100%">
                        <Typography>
                          Rule {index + 1}: {rule.action} - {rule.description || 'No description'}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            removeRule(index);
                          }}
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                          <FormControl fullWidth>
                            <InputLabel>Action</InputLabel>
                            <Select
                              value={rule.action}
                              onChange={(e) => handleRuleChange(index, 'action', e.target.value)}
                              label="Action"
                            >
                              {ruleActions.map((action) => (
                                <MenuItem key={action} value={action}>
                                  {action}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </Grid>
                        <Grid item xs={12} md={6}>
                          <TextField
                            fullWidth
                            label="Description"
                            value={rule.description}
                            onChange={(e) => handleRuleChange(index, 'description', e.target.value)}
                          />
                        </Grid>
                        <Grid item xs={12} md={6}>
                          <TextField
                            fullWidth
                            label="Match Conditions (JSON)"
                            value={JSON.stringify(rule.match, null, 2)}
                            onChange={(e) => {
                              try {
                                const parsed = JSON.parse(e.target.value);
                                handleRuleChange(index, 'match', parsed);
                              } catch {
                                // Invalid JSON, ignore for now
                              }
                            }}
                            multiline
                            rows={3}
                          />
                        </Grid>
                        <Grid item xs={12} md={6}>
                          <TextField
                            fullWidth
                            label="Parameters (JSON)"
                            value={JSON.stringify(rule.parameters || {}, null, 2)}
                            onChange={(e) => {
                              try {
                                const parsed = JSON.parse(e.target.value);
                                handleRuleChange(index, 'parameters', parsed);
                              } catch {
                                // Invalid JSON, ignore for now
                              }
                            }}
                            multiline
                            rows={3}
                          />
                        </Grid>
                      </Grid>
                    </AccordionDetails>
                  </Accordion>
                ))}

                {formData.rules.length === 0 && (
                  <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                    No rules defined. Click "Add Rule" to create your first rule.
                  </Typography>
                )}
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <TextField
              fullWidth
              multiline
              rows={20}
              value={jsonText}
              onChange={(e) => handleJsonChange(e.target.value)}
              variant="outlined"
              sx={{
                '& .MuiInputBase-input': {
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                }
              }}
            />
          </TabPanel>

          {/* Validation Results */}
          {validation && (
            <Box mt={2}>
              {validation.valid ? (
                <Alert severity="success">
                  Policy validation passed! Ready to save.
                </Alert>
              ) : (
                <Alert severity="error">
                  <Typography variant="subtitle2" gutterBottom>
                    Validation Errors:
                  </Typography>
                  {validation.errors.map((error, index) => (
                    <Typography key={index} variant="body2">
                      • {error}
                    </Typography>
                  ))}
                </Alert>
              )}

              {validation.warnings && validation.warnings.length > 0 && (
                <Alert severity="warning" sx={{ mt: 1 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Warnings:
                  </Typography>
                  {validation.warnings.map((warning, index) => (
                    <Typography key={index} variant="body2">
                      • {warning}
                    </Typography>
                  ))}
                </Alert>
              )}
            </Box>
          )}
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 3, borderTop: 1, borderColor: 'divider' }}>
        <Button onClick={handleClose}>
          Cancel
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={!validation?.valid || saving}
        >
          {saving ? 'Saving...' : mode === 'create' ? 'Create Policy' : 'Update Policy'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PolicyEditor; 