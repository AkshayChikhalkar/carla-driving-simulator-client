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
  Button,
  IconButton
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import DeleteIcon from '@mui/icons-material/Delete';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import Link from '@mui/material/Link';

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

function Reports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [order, setOrder] = useState('desc');
  const [orderBy, setOrderBy] = useState('created');
  const { filename } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    // Fetch the list of reports from the backend
    const fetchReports = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/reports`);
        if (!response.ok) throw new Error('Failed to fetch reports');
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
          const text = await response.text();
          throw new Error('Server did not return JSON. Response was: ' + text.slice(0, 100));
        }
        const data = await response.json();
        setReports(data.reports || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchReports();
  }, []);

  const handleRequestSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const handleDelete = async (filename) => {
    if (!window.confirm(`Delete report "${filename}"?`)) return;
    try {
      const response = await fetch(`${API_BASE_URL}/api/reports/${encodeURIComponent(filename)}`, { method: 'DELETE' });
      if (!response.ok) throw new Error('Failed to delete');
      setReports(reports => reports.filter(r => r.filename !== filename));
    } catch (err) {
      alert('Error deleting report: ' + err.message);
    }
  };

  if (filename) {
    return (
      <Box sx={{ maxWidth: 900, mx: 'auto', mt: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <IconButton onClick={() => navigate('/reports')} color="primary">
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h5" sx={{ ml: 1 }}>
            {filename}
          </Typography>
        </Box>
        <Paper sx={{ p: 1, minHeight: 600 }}>
          <iframe
            src={`${API_BASE_URL}/api/reports/${encodeURIComponent(filename)}`}
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
      <Typography variant="h4" gutterBottom>Simulation Reports</Typography>
      <Paper sx={{ p: 2 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error">{error}</Typography>
        ) : reports.length === 0 ? (
          <Typography>No reports found.</Typography>
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
                {stableSort(reports, getComparator(order, orderBy)).map((report) => (
                  <TableRow key={report.filename} hover>
                    <TableCell>
                      <Link
                        component={RouterLink}
                        to={`/reports/${encodeURIComponent(report.filename)}`}
                        underline="hover"
                        color="primary"
                        sx={{ cursor: 'pointer' }}
                      >
                        {report.filename}
                      </Link>
                    </TableCell>
                    <TableCell>{report.created}</TableCell>
                    <TableCell align="center">
                      <IconButton
                        color="primary"
                        component={RouterLink}
                        to={`/reports/${encodeURIComponent(report.filename)}`}
                        aria-label={`Open ${report.filename}`}
                      >
                        <OpenInNewIcon />
                      </IconButton>
                      <IconButton
                        color="error"
                        sx={{ ml: 1 }}
                        onClick={() => handleDelete(report.filename)}
                        aria-label={`Delete ${report.filename}`}
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

export default Reports; 