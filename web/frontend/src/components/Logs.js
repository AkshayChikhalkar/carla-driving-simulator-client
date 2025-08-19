import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  CircularProgress,
  IconButton
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import Link from '@mui/material/Link';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';

const API_BASE_URL = process.env.NODE_ENV === 'production' ? window.location.origin : '';

function descendingComparator(a, b, orderBy) {
  if (b[orderBy] < a[orderBy]) {
    return -1;
  }
  if (b[orderBy] > a[orderBy]) {
    return 1;
  }
  return 0;
}

function getComparator(order, orderBy) {
  return order === 'desc'
    ? (a, b) => descendingComparator(a, b, orderBy)
    : (a, b) => -descendingComparator(a, b, orderBy);
}

function stableSort(array, comparator) {
  const stabilizedThis = array.map((el, index) => [el, index]);
  stabilizedThis.sort((a, b) => {
    const order = comparator(a[0], b[0]);
    if (order !== 0) return order;
    return a[1] - b[1];
  });
  return stabilizedThis.map((el) => el[0]);
}

function Logs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [order, setOrder] = useState('desc');
  const [orderBy, setOrderBy] = useState('created');
  const { filename } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/logs`);
        if (!response.ok) throw new Error('Failed to fetch logs');
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          const text = await response.text();
          throw new Error('Server did not return JSON. Response was: ' + text.slice(0, 100));
        }
        const data = await response.json();
        setLogs(data.logs || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, []);

  const handleRequestSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const handleDelete = async (filename) => {
    if (!window.confirm(`Delete log file "${filename}"?`)) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/logs/${encodeURIComponent(filename)}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Failed to delete');
      setLogs(logs => logs.filter(r => r.filename !== filename));
    } catch (err) {
      alert('Error deleting log: ' + err.message);
    }
  };

  if (filename) {
    return (
      <Box sx={{ maxWidth: 900, mx: 'auto', mt: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <IconButton onClick={() => navigate('/logs')} color="primary">
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h5" sx={{ ml: 1 }}>
            {filename}
          </Typography>
        </Box>
        <Paper sx={{ p: 1, minHeight: 600 }}>
          <iframe
            src={`${API_BASE_URL}/api/logs/${encodeURIComponent(filename)}`}
            title={filename}
            width="100%"
            height="600px"
            style={{ border: 'none', background: '#111' }}
          />
        </Paper>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 900, mx: 'auto', mt: 4 }}>
      <Typography variant="h4" gutterBottom>Log Files</Typography>
      <Paper sx={{ p: 2 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error">{error}</Typography>
        ) : logs.length === 0 ? (
          <Typography>No log files found.</Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'filename'}
                      direction={orderBy === 'filename' ? order : 'asc'}
                      onClick={() => handleRequestSort('filename')}
                    >
                      Filename
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>
                    <TableSortLabel
                      active={orderBy === 'created'}
                      direction={orderBy === 'created' ? order : 'asc'}
                      onClick={() => handleRequestSort('created')}
                    >
                      Created
                    </TableSortLabel>
                  </TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {stableSort(logs, getComparator(order, orderBy)).map((log) => (
                  <TableRow key={log.filename} hover>
                    <TableCell>
                      <Link
                        component={RouterLink}
                        to={`/logs/${encodeURIComponent(log.filename)}`}
                        underline="hover"
                        color="primary"
                        sx={{ cursor: 'pointer' }}
                      >
                        {log.filename}
                      </Link>
                    </TableCell>
                    <TableCell>{log.created}</TableCell>
                    <TableCell align="center">
                      <IconButton
                        color="primary"
                        component="a"
                        href={`${API_BASE_URL}/api/logs/${encodeURIComponent(log.filename)}`}
                        target="_blank"
                        rel="noopener"
                        aria-label={`Open ${log.filename}`}
                      >
                        <OpenInNewIcon />
                      </IconButton>
                      <IconButton
                        color="error"
                        sx={{ ml: 1 }}
                        onClick={() => handleDelete(log.filename)}
                        aria-label={`Delete ${log.filename}`}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  );
}

export default Logs; 
