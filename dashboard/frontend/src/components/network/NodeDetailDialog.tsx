import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Stack,
  Box,
  Button
} from '@mui/material';

interface NodeDetailDialogProps {
  node: any;
  open: boolean;
  onClose: () => void;
}

export const NodeDetailDialog: React.FC<NodeDetailDialogProps> = ({
  node,
  open,
  onClose
}) => {
  if (!node) return null;
  
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {node.type === 'switch' ? 'Switch Details' : 'Host Details'}
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2}>
          <Box>
            <Typography variant="body2" color="text.secondary">ID:</Typography>
            <Typography variant="body1">{node.id}</Typography>
          </Box>
          {node.dpid && (
            <Box>
              <Typography variant="body2" color="text.secondary">DPID:</Typography>
              <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>{node.dpid}</Typography>
            </Box>
          )}
          {node.ip && (
            <Box>
              <Typography variant="body2" color="text.secondary">IP Address:</Typography>
              <Typography variant="body1">{node.ip}</Typography>
            </Box>
          )}
          {node.mac && (
            <Box>
              <Typography variant="body2" color="text.secondary">MAC Address:</Typography>
              <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>{node.mac}</Typography>
            </Box>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="outlined">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
};
