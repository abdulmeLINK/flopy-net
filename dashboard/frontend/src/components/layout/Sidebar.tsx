import {
  Drawer,
  Toolbar,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
} from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';

// Import icons for the sidebar menu items
import DashboardIcon from '@mui/icons-material/Dashboard';
import BarChartIcon from '@mui/icons-material/BarChart';
import NetworkCheckIcon from '@mui/icons-material/NetworkCheck';
import SecurityIcon from '@mui/icons-material/Security';
import HistoryIcon from '@mui/icons-material/History';
import EventNoteIcon from '@mui/icons-material/EventNote';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SettingsIcon from '@mui/icons-material/Settings';

// Define the drawer width
const drawerWidth = 240;

// Menu items configuration with nested routes
const menuItems = [
  { path: '/overview', text: 'Overview', icon: <DashboardIcon /> },
  { path: '/fl-monitoring', text: 'FL Training', icon: <BarChartIcon /> },
  { path: '/network', text: 'Network Topology', icon: <NetworkCheckIcon /> },
  { path: '/policy', text: 'Policy Engine', icon: <SecurityIcon /> },
  
  { path: '/events', text: 'System Events', icon: <EventNoteIcon /> },
  { path: '/scenarios', text: 'Scenarios', icon: <PlayArrowIcon /> },
  { path: '/system-config', text: 'System Config', icon: <SettingsIcon /> },
];

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
      }}
    >
      <Toolbar /> {/* This creates space for the app bar */}
      <List>
        {menuItems.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => navigate(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
      <Divider />
    </Drawer>
  );
};

export default Sidebar; 