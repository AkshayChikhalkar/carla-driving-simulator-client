import React from 'react';
import { Box, Typography } from '@mui/material';

const GRAFANA_URL = 'http://localhost:3001/d/carla-simulator-metrics?orgId=1&kiosk'; 

const Analytics = () => {
  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Simulation Analytics
      </Typography>
      <Box sx={{ mt: 2, height: '80vh', width: '100%' }}>
        <iframe
          src={GRAFANA_URL}
          width="100%"
          height="100%"
          frameBorder="0"
          title="Carla Analytics Dashboard"
          style={{ minHeight: '600px', border: 'none' }}
          allowFullScreen
        />
      </Box>
    </Box>
  );
};

export default Analytics; 