import React, { useState } from 'react';
import {
  Box,
  Tabs,
  Tab,
  Paper
} from '@mui/material';
import {
  Timeline as TimelineIcon,
  Speed as SpeedIcon,
  LocationOn as LocationIcon,
  Assessment as AssessmentIcon
} from '@mui/icons-material';

const GRAFANA_BASE_URL = 'http://193.16.126.186:3005/d';
const GRAFANA_PARAMS = '?orgId=1&kiosk';

// Dashboard configurations - Using actual dashboard UIDs from your Grafana setup
const dashboardConfigs = [
  {
    id: 'metrics',
    label: 'Simulator Metrics',
    icon: <AssessmentIcon />,
    url: `${GRAFANA_BASE_URL}/carla-simulator-metrics${GRAFANA_PARAMS}`,
    description: 'Vehicle speed, navigation metrics, position, and controls'
  },
  {
    id: 'performance',
    label: 'Performance Monitor',
    icon: <SpeedIcon />,
    url: `${GRAFANA_BASE_URL}/carla-dgx-performance${GRAFANA_PARAMS}`,
    description: 'DGX A100 GPU utilization, memory usage, CPU and system performance'
  },
  {
    id: 'power',
    label: 'Power & Performance',
    icon: <TimelineIcon />,
    url: `${GRAFANA_BASE_URL}/power-and-other/power-and-other${GRAFANA_PARAMS}`,
    description: 'DGX A100 power consumption, GPU utilization and temperature monitoring'
  },
  {
    id: 'services',
    label: 'Services Monitor',
    icon: <LocationIcon />,
    url: `${GRAFANA_BASE_URL}/logging/logging${GRAFANA_PARAMS}`,
    description: 'Log monitoring, error tracking, and service health for CARLA components'
  }
];

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

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
  };

  return (
    <Box sx={{ p: 0.5 }}>
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
            />
          </Box>
        </TabPanel>
      ))}
    </Box>
  );
};

export default Analytics; 