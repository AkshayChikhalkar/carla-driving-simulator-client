import React, { useState, useEffect, useMemo } from 'react';
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
import { SETTINGS_CATEGORIES, getValue, setValue } from '../utils/settingsSchema';

const API_BASE_URL = '/api';

function Settings() {
  const [config, setConfig] = useState({});
  const [editedConfig, setEditedConfig] = useState({});
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'success' });
  const [search, setSearch] = useState('');
  const [showAll, setShowAll] = useState(true); // VSCode-like: show all vs schema categories

  // Compact, uniform TextField sizing across all input types
  const compactFieldSx = useMemo(() => ({
    '& .MuiInputBase-root': { height: 36 },
    '& .MuiOutlinedInput-input': { paddingTop: '6px', paddingBottom: '6px', fontSize: 13 },
    '& .MuiSelect-select': { paddingTop: '6px', paddingBottom: '6px', fontSize: 13 },
    '& .MuiInputLabel-root': { fontSize: 12, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '100%' },
    '& .MuiFormHelperText-root': { margin: 0 }
  }), []);

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
  // --- VSCode-like helpers ---
  const topLevelKeys = useMemo(() => Object.keys(config || {}), [config]);

  const pathIncludes = (path, value) => {
    if (!search) return true;
    const q = search.toLowerCase();
    if (path.toLowerCase().includes(q)) return true;
    if (value !== null && value !== undefined) {
      try {
        const s = Array.isArray(value) ? value.join(', ') : typeof value === 'object' ? JSON.stringify(value) : String(value);
        return s.toLowerCase().includes(q);
      } catch { /* noop */ }
    }
    return false;
  };

  const renderRecursive = (obj, parentPath = '') => {
    if (obj === null || obj === undefined) return null;
    if (typeof obj !== 'object' || Array.isArray(obj)) {
      // Primitive or array is handled by field renderer, not here
      return null;
    }
    return (
      <Grid container spacing={2}>
        {Object.entries(obj).map(([k, v]) => {
          const full = parentPath ? `${parentPath}.${k}` : k;
          if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
            // Nested group accordion
            const anyMatch = search ? hasAnyMatch(v, full) : true;
            if (!anyMatch) return null;
            return (
              <Grid item xs={12} key={full}>
                <Accordion defaultExpanded={!!search} sx={{ mb: 1, boxShadow: 'none', border: '1px solid #444', background: 'transparent' }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="subtitle1">{full}</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    {renderRecursive(v, full)}
                  </AccordionDetails>
                </Accordion>
              </Grid>
            );
          }
          // Leaf field
          if (!pathIncludes(full, v)) return null;
          return (
            <Grid item xs={12} md={6} key={full}>
              {renderLeafField(full, v)}
            </Grid>
          );
        })}
      </Grid>
    );
  };

  const hasAnyMatch = (obj, base) => {
    if (typeof obj !== 'object' || obj === null) return pathIncludes(base, obj);
    return Object.entries(obj).some(([k, v]) => {
      const full = base ? `${base}.${k}` : k;
      if (typeof v === 'object' && v !== null) return hasAnyMatch(v, full);
      return pathIncludes(full, v);
    });
  };

  const renderLeafField = (path, value) => {
    if (typeof value === 'boolean') {
      return (
        <TextField
          select
          variant="outlined"
          fullWidth
          size="small"
          margin="dense"
          value={value ? 'true' : 'false'}
          onChange={(e) => handleConfigChangeByPath(path, e.target.value === 'true')}
          SelectProps={{ native: true }}
          sx={compactFieldSx}
          inputProps={{ 'aria-label': path }}
        >
          <option value="true">True</option>
          <option value="false">False</option>
        </TextField>
      );
    }
    if (typeof value === 'number') {
      return (
        <TextField
          variant="outlined"
          fullWidth
          type="number"
          size="small"
          margin="dense"
          placeholder={path}
          value={value}
          onChange={(e) => handleConfigChangeByPath(path, Number(e.target.value))}
          sx={compactFieldSx}
          inputProps={{ 'aria-label': path }}
        />
      );
    }
    if (typeof value === 'string') {
      return (
        <TextField
          variant="outlined"
          fullWidth
          size="small"
          margin="dense"
          placeholder={path}
          value={value}
          onChange={(e) => handleConfigChangeByPath(path, e.target.value)}
          sx={compactFieldSx}
          inputProps={{ 'aria-label': path }}
        />
      );
    }
    if (Array.isArray(value)) {
      return (
        <TextField
          variant="outlined"
          fullWidth
          size="small"
          margin="dense"
          placeholder={path}
          value={value.join(', ')}
          onChange={(e) => handleConfigChangeByPath(path, e.target.value.split(',').map(v => v.trim()))}
          sx={compactFieldSx}
          inputProps={{ 'aria-label': path }}
        />
      );
    }
    return null;
  };


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

  const renderField = (field) => {
    const { path, label, type, options, min, max, step } = field;
    const value = getValue(editedConfig, path, type === 'boolean' ? false : '');

    if (type === 'boolean') {
      return (
        <TextField
          select
          variant="outlined"
          fullWidth
          size="small"
          margin="dense"
          placeholder={label}
          value={value ? 'true' : 'false'}
          onChange={(e) => setEditedConfig(prev => setValue(prev, path, e.target.value === 'true'))}
          SelectProps={{ native: true }}
          sx={compactFieldSx}
          inputProps={{ 'aria-label': label }}
        >
          <option value="true">True</option>
          <option value="false">False</option>
        </TextField>
      );
    }
    if (type === 'enum') {
      return (
        <TextField
          select
          variant="outlined"
          fullWidth
          size="small"
          margin="dense"
          placeholder={label}
          value={value}
          onChange={(e) => setEditedConfig(prev => setValue(prev, path, e.target.value))}
          SelectProps={{ native: true }}
          sx={compactFieldSx}
          inputProps={{ 'aria-label': label }}
        >
          {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
        </TextField>
      );
    }
    if (type === 'number') {
      return (
        <TextField
          variant="outlined"
          fullWidth
          type="number"
          size="small"
          margin="dense"
          inputProps={{ min, max, step }}
          placeholder={label}
          value={value}
          onChange={(e) => setEditedConfig(prev => setValue(prev, path, Number(e.target.value)))}
          sx={compactFieldSx}
        />
      );
    }
    // default: string
    return (
      <TextField
        variant="outlined"
        fullWidth
        size="small"
        margin="dense"
        placeholder={label}
        value={value}
        onChange={(e) => setEditedConfig(prev => setValue(prev, path, e.target.value))}
        sx={compactFieldSx}
      />
    );
  };

  // compact styles
  const accordionSx = { mb: 1.5, boxShadow: 'none', border: '1px solid #444', background: 'transparent' };
  const summarySx = { minHeight: 36, '& .MuiAccordionSummary-content': { my: 0 } };

  return (
    <Box sx={{ flexGrow: 1, maxWidth: 1100, mx: 'auto', px: 2 }}>
      <Paper sx={{ p: 2 }} elevation={0}>
        <Typography variant="h6" gutterBottom>
          Simulation Configuration
        </Typography>

        {/* VSCode-like toolbar */}
        <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center', mb: 1.5 }}>
          <TextField
            placeholder="Search settings"
            size="small"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            sx={{ minWidth: 260 }}
          />
          <TextField select size="small" value={showAll ? 'all' : 'recommended'} onChange={(e) => setShowAll(e.target.value === 'all')} SelectProps={{ native: true }}>
            <option value="all">Show all</option>
            <option value="recommended">Recommended</option>
          </TextField>
        </Box>

        {showAll ? (
          <Grid container spacing={1.5}>
            {topLevelKeys.map((catKey) => (
              <Grid item xs={12} key={catKey} id={`sec-${catKey}`}>
                <Accordion defaultExpanded={!!search} sx={accordionSx}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={summarySx}>
                    <Typography variant="subtitle1">{catKey}</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    {renderRecursive(config[catKey], catKey)}
                  </AccordionDetails>
                </Accordion>
              </Grid>
            ))}
          </Grid>
        ) : (
          <Grid container spacing={1.5}>
            {SETTINGS_CATEGORIES.map(cat => (
              <Grid item xs={12} key={cat.key}>
                <Accordion defaultExpanded sx={accordionSx}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={summarySx}>
                    <Typography variant="subtitle1">{cat.label}</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={1.5}>
                      {cat.fields.map(field => (
                        <Grid item xs={12} md={6} key={field.path}>
                          {renderField(field)}
                        </Grid>
                      ))}
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              </Grid>
            ))}
            {/* Scenarios: render full nested content in curated view for completeness */}
            {config && config.scenarios && (
              <Grid item xs={12} key="scenarios">
                <Accordion defaultExpanded sx={accordionSx}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={summarySx}>
                    <Typography variant="subtitle1">scenarios</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    {renderRecursive(config.scenarios, 'scenarios')}
                  </AccordionDetails>
                </Accordion>
              </Grid>
            )}
          </Grid>
        )}

        <Box sx={{ mt: 2, display: 'flex', gap: 1.5 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={handleSave}
            size="small">
            Save Changes
          </Button>
          <Button
            variant="outlined"
            onClick={handleReset}
            size="small">
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
