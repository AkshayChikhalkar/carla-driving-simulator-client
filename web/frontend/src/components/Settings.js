import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  Alert,
  Snackbar,
} from '@mui/material';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

function Settings() {
  const [config, setConfig] = useState({});
  const [editedConfig, setEditedConfig] = useState({});
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'success' });

  useEffect(() => {
    // Fetch current configuration
    axios.get(`${API_BASE_URL}/config`)
      .then(response => {
        setConfig(response.data);
        setEditedConfig(response.data);
      })
      .catch(error => {
        console.error('Error fetching configuration:', error);
        showNotification('Error loading configuration', 'error');
      });
  }, []);

  const showNotification = (message, severity = 'success') => {
    setNotification({ open: true, message, severity });
  };

  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };

  const handleConfigChange = (key, value) => {
    setEditedConfig(prev => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSave = async () => {
    try {
      await axios.post(`${API_BASE_URL}/config`, {
        config_data: editedConfig,
      });
      showNotification('Configuration saved successfully');
      setConfig(editedConfig);
    } catch (error) {
      console.error('Error saving configuration:', error);
      showNotification('Error saving configuration', 'error');
    }
  };

  const handleReset = () => {
    setEditedConfig(config);
  };

  const renderConfigField = (key, value) => {
    if (typeof value === 'boolean') {
      return (
        <TextField
          select
          fullWidth
          label={key}
          value={editedConfig[key] ? 'true' : 'false'}
          onChange={(e) => handleConfigChange(key, e.target.value === 'true')}
          SelectProps={{
            native: true,
          }}
        >
          <option value="true">True</option>
          <option value="false">False</option>
        </TextField>
      );
    } else if (typeof value === 'number') {
      return (
        <TextField
          fullWidth
          type="number"
          label={key}
          value={editedConfig[key]}
          onChange={(e) => handleConfigChange(key, Number(e.target.value))}
        />
      );
    } else {
      return (
        <TextField
          fullWidth
          label={key}
          value={editedConfig[key]}
          onChange={(e) => handleConfigChange(key, e.target.value)}
        />
      );
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Simulation Configuration
        </Typography>

        <Grid container spacing={3}>
          {Object.entries(config).map(([key, value]) => (
            <Grid item xs={12} md={6} key={key}>
              {renderConfigField(key, value)}
            </Grid>
          ))}
        </Grid>

        <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={handleSave}
          >
            Save Changes
          </Button>
          <Button
            variant="outlined"
            onClick={handleReset}
          >
            Reset
          </Button>
        </Box>
      </Paper>

      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleCloseNotification}
      >
        <Alert
          onClose={handleCloseNotification}
          severity={notification.severity}
          sx={{ width: '100%' }}
        >
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default Settings; 