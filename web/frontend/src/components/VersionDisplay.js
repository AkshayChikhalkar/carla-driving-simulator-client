import React, { useState, useEffect } from 'react';
import { Box, Typography, Chip } from '@mui/material';
import axios from 'axios';

const VersionDisplay = () => {
  const [version, setVersion] = useState('Loading...');
  const [buildTime, setBuildTime] = useState('');

  useEffect(() => {
    const fetchVersion = async () => {
      try {
        // Try to get version from backend first
        const response = await axios.get('/api/version');
        if (response.data && response.data.version) {
          setVersion(response.data.version);
          if (response.data.build_time) {
            setBuildTime(response.data.build_time);
          }
        } else {
          // Fallback to frontend version file
          const versionResponse = await axios.get('/version.txt');
          setVersion(versionResponse.data.trim());
        }
      } catch (error) {
        console.warn('Failed to fetch version from backend, trying frontend fallback');
        try {
          // Fallback to frontend version file
          const versionResponse = await axios.get('/version.txt');
          setVersion(versionResponse.data.trim());
        } catch (fallbackError) {
          console.warn('Failed to fetch version from frontend fallback');
          setVersion('Unknown');
        }
      }
    };

    fetchVersion();
  }, []);

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 12,
        left: 12,
        zIndex: 9999, // Higher z-index
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        gap: 0.5,
      }}
    >
      <Chip
        label={`v${version}`}
        size="small"
        sx={{
          backgroundColor: 'transparent', // Remove background
          color: 'white',
          fontSize: '0.75rem',
          height: '20px',
          '& .MuiChip-label': {
            padding: '0 8px',
          },
        }}
      />
      {buildTime && (
        <Typography
          variant="caption"
          sx={{
            color: 'rgba(255,255,255,0.8)', // More visible text
            fontSize: '0.6rem',
            backgroundColor: 'rgba(0,0,0,0.8)', // More opaque background
            padding: '2px 6px',
            borderRadius: '4px',
          }}
        >
          {new Date(buildTime).toLocaleDateString()}
        </Typography>
      )}
    </Box>
  );
};

export default VersionDisplay;