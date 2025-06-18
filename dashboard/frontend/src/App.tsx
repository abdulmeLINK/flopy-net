import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Box from '@mui/material/Box';

// Layout components (to be created)
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import PageWrapper from './components/layout/PageWrapper';

// Page components (to be created/fleshed out)
import OverviewPage from './pages/OverviewPage';
import FLTrainingPage from './pages/FLTrainingPage';
import NetworkPage from './pages/NetworkPage';
import PolicyPage from './pages/PolicyPage';
import EventsPage from './pages/EventsPage';
import ScenariosPage from './pages/ScenariosPage';
import SystemConfigPage from './pages/SystemConfigPage';


function App() {
  return (
    <Router>
      <Box sx={{ display: 'flex' }}>
        <Header /> 
        <Sidebar />
        <PageWrapper>
          <Routes>
            <Route path="/" element={<Navigate replace to="/overview" />} />
            <Route path="/overview" element={<OverviewPage />} />
            <Route path="/fl-monitoring" element={<FLTrainingPage />} />
            <Route path="/network" element={<NetworkPage />} />
            <Route path="/policy" element={<PolicyPage />} />

            <Route path="/events" element={<EventsPage />} />
            <Route path="/scenarios" element={<ScenariosPage />} />
            <Route path="/system-config" element={<SystemConfigPage />} />
            {/* Add other routes here */}
            <Route path="*" element={<div>Page Not Found</div>} />
          </Routes>
        </PageWrapper>
      </Box>
    </Router>
  );
}

export default App; 