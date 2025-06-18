import { ReactNode } from 'react';
import { Box, Toolbar } from '@mui/material';

interface PageWrapperProps {
  children: ReactNode;
}

const PageWrapper = ({ children }: PageWrapperProps) => {
  return (
    <Box
      component="main"
      sx={{
        flexGrow: 1,
        p: 3,
        width: { sm: `calc(100% - 240px)` }, // 240px is the drawer width
        overflow: 'auto',
      }}
    >
      <Toolbar /> {/* This creates space for the app bar */}
      {children}
    </Box>
  );
};

export default PageWrapper; 