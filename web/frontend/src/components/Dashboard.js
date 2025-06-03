import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  FormControlLabel,
  Checkbox,
  Typography,
  Grid,
  Paper,
  Switch,
  IconButton
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Pause as PauseIcon,
} from '@mui/icons-material';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

function Dashboard({ onThemeToggle, isDarkMode }) {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState('');
  const [debug, setDebug] = useState(false);
  const [report, setReport] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [status, setStatus] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const wsRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    // Fetch available scenarios
    axios.get(`${API_BASE_URL}/scenarios`)
      .then(response => {
        setScenarios(response.data.scenarios);
        if (response.data.scenarios.length > 0) {
          setSelectedScenario(response.data.scenarios[0]);
        }
      })
      .catch(error => {
        console.error('Error fetching scenarios:', error);
        setStatus('Error loading scenarios');
      });

    // Setup WebSocket connection for both video and status
    const setupWebSocket = () => {
      wsRef.current = new WebSocket('ws://localhost:8000/ws/simulation-view');
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setStatus('Connected to simulation server');
      };
      
      wsRef.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsRunning(false);
        setIsPaused(false);
        setStatus('Disconnected from simulation server');
        // Attempt to reconnect after 2 seconds
        setTimeout(setupWebSocket, 2000);
      };
      
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setStatus('Error in simulation connection');
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          // Try to parse as JSON for status updates
          const data = JSON.parse(event.data);
          if (data.type === 'status') {
            setIsRunning(data.is_running);
            if (!data.is_running) {
              setIsPaused(false);
            }
          }
        } catch (e) {
          // If not JSON, treat as image data
          const img = new Image();
          img.onload = () => {
            const canvas = canvasRef.current;
            if (canvas) {
              const ctx = canvas.getContext('2d');
              canvas.width = img.width;
              canvas.height = img.height;
              ctx.drawImage(img, 0, 0);
            }
          };
          img.src = `data:image/jpeg;base64,${event.data}`;
        }
      };
    };

    setupWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleStart = async () => {
    if (isStarting) return; // Prevent multiple clicks
    
    try {
      setIsStarting(true);
      setIsRunning(true);
      setStatus('Starting simulation...');
      
      const response = await axios.post(`${API_BASE_URL}/simulation/start`, {
        scenario: selectedScenario,
        debug,
        report,
      });

      setStatus(response.data.message);
    } catch (error) {
      console.error('Error starting simulation:', error);
      setStatus('Error starting simulation');
      setIsRunning(false);
    } finally {
      setIsStarting(false);
    }
  };

  const handleStop = async () => {
    if (isStopping) return; // Prevent multiple clicks
    
    try {
      setIsStopping(true);
      setStatus('Stopping simulation...');
      const response = await axios.post(`${API_BASE_URL}/simulation/stop`);
      setStatus(response.data.message);
      
      // Clear the canvas when simulation stops
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    } catch (error) {
      console.error('Error stopping simulation:', error);
      setStatus('Error stopping simulation');
    } finally {
      setIsStopping(false);
    }
  };

  const handlePause = () => {
    setIsPaused(!isPaused);
    setStatus(isPaused ? 'Simulation resumed' : 'Simulation paused');
  };

  // Helper function to determine if start button should be disabled
  const isStartDisabled = () => {
    return isRunning || !selectedScenario || isStarting;
  };

  // Helper function to determine if stop button should be disabled
  const isStopDisabled = () => {
    return !isRunning || isStopping;
  };

  // Helper function to determine if pause button should be disabled
  const isPauseDisabled = () => {
    return !isRunning || isStopping;
  };

  return (
    <>
      {/* Dark mode toggle button in extreme top right corner */}
      <Box sx={{ position: 'fixed', top: 8, right: 8, zIndex: 2001, display: 'flex', alignItems: 'center', m: 0, p: 1 }}>
        <IconButton onClick={onThemeToggle} color="inherit" size="medium">
          {isDarkMode ? <Brightness7Icon /> : <Brightness4Icon />}
        </IconButton>
      </Box>
      <Box sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '88vh',
        width: '85vw',
        overflow: 'hidden',
        background: '#111',
        margin: 0,
        padding: 0
      }}>
        {/* Control Panel */}
        <Paper sx={{
          p: 1,
          borderRadius: 0,
          mb: 0,
          mt: 0,
          boxShadow: 3,
          background: '#222',
          width: '100%',
          flex: '0 0 auto',
          position: 'relative'
        }}>
          <Grid container spacing={1} alignItems="center" sx={{ margin: 0, padding: 0 }}>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Scenario</InputLabel>
                <Select
                  value={selectedScenario}
                  label="Scenario"
                  onChange={(e) => setSelectedScenario(e.target.value)}
                  disabled={isRunning}
                  size="small"
                >
                  <MenuItem value="all">All Scenarios</MenuItem>
                  {scenarios.map((scenario) => (
                    <MenuItem key={scenario} value={scenario}>
                      {scenario}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={3}>
              <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'center' }}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={debug}
                      onChange={(e) => setDebug(e.target.checked)}
                      disabled={isRunning}
                      size="small"
                    />
                  }
                  label="Debug"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={report}
                      onChange={(e) => setReport(e.target.checked)}
                      disabled={isRunning}
                      size="small"
                    />
                  }
                  label="Report"
                />
              </Box>
            </Grid>

            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', pr: 2.5, alignItems: 'center' }}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<PlayIcon />}
                  onClick={handleStart}
                  disabled={isStartDisabled()}
                  size="small"
                  sx={{ 
                    '& .MuiButton-startIcon': { 
                      marginRight: 0.5,
                      marginLeft: 0
                    }
                  }}
                >
                  {isStarting ? 'Starting...' : 'Start'}
                </Button>
                <Button
                  variant="contained"
                  color="secondary"
                  startIcon={<PauseIcon />}
                  onClick={handlePause}
                  disabled={isPauseDisabled()}
                  size="small"
                  sx={{ 
                    '& .MuiButton-startIcon': { 
                      marginRight: 0.5,
                      marginLeft: 0
                    }
                  }}
                >
                  {isPaused ? 'Resume' : 'Pause'}
                </Button>
                <Button
                  variant="contained"
                  color="error"
                  startIcon={<StopIcon />}
                  onClick={handleStop}
                  disabled={isStopDisabled()}
                  size="small"
                  sx={{ 
                    '& .MuiButton-startIcon': { 
                      marginRight: 0.5,
                      marginLeft: 0
                    }
                  }}
                >
                  {isStopping ? 'Stopping...' : 'Stop'}
                </Button>
              </Box>
            </Grid>

            {status && (
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0, mb: 0, lineHeight: 1.2 }}>
                  Status: {status}
                </Typography>
              </Grid>
            )}
          </Grid>
        </Paper>
        {/* Simulation View */}
        <Box
          sx={{
            flex: '1 1 0',
            minHeight: 0,
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
            p: 0,
            m: 0,
            background: 'background.paper',
            border: '1px solid',
            borderColor: 'divider'
          }}
        >
          {isRunning ? (
            <canvas
              ref={canvasRef}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain',
                display: 'block',
                background: '#000',
                margin: 0,
                padding: 0
              }}
            />
          ) : (
            <img
              src="/wavy_logo_loading.gif"
              alt="Loading"
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'contain',
                display: 'block',
                background: '#000',
                margin: 0,
                padding: 0
              }}
            />
          )}
        </Box>
      </Box>
    </>
  );
}

export default Dashboard; 