import { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  Typography,
  Toolbar,
  IconButton,
  Tooltip,
  TextField,
  InputAdornment
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';

type Order = 'asc' | 'desc';

interface Column {
  id: string;
  label: string;
  minWidth?: number;
  maxWidth?: number;
  align?: 'left' | 'right' | 'center';
  format?: (value: any, row?: any) => React.ReactNode;
}

interface DataTableProps {
  columns: Column[];
  data: any[];
  title?: string;
  emptyMessage?: string;
  onRowClick?: (row: any) => void;
  getRowId?: (row: any) => string;
  onRefresh?: () => void;
  searchEnabled?: boolean;
  initialSortBy?: string;
  initialSortDirection?: Order;
  selectedRowId?: string | null;
  onRowSelect?: (rowId: string | null) => void;
}

/**
 * A reusable data table component with sorting, pagination, and optional search.
 */
const DataTable = ({
  columns,
  data,
  title,
  emptyMessage = 'No data available',
  onRowClick,
  getRowId,
  onRefresh,
  searchEnabled = true,
  initialSortBy,
  initialSortDirection = 'desc',
  selectedRowId,
  onRowSelect
}: DataTableProps) => {
  const [order, setOrder] = useState<Order>(initialSortDirection);
  const [orderBy, setOrderBy] = useState<string>(initialSortBy || columns[0]?.id || '');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');

  // Reset page when data changes
  useEffect(() => {
    setPage(0);
  }, [data.length]);

  // Handle sort request
  const handleRequestSort = (property: string) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  // Handle page change
  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  // Handle rows per page change
  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Handle search input change
  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
    setPage(0);
  };

  // Filtered and sorted data
  const filteredAndSortedData = useMemo(() => {
    try {
      // Ensure data is an array
      const safeData = Array.isArray(data) ? data : [];
      
      // Filter data by search query
      let filteredData = safeData;
      if (searchQuery) {
        const lowercaseQuery = searchQuery.toLowerCase();
        filteredData = safeData.filter(row => {
          if (!row || typeof row !== 'object') return false;
          return columns.some(column => {
            try {
              const value = row[column.id];
              if (value == null) return false;
              return String(value).toLowerCase().includes(lowercaseQuery);
            } catch (err) {
              console.error('Error accessing column value:', err);
              return false;
            }
          });
        });
      }

      // Sort data
      if (!orderBy) return filteredData;

      return [...filteredData].sort((a, b) => {
        try {
          if (!a || !b || typeof a !== 'object' || typeof b !== 'object') {
            return 0;
          }
          
          const aValue = a[orderBy];
          const bValue = b[orderBy];

          // Handle null and undefined values
          if (aValue == null && bValue == null) return 0;
          if (aValue == null) return order === 'asc' ? -1 : 1;
          if (bValue == null) return order === 'asc' ? 1 : -1;

          // Sort by string or number
          if (typeof aValue === 'string' && typeof bValue === 'string') {
            return order === 'asc' 
              ? aValue.localeCompare(bValue) 
              : bValue.localeCompare(aValue);
          }

          // Default number comparison
          return order === 'asc' 
            ? (aValue < bValue ? -1 : aValue > bValue ? 1 : 0)
            : (bValue < aValue ? -1 : bValue > aValue ? 1 : 0);
        } catch (err) {
          console.error('Error comparing row values:', err);
          return 0;
        }
      });
    } catch (err) {
      console.error('Error filtering/sorting data:', err);
      return [];
    }
  }, [data, columns, searchQuery, orderBy, order]);

  // Paginated data
  const paginatedData = useMemo(() => {
    return filteredAndSortedData.slice(
      page * rowsPerPage,
      page * rowsPerPage + rowsPerPage
    );
  }, [filteredAndSortedData, page, rowsPerPage]);

  return (
    <Paper sx={{ width: '100%', overflow: 'hidden' }}>
      {/* Table toolbar with title and search */}
      <Toolbar
        sx={{
          pl: { sm: 2 },
          pr: { xs: 1, sm: 1 },
          justifyContent: 'space-between'
        }}
      >
        <Typography
          variant="h6"
          id="tableTitle"
          component="div"
        >
          {title}
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          {searchEnabled && (
            <TextField
              size="small"
              variant="outlined"
              placeholder="Search..."
              value={searchQuery}
              onChange={handleSearchChange}
              sx={{ mr: 1 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          )}

          {onRefresh && (
            <Tooltip title="Refresh">
              <IconButton onClick={onRefresh} size="large">
                <RefreshIcon />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      </Toolbar>

      {/* Table content */}
      <TableContainer sx={{ maxHeight: 600 }}>
        <Table stickyHeader aria-label="sticky table">
          {/* Table header */}
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell
                  key={column.id}
                  align={column.align || 'left'}
                  style={{ 
                    minWidth: column.minWidth,
                    maxWidth: column.maxWidth
                  }}
                >
                  <TableSortLabel
                    active={orderBy === column.id}
                    direction={orderBy === column.id ? order : 'asc'}
                    onClick={() => handleRequestSort(column.id)}
                  >
                    {column.label}
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>

          {/* Table body */}
          <TableBody>
            {paginatedData.length > 0 ? (
              paginatedData.map((row, index) => {
                const rowId = getRowId ? getRowId(row) : String(index);
                const isSelected = selectedRowId === rowId;
                
                const handleRowClick = () => {
                  if (onRowClick) {
                    onRowClick(row);
                  }
                  if (onRowSelect) {
                    onRowSelect(isSelected ? null : rowId);
                  }
                };
                
                return (
                  <TableRow
                    key={rowId}
                    onClick={onRowClick ? handleRowClick : undefined}
                    role={onRowClick ? 'button' : undefined}
                    sx={{ 
                      cursor: onRowClick ? 'pointer' : 'default',
                      backgroundColor: isSelected 
                        ? 'rgba(25, 118, 210, 0.08)' 
                        : 'transparent',
                      '&:hover': onRowClick ? {
                        backgroundColor: isSelected 
                          ? 'rgba(25, 118, 210, 0.12)' 
                          : 'rgba(0, 0, 0, 0.04)',
                        '& .MuiTableCell-root': {
                          borderBottom: '1px solid rgba(224, 224, 224, 1)'
                        }
                      } : {},
                      '&:active': onRowClick ? {
                        backgroundColor: 'rgba(25, 118, 210, 0.16)',
                      } : {},
                      transition: 'background-color 0.15s ease-in-out',
                      '&:nth-of-type(even)': !isSelected ? {
                        backgroundColor: 'rgba(0, 0, 0, 0.02)'
                      } : {},
                      ...(isSelected && {
                        borderLeft: '3px solid #1976d2',
                        '& .MuiTableCell-root:first-of-type': {
                          paddingLeft: '13px' // Compensate for border
                        }
                      })
                    }}
                  >
                    {columns.map((column) => {
                      try {
                        const value = row && typeof row === 'object' ? row[column.id] : undefined;
                        return (
                          <TableCell key={column.id} align={column.align || 'left'}>
                            {column.format 
                              ? column.format(value, row) 
                              : (value !== null && value !== undefined ? value : '')}
                          </TableCell>
                        );
                      } catch (err) {
                        console.error('Error rendering table cell:', err);
                        return (
                          <TableCell key={column.id} align={column.align || 'left'}>
                            Error
                          </TableCell>
                        );
                      }
                    })}
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} align="center">
                  {emptyMessage}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      <TablePagination
        rowsPerPageOptions={[5, 10, 25, 50, 100]}
        component="div"
        count={filteredAndSortedData.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />
    </Paper>
  );
};

export default DataTable; 