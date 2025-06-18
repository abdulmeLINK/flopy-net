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

interface NetworkSwitchesTabProps {
  switchesList: any[];
  refreshing?: boolean;
}

export const NetworkSwitchesTab: React.FC<NetworkSwitchesTabProps> = ({
  switchesList,
  refreshing = false
}) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Network Switches ({switchesList.length})
        </Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Switch ID</TableCell>
                <TableCell>DPID</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Ports</TableCell>
                <TableCell>Type</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {switchesList.map((switch_item, index) => (
                <TableRow key={switch_item.id || index}>
                  <TableCell>{switch_item.id}</TableCell>
                  <TableCell><code>{switch_item.dpid}</code></TableCell>
                  <TableCell>
                    <Chip 
                      label={switch_item.status || 'active'} 
                      color="success" 
                      size="small" 
                    />
                  </TableCell>
                  <TableCell>{switch_item.ports?.length || 0}</TableCell>
                  <TableCell>{switch_item.type}</TableCell>
                </TableRow>
              ))}              {switchesList.length === 0 && !refreshing && (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    No switches found
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
