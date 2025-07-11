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
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import axios from 'axios';
import logger from '../utils/logger';

const API_BASE_URL = '/api';

function Settings() {
  const [config, setConfig] = useState({});
  const [editedConfig, setEditedConfig] = useState({});
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'success' });

  useEffect(() => {
    // Fetch current configuration
    logger.info('Fetching current simulation configuration');
    axios.get(`${API_BASE_URL}/config`)
      .then(response => {
        setConfig(response.data);
        setEditedConfig(response.data);
        logger.info('Configuration loaded successfully');
      })
      .catch(error => {
        logger.error('Error fetching configuration:', error);
        showNotification('Error loading configuration', 'error');
      });
  }, []);

  const showNotification = (message, severity = 'success') => {
    setNotification({ open: true, message, severity });
    logger.info(`Notification shown: ${message} (${severity})`);
  };

  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };


  const handleConfigChangeByPath = (path, value) => {
    setEditedConfig(prev => {
      const keys = path.split('.');
      const newConfig = { ...prev };
      let obj = newConfig;
      for (let i = 0; i < keys.length - 1; i++) {
        if (!obj[keys[i]]) obj[keys[i]] = {};
        obj = obj[keys[i]];
      }
      obj[keys[keys.length - 1]] = value;
      return newConfig;
    });
  };

  const handleSave = async () => {
    try {
      logger.info('Saving configuration changes');
      const response = await axios.post(`${API_BASE_URL}/config`, {
        config_data: editedConfig,
      });
      
      // Update the config with the server response
      setConfig(response.data.config);
      setEditedConfig(response.data.config);
      
      showNotification('Configuration saved successfully');
      logger.info('Configuration saved successfully');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Error saving configuration';
      logger.error('Error saving configuration:', error);
      showNotification(errorMessage, 'error');
    }
  };

  const handleReset = () => {
    logger.info('Resetting configuration to last saved state');
    setEditedConfig(config);
  };

  const renderConfigField = (key, value, parentKey = '', isTopLevel = false) => {
    const fullKey = parentKey ? `${parentKey}.${key}` : key;

    if (typeof value === 'boolean') {
      return (
        <TextField
          select
          fullWidth
          label={key}
          value={getValueByPath(editedConfig, fullKey) ? 'true' : 'false'}
          onChange={(e) => handleConfigChangeByPath(fullKey, e.target.value === 'true')}
          SelectProps={{ native: true }}
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
          value={getValueByPath(editedConfig, fullKey)}
          onChange={(e) => handleConfigChangeByPath(fullKey, Number(e.target.value))}
        />
      );
    } else if (typeof value === 'string') {
      return (
        <TextField
          fullWidth
          label={key}
          value={getValueByPath(editedConfig, fullKey)}
          onChange={(e) => handleConfigChangeByPath(fullKey, e.target.value)}
        />
      );
    } else if (Array.isArray(value)) {
      return (
        <TextField
          fullWidth
          label={key}
          value={getValueByPath(editedConfig, fullKey).join(', ')}
          onChange={(e) => handleConfigChangeByPath(fullKey, e.target.value.split(',').map(v => v.trim()))}
        />
      );
    } else if (typeof value === 'object' && value !== null) {
      // Accordion for all object levels
      return (
        <Accordion
          defaultExpanded
          sx={{
            mb: 2,
            boxShadow: 'none',
            border: '1px solid #444',
            background: 'transparent'
          }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant={isTopLevel ? 'h6' : 'subtitle2'}>{key}</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              {Object.entries(value).map(([childKey, childValue]) => (
                <Grid item xs={12} md={6} key={childKey}>
                  {renderConfigField(childKey, childValue, fullKey)}
                </Grid>
              ))}
            </Grid>
          </AccordionDetails>
        </Accordion>
      );
    } else {
      return null;
    }
  };

  const getValueByPath = (obj, path) => {
    return path.split('.').reduce((acc, part) => (acc && acc[part] !== undefined ? acc[part] : ''), obj);
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Simulation Configuration
        </Typography>

        <Grid container spacing={3}>
          {Object.entries(config).map(([key, value]) => (
            <Grid item xs={12} key={key}>
              {renderConfigField(key, value, '', true)}
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