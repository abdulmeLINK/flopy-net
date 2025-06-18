import React, { useState } from 'react';
import {
  Container,
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  Fade
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Timeline as TimelineIcon,
  History as HistoryIcon,
  Settings as SettingsIcon
} from '@mui/icons-material';

// Import the new component structure
import { useFLData } from '../components/fl/hooks/useFLData';
import { FLOverviewTab } from '../components/fl/FLOverviewTab';
import { FLTrainingChartsTab } from '../components/fl/FLTrainingChartsTab';
import { FLRoundsHistoryTab } from '../components/fl/FLRoundsHistoryTab';
import { FLConfigurationTab } from '../components/fl/FLConfigurationTab';

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
      id={`fl-tabpanel-${index}`}
      aria-labelledby={`fl-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Fade in={true} timeout={300}>
          <Box sx={{ py: 3 }}>
            {children}
          </Box>
        </Fade>
      )}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `fl-tab-${index}`,
    'aria-controls': `fl-tabpanel-${index}`,
  };
}

const FLTrainingPage: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);

  // Use the custom hook for data management
  const flData = useFLData();

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box mb={4}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
          Federated Learning Training
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Monitor FL training progress, view metrics, and manage configurations
        </Typography>
      </Box>

      <Paper sx={{ borderRadius: 2, overflow: 'hidden' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs 
            value={tabValue} 
            onChange={handleTabChange} 
            variant="fullWidth"
            sx={{
              '& .MuiTab-root': {
                minHeight: 64,
                textTransform: 'none',
                fontSize: '1rem',
                fontWeight: 500
              }
            }}
          >
            <Tab 
              icon={<DashboardIcon />} 
              label="Overview" 
              {...a11yProps(0)}
              iconPosition="start"
            />
            <Tab 
              icon={<TimelineIcon />} 
              label="Training Charts" 
              {...a11yProps(1)}
              iconPosition="start"
            />
            <Tab 
              icon={<HistoryIcon />} 
              label="Rounds History" 
              {...a11yProps(2)}
              iconPosition="start"
            />
            <Tab 
              icon={<SettingsIcon />} 
              label="Configuration" 
              {...a11yProps(3)}
              iconPosition="start"
            />
          </Tabs>
        </Box>

        <Box sx={{ minHeight: 600 }}>
          {/* Overview Tab */}
          <TabPanel value={tabValue} index={0}>
            <FLOverviewTab
              data={flData}
              onRefresh={flData.handleRefresh}
              formatAccuracy={flData.formatAccuracy}
              formatLoss={flData.formatLoss}
              formatModelSize={flData.formatModelSize}
              getTrainingStatusColor={flData.getTrainingStatusColor}
              getTrainingStatusText={flData.getTrainingStatusText}
            />
          </TabPanel>

          {/* Training Charts Tab */}
          <TabPanel value={tabValue} index={1}>
            <FLTrainingChartsTab
              data={flData}
            />
          </TabPanel>

          {/* Rounds History Tab */}
          <TabPanel value={tabValue} index={2}>
            <FLRoundsHistoryTab
              data={flData}
              formatAccuracy={flData.formatAccuracy}
              formatLoss={flData.formatLoss}
              formatModelSize={flData.formatModelSize}
            />
          </TabPanel>

          {/* Configuration Tab */}
          <TabPanel value={tabValue} index={3}>
            <FLConfigurationTab
              configuration={flData.configuration}
              configLoading={flData.configLoading}
              configError={flData.configError}
              onReloadConfig={flData.loadConfiguration}
            />
          </TabPanel>
        </Box>
      </Paper>
    </Container>
  );
};

export default FLTrainingPage; 