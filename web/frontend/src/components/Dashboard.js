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
import logger from '../utils/logger';

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
  const [hasReceivedFrame, setHasReceivedFrame] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    // Fetch available scenarios
    axios.get(`${API_BASE_URL}/scenarios`)
      .then(response => {
        setScenarios(response.data.scenarios);
        if (response.data.scenarios.length > 0) {
          setSelectedScenario(response.data.scenarios[0]);
          logger.info(`Loaded ${response.data.scenarios.length} scenarios, default selected: ${response.data.scenarios[0]}`);
        } else {
          logger.warn('No scenarios available');
        }
      })
      .catch(error => {
        logger.error('Error fetching scenarios:', error);
        setStatus('Error loading scenarios');
      });

    // Setup WebSocket connection for both video and status
    const setupWebSocket = () => {
      wsRef.current = new WebSocket('ws://localhost:8000/ws/simulation-view');
      
      wsRef.current.onopen = () => {
        logger.info('WebSocket connected');
        setStatus('Connected to simulation server');
      };
      
      wsRef.current.onclose = () => {
        logger.info('WebSocket disconnected');
        setIsRunning(false);
        setIsPaused(false);
        setStatus('Disconnected from simulation server');
        // Attempt to reconnect after 2 seconds
        setTimeout(setupWebSocket, 2000);
      };
      
      wsRef.current.onerror = (error) => {
        logger.error('WebSocket error:', error);
        setStatus('Error in simulation connection');
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          // Try to parse as JSON for status updates
          const data = JSON.parse(event.data);
          if (data.type === 'status') {
            // Only update isRunning if we're not in the starting process
            if (!isStarting) {
              setIsRunning(data.is_running);
              if (!data.is_running) {
                setIsPaused(false);
                setIsStopping(false);
                setHasReceivedFrame(false);
              }
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
              setHasReceivedFrame(true);
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
      setStatus('Starting simulation...');
      setError(null); // Clear any previous errors
      
      logger.info(`Starting simulation with scenario: ${selectedScenario}, debug: ${debug}, report: ${report}`);
      
      const response = await axios.post(`${API_BASE_URL}/simulation/start`, {
        scenario: selectedScenario,
        debug,
        report,
      });

      // Only set isRunning to true after successful API call
      setIsRunning(true);
      setStatus(response.data.message);
      logger.info(`Simulation started successfully: ${response.data.message}`);
    } catch (error) {
      logger.error('Error starting simulation:', error);
      setStatus('Error starting simulation');
      setError('Failed to start simulation, please try again!');
      setIsRunning(false);
    } finally {
      // Reset isStarting after a short delay to ensure the button state is visible
      setTimeout(() => {
        setIsStarting(false);
      }, 1000);
    }
  };

  const handleStop = async () => {
    if (isStopping) return; // Prevent multiple clicks
    
    try {
      setIsStopping(true);
      setStatus('Stopping simulation...');
      setError(null); // Clear any previous errors
      
      logger.info('Initiating simulation stop');
      
      // Reset the entire view
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        // Clear the entire canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        // Reset canvas dimensions
        canvas.width = 0;
        canvas.height = 0;
        logger.debug('Canvas completely reset after stop button click');
      }
      
      // Reset all view states
      setIsRunning(false);
      setHasReceivedFrame(false);
      
      // Wait for the transition to complete before stopping the simulation
      setTimeout(async () => {
        try {
          const response = await axios.post(`${API_BASE_URL}/simulation/stop`);
          setStatus(response.data.message);
          logger.info(`Simulation stopped successfully: ${response.data.message}`);
        } catch (error) {
          logger.error('Error stopping simulation:', error);
          setStatus('Error stopping simulation');
          setError('Failed to stop simulation properly. Please try again.');
        } finally {
          // Add a small delay before resetting the stopping state
          setTimeout(() => {
            setIsStopping(false);
            setStatus('Ready to start');
          }, 500);
        }
      }, 500); // Match the transition duration
    } catch (error) {
      logger.error('Error stopping simulation:', error);
      setStatus('Error stopping simulation');
      setError('Failed to stop simulation. Please try again.');
      setIsStopping(false);
    }
  };

  const handlePause = () => {
    const newPauseState = !isPaused;
    setIsPaused(newPauseState);
    setStatus(newPauseState ? 'Simulation paused' : 'Simulation resumed');
    logger.info(`Simulation ${newPauseState ? 'paused' : 'resumed'}`);
  };

  // Helper function to determine if start button should be disabled
  const isStartDisabled = () => {
    return isRunning || !selectedScenario || isStarting || isStopping;
  };

  // Helper function to determine if stop button should be disabled
  const isStopDisabled = () => {
    return !isRunning || isStopping || isStarting;
  };

  // Helper function to determine if pause button should be disabled
  const isPauseDisabled = () => {
    return !isRunning || isStopping || isStarting || isPaused;
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
        height: '100%',
        width: '100%',
        overflow: 'hidden',
        background: '#111',
        minHeight: '84vh',
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
            background: '#000',
            border: '1px solid',
            borderColor: 'divider',
            position: 'relative'
          }}
        >
          <canvas
            ref={canvasRef}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              display: isRunning && hasReceivedFrame && !isStopping ? 'block' : 'none',
              background: '#000',
              margin: 0,
              padding: 0,
              position: 'absolute',
              top: 0,
              left: 0,
              opacity: isRunning && hasReceivedFrame && !isStopping ? 1 : 0,
              transition: 'opacity 0.5s ease-in-out',
              zIndex: 0
            }}
          />
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#000',
              opacity: (!isRunning || !hasReceivedFrame || isStopping) ? 1 : 0,
              transition: 'opacity 0.5s ease-in-out',
              zIndex: 1
            }}
          >
            <img
              src="/wavy_logo_loading.gif"
              alt="Loading"
              style={{
                width: '50%',
                height: '50%',
                objectFit: 'contain',
                display: 'block',
                background: '#000',
                margin: 0,
                padding: 0,
                opacity: isStopping ? 1 : (!isRunning || !hasReceivedFrame ? 1 : 0),
                transition: 'opacity 0.5s ease-in-out'
              }}
            />
            <Typography
              variant="h6"
              sx={{
                color: 'white',
                mt: 2,
                textAlign: 'center',
                textShadow: '0 2px 4px rgba(0,0,0,0.5)',
                whiteSpace: 'pre-line'
              }}
            >
              {error ? error : 
               isStarting && !hasReceivedFrame ? 'Hang on,\nLoading Simulation...' : 
               isStopping ? 'Stopping Simulation...' : 
               'Ready to Start'}
            </Typography>
            {error && (
              <Typography
                variant="body2"
                sx={{
                  color: '#ff6b6b',
                  mt: 1,
                  textAlign: 'center',
                  textShadow: '0 1px 2px rgba(0,0,0,0.5)'
                }}
              >
                Click Start button to try again
              </Typography>
            )}
          </Box>
        </Box>
      </Box>
    </>
  );
}

export default Dashboard; 