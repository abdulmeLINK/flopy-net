import { AppBar, Toolbar, Typography, IconButton, Box, Chip, Tooltip, Button } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DescriptionIcon from '@mui/icons-material/Description';

interface HeaderProps {
  onMenuToggle?: () => void;
}

const Header = ({ onMenuToggle }: HeaderProps) => {
  // Get version info from environment variables (set at build time)
  const version = (import.meta as any).env?.VITE_APP_VERSION || '1.0.0';
  const buildDate = (import.meta as any).env?.VITE_BUILD_DATE || new Date().toISOString().split('T')[0];
  const gitCommit = (import.meta as any).env?.VITE_GIT_COMMIT || 'latest';
  const environment = (import.meta as any).env?.VITE_ENVIRONMENT || 'development';
  const backendUrl = (import.meta as any).env?.VITE_BACKEND_URL || 'http://localhost:8001';

  // Format version for display (remove 'v' if present)
  const displayVersion = version.startsWith('v') ? version.slice(1) : version;

  return (
    <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
      <Toolbar>
        <IconButton
          color="inherit"
          aria-label="open drawer"
          edge="start"
          onClick={onMenuToggle}
          sx={{ mr: 2, display: { sm: 'none' } }}
        >
          <MenuIcon />
        </IconButton>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexGrow: 1 }}>
          <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 'bold' }}>
            FLOPY-NET
          </Typography>
          
          {/* Version Chip */}
          <Tooltip title={`Version: ${displayVersion}\nCommit: ${gitCommit}\nEnvironment: ${environment}`}>
            <Chip 
              label={`v${displayVersion}`}
              size="small"
              variant="outlined"
              sx={{ 
                color: 'white', 
                borderColor: 'rgba(255,255,255,0.3)',
                fontSize: '0.75rem',
                height: '24px',
                cursor: 'pointer'
              }}
            />
          </Tooltip>
          
          {/* Build Date */}
          <Typography 
            variant="caption" 
            sx={{ 
              color: 'rgba(255,255,255,0.7)',
              fontSize: '0.7rem',
              display: { xs: 'none', sm: 'block' }
            }}
          >
            Build: {buildDate}
          </Typography>

          {/* Environment Indicator */}
          {environment !== 'production' && (
            <Chip 
              label={environment.toUpperCase()}
              size="small"
              color={environment === 'development' ? 'warning' : 'info'}
              sx={{ 
                fontSize: '0.65rem',
                height: '20px',
                display: { xs: 'none', md: 'flex' }
              }}
            />
          )}
        </Box>

        {/* API Docs Button */}
        <Tooltip title="Open API Documentation">
          <Button
            color="inherit"
            href={`${backendUrl}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            startIcon={<DescriptionIcon />}
            sx={{ 
              textTransform: 'none',
              display: { xs: 'none', md: 'inline-flex' }
            }}
          >
            API Docs
          </Button>
        </Tooltip>

        <Tooltip title="Open API Documentation">
          <IconButton
            color="inherit"
            href={`${backendUrl}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            sx={{ display: { xs: 'inline-flex', md: 'none' } }}
          >
            <DescriptionIcon />
          </IconButton>
        </Tooltip>
      </Toolbar>
    </AppBar>
  );
};

export default Header; 