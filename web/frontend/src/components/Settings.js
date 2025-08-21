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
  List,
  ListItemButton,
  ListItemText,
  Divider,
  Tooltip,
  IconButton
} from '@mui/material';
// Removed unused icon import
import RestartAltIcon from '@mui/icons-material/RestartAlt';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import logger from '../utils/logger';
import { APP_SETTINGS_CATEGORIES, SIM_SETTINGS_CATEGORIES, getValue, setValue } from '../utils/settingsSchema';
import Ajv from 'ajv';
import { buildSchemaFromCategories } from '../utils/buildSchema';
import { fetchJson } from '../utils/fetchJson';

const API_BASE_URL = '/api';

function Settings() {
  const [config, setConfig] = useState({});
  const [editedConfig, setEditedConfig] = useState({});
  const [notification, setNotification] = useState({ open: false, message: '', severity: 'success' });
  const [activeTab, setActiveTab] = useState('app'); // 'app' | 'simulation'

  // Compact, uniform TextField sizing across all input types
  const compactFieldSx = useMemo(() => ({
    '& .MuiInputBase-root': {
      height: 36,
      alignItems: 'center',
      fontSize: 13,
    },
    '& .MuiOutlinedInput-input': {
      paddingTop: '8px',
      paddingBottom: '8px',
      paddingLeft: '12px',
      paddingRight: '12px',
      height: 'unset',
      fontSize: 13,
    },
    '& .MuiSelect-select': {
      paddingTop: '8px !important',
      paddingBottom: '8px !important',
      paddingLeft: '12px !important',
      paddingRight: '40px !important',
      height: 'unset',
      display: 'block',
      fontSize: 13,
      lineHeight: '20px',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
    },
    '& .MuiInputLabel-root': {
      fontSize: 12,
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      maxWidth: '100%'
    },
    '& .MuiFormHelperText-root': { margin: 0 }
  }), []);

  useEffect(() => {
    // Fetch current configuration (using fetch for broad test compatibility)
    const load = async () => {
      try {
        logger.info('Fetching current simulation configuration');
        const data = await fetchJson(`${API_BASE_URL}/config`);
        setConfig(data);
        setEditedConfig(data);
        logger.info('Configuration loaded successfully');
      } catch (error) {
        logger.error('Error fetching configuration:', error);
        showNotification('Error loading configuration', 'error');
      }
    };
    load();
    // Load defaults for resetField hints without mutating server state
    const loadDefaults = async () => {
      try {
        const data = await fetchJson(`${API_BASE_URL}/config/defaults`);
        if (data) {
          if (data && data.config) setDefaults(data.config);
        }
      } catch {}
    };
    loadDefaults();
    // Mounted flag no longer used
  }, []);
  // --- Helpers ---
  // Removed unused computed keys to satisfy linter

  // renderRecursive removed (unused)


  // renderLeafField removed (unused)


  const showNotification = (message, severity = 'success') => {
    setNotification({ open: true, message, severity });
    logger.info(`Notification shown: ${message} (${severity})`);
  };

  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };


  const handleSave = async () => {
    try {
      logger.info('Saving configuration changes');
      // Split editedConfig into app and sim sections for API
      const appTopKeys = Array.from(new Set(APP_SETTINGS_CATEGORIES.flatMap(cat => cat.fields.map(f => f.path.split('.')[0]))));
      const simTopKeys = Array.from(new Set(SIM_SETTINGS_CATEGORIES.flatMap(cat => cat.fields.map(f => f.path.split('.')[0]))));
      const pick = (obj, keys) => keys.reduce((acc, k) => { if (obj && Object.prototype.hasOwnProperty.call(obj, k)) acc[k] = obj[k]; return acc; }, {});
      const app_config = pick(editedConfig, appTopKeys);
      const sim_config = pick(editedConfig, simTopKeys);

      // Validate with Ajv
      const ajv = new Ajv({ allErrors: true, strict: false });
      const appSchema = buildSchemaFromCategories(APP_SETTINGS_CATEGORIES);
      const simSchema = buildSchemaFromCategories(SIM_SETTINGS_CATEGORIES);
      const validateApp = ajv.compile(appSchema);
      const validateSim = ajv.compile(simSchema);
      const appValid = validateApp(app_config);
      const simValid = validateSim(sim_config);
      if (!appValid || !simValid) {
        showNotification('Validation failed. Please check highlighted fields.', 'error');
        return;
      }

      const data = await fetchJson(`${API_BASE_URL}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // Persist the full edited configuration so out-of-schema keys are not lost
        body: JSON.stringify({ app_config, sim_config: editedConfig })
      });
      const newConfig = data.config ?? editedConfig;
      setConfig(newConfig);
      setEditedConfig(newConfig);
      showNotification('Configuration saved successfully');
      logger.info('Configuration saved successfully');
    } catch (error) {
      logger.error('Error saving configuration:', error);
      showNotification('Error saving configuration', 'error');
    }
  };

  const handleReset = async () => {
    try {
      // Confirm
      if (!window.confirm('Reset all settings to server defaults? This will overwrite your unsaved changes.')) {
        return;
      }
      logger.info('Resetting configuration to defaults from DB');
      const res = await fetchJson(`${API_BASE_URL}/config/reset`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
      if (!res.ok) {
        let errMsg = `HTTP ${res.status}`;
        try { const err = await res.json(); errMsg = err?.detail || JSON.stringify(err); } catch {}
        showNotification(`Error resetting configuration: ${errMsg}`, 'error');
        return;
      }
      const data = await res.json();
      const newCfg = (data && data.config && Object.keys(data.config).length > 0) ? data.config : editedConfig;
      setConfig(newCfg);
      setEditedConfig(newCfg);
      showNotification('Configuration reset to defaults');
    } catch (e) {
      showNotification('Error resetting configuration', 'error');
    }
  };

  const [defaults, setDefaults] = useState({});
  const [catalog, setCatalog] = useState(null);

  useEffect(() => {
    const loadCatalog = async () => {
      try {
        // Try DB first
        let data = null;
        try {
          const resDb = await fetch('/api/carla/metadata/0.10.0');
          if (resDb.ok) {
            const row = await resDb.json();
            data = row.data || row;
          }
        } catch {}
        if (!data) {
          const resFile = await fetch('/carla_0100_catalog.json');
          if (resFile.ok) data = await resFile.json();
        }
        if (data) setCatalog(data);
      } catch {}
    };
    loadCatalog();
  }, []);

  const isModified = (path) => {
    const current = getValue(editedConfig, path);
    const original = getValue(config, path);
    return JSON.stringify(current) !== JSON.stringify(original);
  };

  const resetField = (path) => {
    const defVal = getValue(defaults, path, undefined);
    if (defVal !== undefined) {
      setEditedConfig(prev => setValue(prev, path, defVal));
    } else {
      // Fallback to last saved config; if missing there, keep current value instead of blank
      const currentVal = getValue(editedConfig, path);
      const origVal = getValue(config, path, currentVal);
      setEditedConfig(prev => setValue(prev, path, origVal));
    }
  };

  const renderField = (field) => {
    const { path, label, type, options, optionsFromCatalog, min, max, step } = field;
    const value = getValue(editedConfig, path, type === 'boolean' ? false : '');

    if (type === 'boolean') {
      return (
        <TextField
          select
          variant="outlined"
          fullWidth
          size="small"
          margin="dense"
          label={label}
          value={value ? 'true' : 'false'}
          onChange={(e) => setEditedConfig(prev => setValue(prev, path, e.target.value === 'true'))}
          SelectProps={{ native: true }}
          sx={compactFieldSx}
          inputProps={{ 'aria-label': label }}
        >
          <option value="true">Enabled</option>
          <option value="false">Disabled</option>
        </TextField>
      );
    }
    if (type === 'enum') {
      let resolvedOptions = options || [];
      if (!resolvedOptions.length && optionsFromCatalog && catalog) {
        if (optionsFromCatalog === 'maps') resolvedOptions = catalog.maps || [];
        if (optionsFromCatalog === 'vehicles') resolvedOptions = catalog.blueprints?.vehicles || [];
        if (optionsFromCatalog === 'sensors') resolvedOptions = catalog.blueprints?.sensors || [];
        if (optionsFromCatalog === 'walkers') resolvedOptions = catalog.blueprints?.walkers || [];
      }
      return (
        <TextField
          select
          variant="outlined"
          fullWidth
          size="small"
          margin="dense"
          label={label}
          value={value}
          onChange={(e) => setEditedConfig(prev => setValue(prev, path, e.target.value))}
          SelectProps={{ native: true }}
          sx={compactFieldSx}
          inputProps={{ 'aria-label': label }}
          InputLabelProps={{ shrink: true }}
        >
          {resolvedOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
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
          label={label}
          value={value}
          onChange={(e) => setEditedConfig(prev => setValue(prev, path, Number(e.target.value)))}
          sx={compactFieldSx}
          FormHelperTextProps={{ sx: { display: 'none' } }}
          InputLabelProps={{ shrink: true }}
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
        label={label}
        value={value}
        onChange={(e) => setEditedConfig(prev => setValue(prev, path, e.target.value))}
        sx={compactFieldSx}
        InputLabelProps={{ shrink: true }}
      />
    );
  };

  // --- Advanced blueprint-driven editors (CARLA 0.10.0) ---
  const findBlueprint = (bpId) => {
    if (!catalog) return null;
    if (catalog.blueprints?.all) {
      return catalog.blueprints.all.find((b) => b.id === bpId) || null;
    }
    return null;
  };

  const renderAttributeEditor = (fullPath, attr) => {
    const currentVal = getValue(editedConfig, fullPath, undefined);
    const attrType = (attr.type || '').toLowerCase();
    const options = Array.isArray(attr.recommended_values) ? attr.recommended_values : [];
    if (options.length > 0) {
      return (
        <TextField select variant="outlined" fullWidth size="small" margin="dense" label={attr.id}
          value={currentVal !== undefined ? currentVal : attr.value}
          onChange={(e) => setEditedConfig((prev) => setValue(prev, fullPath, e.target.value))}
          SelectProps={{ native: true }} sx={compactFieldSx}
          InputLabelProps={{ shrink: true }}>
          {options.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </TextField>
      );
    }
    if (attrType === 'bool' || attrType === 'boolean') {
      const boolVal = String(currentVal !== undefined ? currentVal : attr.value) === 'true';
      return (
        <TextField select variant="outlined" fullWidth size="small" margin="dense" label={attr.id}
          value={boolVal ? 'true' : 'false'}
          onChange={(e) => setEditedConfig((prev) => setValue(prev, fullPath, e.target.value === 'true'))}
          SelectProps={{ native: true }} sx={compactFieldSx}
          InputLabelProps={{ shrink: true }}>
          <option value="true">True</option>
          <option value="false">False</option>
        </TextField>
      );
    }
    if (attrType === 'int' || attrType === 'float' || attrType === 'double') {
      return (
        <TextField type="number" variant="outlined" fullWidth size="small" margin="dense" label={attr.id}
          value={currentVal !== undefined ? currentVal : attr.value}
          onChange={(e) => setEditedConfig((prev) => setValue(prev, fullPath, Number(e.target.value)))}
          sx={compactFieldSx}
          InputLabelProps={{ shrink: true }}
        />
      );
    }
    return (
      <TextField variant="outlined" fullWidth size="small" margin="dense" label={attr.id}
        value={currentVal !== undefined ? currentVal : (attr.value ?? '')}
        onChange={(e) => setEditedConfig((prev) => setValue(prev, fullPath, e.target.value))}
        sx={compactFieldSx}
        InputLabelProps={{ shrink: true }}
      />
    );
  };

  const renderBlueprintAttributes = (pathPrefix, blueprintId) => {
    const bp = findBlueprint(blueprintId);
    if (!bp) return null;
    return (
      <Grid container spacing={1.5}>
        {bp.attributes.map((attr) => (
          <Grid item xs={12} md={6} key={`${pathPrefix}.attributes.${attr.id}`}>
            {renderAttributeEditor(`${pathPrefix}.attributes.${attr.id}`, attr)}
          </Grid>
        ))}
      </Grid>
    );
  };

  // compact styles (currently unused)

  // Sidebar helpers
  const [activeSection, setActiveSection] = useState('');
  useEffect(() => {
    const keys = activeTab === 'app' ? APP_SETTINGS_CATEGORIES.map(c => c.key) : SIM_SETTINGS_CATEGORIES.map(c => c.key);
    const observers = [];
    keys.forEach((k) => {
      const el = document.getElementById(`sec-${k}`);
      if (!el) return;
      const obs = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActiveSection(k);
        });
      }, { root: null, rootMargin: '0px 0px -70% 0px', threshold: 0.0 });
      obs.observe(el);
      observers.push(obs);
    });
    return () => observers.forEach(o => o.disconnect());
  }, [activeTab, config]);

  const handleJump = (key) => {
    const el = document.getElementById(`sec-${key}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const sidebarItems = activeTab === 'app'
    ? APP_SETTINGS_CATEGORIES.map(c => ({ key: c.key, label: c.label }))
    : SIM_SETTINGS_CATEGORIES.map(c => ({ key: c.key, label: c.label }));

  return (
    <Box sx={{ flexGrow: 1, maxWidth: 1300, mx: 'auto', px: 2 }}>
      <Paper sx={{ p: 2 }} elevation={0}>
        <Typography variant="h6" gutterBottom>
          Settings
        </Typography>
        <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)} sx={{ mb: 1 }}>
          <Tab value="app" label="Application" />
          <Tab value="simulation" label="Simulation" />
        </Tabs>
        {activeTab === 'simulation' && catalog && catalog.carla_version && catalog.carla_version !== '0.10.0' && (
          <Alert severity="warning" sx={{ mb: 1.5 }}>
            Detected CARLA catalog version {catalog.carla_version}. This UI targets 0.10.0; options may differ.
          </Alert>
        )}

        {/* Toolbar removed: no search or filter as requested */}

        <Grid container spacing={2}>
          <Grid item xs={12} md={3} lg={3}>
            <Box sx={{ position: 'sticky', top: 12 }}>
              <Paper elevation={0} sx={{ bgcolor: 'transparent', border: 'none' }}>
                <List dense>
                  {sidebarItems.map((item, idx) => (
                    <React.Fragment key={item.key}>
                      <ListItemButton selected={activeSection === item.key} onClick={() => handleJump(item.key)}>
                        <ListItemText primary={item.label} primaryTypographyProps={{ noWrap: true }} />
                      </ListItemButton>
                      {idx < sidebarItems.length - 1 && <Divider component="li" sx={{ opacity: 0.2 }} />}
                    </React.Fragment>
                  ))}
                </List>
              </Paper>
            </Box>
          </Grid>
          <Grid item xs={12} md={9} lg={9}>
            {activeTab === 'app' ? (
              <Grid container spacing={2}>
                {APP_SETTINGS_CATEGORIES.map(cat => (
                  <Grid item xs={12} key={cat.key} id={`sec-${cat.key}`}>
                    <Typography variant="subtitle2" sx={{ mb: 0.5 }}>{cat.label}</Typography>
                    <Grid container spacing={1.5}>
                      {cat.fields.map(field => (
                        <Grid item xs={12} md={6} key={`app-${field.path}`}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Box sx={{ flex: 1 }}>
                              {renderField(field)}
                            </Box>
                            {isModified(field.path) && (
                              <Typography variant="caption" color="warning.main" sx={{ whiteSpace: 'nowrap' }}>Modified</Typography>
                            )}
                            <Tooltip title="Reset to default" arrow>
                              <IconButton size="small" onClick={() => resetField(field.path)}>
                                <RestartAltIcon fontSize="inherit" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                          {field.description && (
                            <Typography variant="caption" color="text.secondary">{field.description}</Typography>
                          )}
                        </Grid>
                      ))}
                    </Grid>
                    <Divider sx={{ my: 2, opacity: 0.2 }} />
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Grid container spacing={2}>
                {SIM_SETTINGS_CATEGORIES.map(cat => (
                  <Grid item xs={12} key={cat.key} id={`sec-${cat.key}`}>
                    <Typography variant="subtitle2" sx={{ mb: 0.5 }}>{cat.label}</Typography>
                    <Grid container spacing={1.5}>
                      {cat.fields.map(field => (
                        <Grid item xs={12} md={6} key={`sim-${field.path}`}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Box sx={{ flex: 1 }}>
                              {renderField(field)}
                            </Box>
                            {isModified(field.path) && (
                              <Typography variant="caption" color="warning.main" sx={{ whiteSpace: 'nowrap' }}>Modified</Typography>
                            )}
                            <Tooltip title="Reset to default" arrow>
                              <IconButton size="small" onClick={() => resetField(field.path)}>
                                <RestartAltIcon fontSize="inherit" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                          {field.description && (
                            <Typography variant="caption" color="text.secondary">{field.description}</Typography>
                          )}
                        </Grid>
                      ))}
                    </Grid>
                    {cat.key === 'advanced' && (
                      <Box sx={{ mt: 1 }}>
                        {/* Vehicle blueprint attributes */}
                        {getValue(editedConfig, 'advanced.vehicle_blueprint') && (
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="body2" sx={{ mb: 1 }}>Vehicle Blueprint Attributes</Typography>
                            {renderBlueprintAttributes('advanced.vehicle', getValue(editedConfig, 'advanced.vehicle_blueprint'))}
                          </Box>
                        )}
                        {/* Sensor blueprint attributes */}
                        {getValue(editedConfig, 'advanced.sensor_blueprint') && (
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="body2" sx={{ mb: 1 }}>Sensor Blueprint Attributes</Typography>
                            {renderBlueprintAttributes('advanced.sensor', getValue(editedConfig, 'advanced.sensor_blueprint'))}
                          </Box>
                        )}
                        {/* Walker blueprint attributes */}
                        {getValue(editedConfig, 'advanced.walker_blueprint') && (
                          <Box sx={{ mb: 2 }}>
                            <Typography variant="body2" sx={{ mb: 1 }}>Walker Blueprint Attributes</Typography>
                            {renderBlueprintAttributes('advanced.walker', getValue(editedConfig, 'advanced.walker_blueprint'))}
                          </Box>
                        )}
                      </Box>
                    )}
                    <Divider sx={{ my: 2, opacity: 0.2 }} />
                  </Grid>
                ))}
              </Grid>
            )}

            <Box sx={{ mt: 2, display: 'flex', gap: 1.5 }}>
              <Button
                variant="contained"
                color="primary"
                onClick={handleSave}
                size="small">
                Save Settings
              </Button>
              <Button
                variant="outlined"
                onClick={handleReset}
                size="small">
                Reset
              </Button>
            </Box>
          </Grid>
        </Grid>
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
