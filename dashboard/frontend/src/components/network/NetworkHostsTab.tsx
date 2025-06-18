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
  Chip
} from '@mui/material';

interface NetworkHostsTabProps {
  hostsList: any[];
  refreshing?: boolean;
}

export const NetworkHostsTab: React.FC<NetworkHostsTabProps> = ({
  hostsList,
  refreshing = false
}) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Network Hosts ({hostsList.length})
        </Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Host ID</TableCell>
                <TableCell>MAC Address</TableCell>
                <TableCell>IP Address</TableCell>
                <TableCell>Connected Switch</TableCell>
                <TableCell>Port</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {hostsList.map((host, index) => (
                <TableRow key={host.id || index}>
                  <TableCell>{host.id}</TableCell>
                  <TableCell><code>{host.mac}</code></TableCell>
                  <TableCell>{host.ip}</TableCell>
                  <TableCell><code>{host.dpid}</code></TableCell>
                  <TableCell>{host.port}</TableCell>
                  <TableCell>
                    <Chip 
                      label={host.status || 'active'} 
                      color="success" 
                      size="small" 
                    />
                  </TableCell>
                </TableRow>
              ))}              {hostsList.length === 0 && !refreshing && (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    No hosts found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
};
