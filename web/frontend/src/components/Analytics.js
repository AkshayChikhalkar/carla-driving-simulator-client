import React, { useEffect, useState } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Paper,
  Typography
} from '@mui/material';
import {
  Timeline as TimelineIcon,
  Speed as SpeedIcon,
  LocationOn as LocationIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';
import { fetchJson } from '../utils/fetchJson';

// Prefer same-origin Grafana if proxied, else fallback to env
const API_BASE_URL = '/api';
const GRAFANA_PARAMS = '?orgId=1&kiosk';

// Read Grafana base URL from backend config at runtime
// Fallbacks: REACT_APP_GRAFANA_BASE_URL env, then proxied same-origin path
const useGrafanaBaseUrl = () => {
  const [grafanaBaseUrl, setGrafanaBaseUrl] = useState(process.env.REACT_APP_GRAFANA_BASE_URL || '/grafana/d');
  const [configError, setConfigError] = useState(null);
  
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const headers = {};
        const storedTenant = localStorage.getItem('tenant_id');
        if (storedTenant) headers['X-Tenant-Id'] = storedTenant;
        const resp = await fetchJson(`${API_BASE_URL}/config`, { headers });
        const data = await resp.json();
        if (data && data.analytics && data.analytics.grafana_base_url) {
          setGrafanaBaseUrl(data.analytics.grafana_base_url);
          setConfigError(null);
        }
      } catch (error) {
        console.warn('Failed to load Grafana config:', error.message);
        setConfigError('Grafana configuration not available. Using default URL.');
        // keep default fallback
      }
    };
    fetchConfig();
  }, []);
  return { grafanaBaseUrl, configError };
};

function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`analytics-tabpanel-${index}`}
      aria-labelledby={`analytics-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ pt: 0.5 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const Analytics = () => {
  const [selectedTab, setSelectedTab] = useState(0);
  const { grafanaBaseUrl, configError } = useGrafanaBaseUrl();

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
  };

  const dashboardConfigs = [
    {
      id: 'metrics',
      label: 'Simulator Metrics',
      icon: <AssessmentIcon />,
      url: `${grafanaBaseUrl}/carla-simulator-metrics/carla-simulator-metrics${GRAFANA_PARAMS}`,
      description: 'Vehicle speed, navigation metrics, position, and controls'
    },
    {
      id: 'performance',
      label: 'Performance Monitor',
      icon: <SpeedIcon />,
      url: `${grafanaBaseUrl}/carla-dgx-performance/carla-dgx-a100-performance-monitor${GRAFANA_PARAMS}`,
      description: 'DGX A100 GPU utilization, memory usage, CPU and system performance'
    },
    {
      id: 'power',
      label: 'Power & Performance',
      icon: <TimelineIcon />,
      url: `${grafanaBaseUrl}/power-and-other/power-and-other${GRAFANA_PARAMS}`,
      description: 'DGX A100 power consumption, GPU utilization and temperature monitoring'
    },
    {
      id: 'services',
      label: 'Services Monitor',
      icon: <LocationIcon />,
      url: `${grafanaBaseUrl}/logging/logging${GRAFANA_PARAMS}`,
      description: 'Log monitoring, error tracking, and service health for CARLA components'
    }
  ];
  return (
    <Box sx={{ p: 0.5 }}>
      {configError && (
        <Paper sx={{ mb: 1, p: 2, bgcolor: 'warning.light' }}>
          <Typography variant="body2" color="warning.contrastText">
            ⚠️ {configError} If Grafana dashboards are not loading, please check if Grafana is running and accessible.
          </Typography>
        </Paper>
      )}
      
      <Paper sx={{ mb: 0.5 }}>
        <Tabs
          value={selectedTab}
          onChange={handleTabChange}
          aria-label="analytics dashboard tabs"
          variant="scrollable"
          scrollButtons="auto"
        >
          {dashboardConfigs.map((config, index) => (
            <Tab
              key={config.id}
              icon={config.icon}
              label={config.label}
              id={`analytics-tab-${index}`}
              aria-controls={`analytics-tabpanel-${index}`}
              iconPosition="start"
            />
          ))}
        </Tabs>
      </Paper>

      {dashboardConfigs.map((config, index) => (
        <TabPanel key={config.id} value={selectedTab} index={index}>
          <Box sx={{ height: '85vh', width: '100%' }}>
            <iframe
              src={config.url}
              width="100%"
              height="100%"
              frameBorder="0"
              title={`${config.label} Dashboard`}
              style={{
                minHeight: '600px',
                border: 'none',
                borderRadius: '4px'
              }}
              allowFullScreen
              allow="fullscreen"
              sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
              onError={() => {
                console.error(`Failed to load ${config.label} dashboard`);
              }}
            />
          </Box>
        </TabPanel>
      ))}
    </Box>
  );
};

export default Analytics; 
