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

interface NetworkLinksTabProps {
  linksList: any[];
  refreshing?: boolean;
}

export const NetworkLinksTab: React.FC<NetworkLinksTabProps> = ({
  linksList,
  refreshing = false
}) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Network Links ({linksList.length})
        </Typography>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Link ID</TableCell>
                <TableCell>Source</TableCell>
                <TableCell>Target</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Type</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {linksList.map((link, index) => (
                <TableRow key={link.id || index}>
                  <TableCell>{link.id || `link-${index}`}</TableCell>
                  <TableCell>{link.source}</TableCell>
                  <TableCell>{link.target}</TableCell>
                  <TableCell>
                    <Chip 
                      label={link.status || 'active'} 
                      color="success" 
                      size="small" 
                    />
                  </TableCell>
                  <TableCell>{link.type || 'direct'}</TableCell>
                </TableRow>
              ))}              {linksList.length === 0 && !refreshing && (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    No links found
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
