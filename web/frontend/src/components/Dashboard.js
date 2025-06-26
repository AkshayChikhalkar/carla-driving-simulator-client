import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  FormControlLabel,
  Checkbox,
  Typography,
  Grid,
  Paper
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Pause as PauseIcon,
  SkipNext as SkipNextIcon
} from '@mui/icons-material';
import axios from 'axios';
import logger from '../utils/logger';

const API_BASE_URL = process.env.NODE_ENV === 'production' ? window.location.origin + '/api' : '/api';
const WS_BASE_URL = process.env.NODE_ENV === 'production' ? 
  window.location.origin.replace('http', 'ws') : 
  window.location.origin.replace('http', 'ws');

function Dashboard({ onThemeToggle, isDarkMode }) {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenarios, setSelectedScenarios] = useState([]);
  const [debug, setDebug] = useState(false);
  const [report, setReport] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [status, setStatus] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [hasReceivedFrame, setHasReceivedFrame] = useState(false);
  const [error, setError] = useState(null);
  const [isSkipping, setIsSkipping] = useState(false);
  const wsRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    // Fetch available scenarios
    axios.get(`${API_BASE_URL}/scenarios`)
      .then(response => {
        setScenarios(Array.isArray(response.data.scenarios) ? response.data.scenarios : []);
        setStatus('Connected to simulation server');
      })
      .catch(error => {
        setScenarios([]);
        setStatus('Error loading scenarios');
        logger.error('Error fetching scenarios:', error);
      });

    // Setup WebSocket connection for both video and status
    const setupWebSocket = () => {
      const wsUrl = `${WS_BASE_URL}/ws/simulation-view`;
      wsRef.current = new WebSocket(wsUrl);
      
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
            // Update state based on backend information
            const backendRunning = data.is_running;
            const isTransitioning = data.is_transitioning || false;
            
            // Only update isRunning if we're not in the starting process
            if (!isStarting) {
              setIsRunning(backendRunning);
              if (!backendRunning) {
                setIsPaused(false);
                setIsStopping(false);
                setHasReceivedFrame(false);
              }
            }
            
            // Update status if transitioning
            if (isTransitioning) {
              setStatus('Transitioning between scenarios...');
            }
            
            // Log state changes for debugging
            logger.debug(`WebSocket state update: running=${backendRunning}, transitioning=${isTransitioning}`);
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
  }, [isStarting]);

  const handleStart = async () => {
    if (isStarting) return; // Prevent multiple clicks
    
    try {
      setIsStarting(true);
      setStatus('Starting simulation...');
      setError(null); // Clear any previous errors
      
      logger.info(`Starting simulation with scenarios: ${selectedScenarios.join(', ')}, debug: ${debug}, report: ${report}`);
      
      const response = await axios.post(`${API_BASE_URL}/simulation/start`, {
        scenarios: selectedScenarios,
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
      // Use backend error message if available
      const backendMsg = error.response?.data?.detail || 'Failed to start simulation, please try again!';
      setError(backendMsg);
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
      
      // Reset the entire view immediately
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
      
      // Reset all view states immediately
      setIsRunning(false);
      setHasReceivedFrame(false);
      
      // Call the stop API
      const response = await axios.post(`${API_BASE_URL}/simulation/stop`);
      
      if (response.data.success) {
        setStatus(response.data.message);
        logger.info(`Simulation stopped successfully: ${response.data.message}`);
        
        // Wait for 2 seconds before showing "Ready to Start"
        setTimeout(() => {
          setStatus('Ready to Start');
          setIsPaused(false);
        }, 2000);
      } else {
        setStatus('Error stopping simulation');
        setError(response.data.message || 'Failed to stop simulation');
      }
      
    } catch (error) {
      logger.error('Error stopping simulation:', error);
      setStatus('Error stopping simulation');
      const errorMsg = error.response?.data?.detail || 'Failed to stop simulation. Please try again.';
      setError(errorMsg);
    } finally {
      // Add a small delay before resetting the stopping state
      setTimeout(() => {
        setIsStopping(false);
      }, 1000);
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
    return isRunning || !selectedScenarios.length || isStarting || isStopping || isSkipping;
  };

  // Helper function to determine if stop button should be disabled
  const isStopDisabled = () => {
    return !isRunning || isStopping || isStarting || isSkipping;
  };

  // Helper function to determine if pause button should be disabled
  const isPauseDisabled = () => {
    return !isRunning || isStopping || isStarting || isPaused || isSkipping;
  };

  // Helper function to determine if skip button should be disabled
  const isSkipDisabled = () => {
    return !isRunning || isSkipping || isStopping || isStarting || (selectedScenarios.length === 1 && !selectedScenarios.includes('all'));
  };

  // Update the handleScenarioChange function
  const handleScenarioChange = (event) => {
    const value = event.target.value;
    
    // If selecting individual scenarios
    if (!value.includes('all')) {
      // If all individual scenarios are selected, switch to "all"
      if (value.length === scenarios.length) {
        setSelectedScenarios(['all']);
      } else {
        setSelectedScenarios(value);
      }
      return;
    }
    
    // If "all" is selected
    if (value.includes('all')) {
      // If "all" is the only selection, keep it
      if (value.length === 1) {
        setSelectedScenarios(['all']);
      } else {
        // If other scenarios are selected with "all", remove "all" and keep individual selections
        setSelectedScenarios(value.filter(v => v !== 'all'));
      }
    }
  };

  // Add skip scenario handler
  const handleSkipScenario = async () => {
    if (!isRunning || isSkipping) return;
    
    try {
      setIsSkipping(true);
      setStatus('Skipping scenario...');
      setError(null); // Clear any previous errors
      
      logger.info('Initiating scenario skip');
      
      const response = await axios.post(`${API_BASE_URL}/simulation/skip`);
      
      // Update status based on response
      if (response.data.success) {
        setStatus(response.data.message);
        
        // If simulation is complete, update UI after a delay
        if (response.data.message.includes("Simulation complete")) {
          // Wait for 2 seconds before showing "Ready to Start"
          setTimeout(() => {
            setStatus('Ready to Start');
            setIsRunning(false);
            setIsPaused(false);
            setHasReceivedFrame(false);
          }, 2000);
        }
        // If there's a next scenario, the WebSocket will update the state
      } else {
        setStatus('Error skipping scenario');
        setError(response.data.message || 'Failed to skip scenario');
      }
      
      logger.info(`Scenario skip result: ${response.data.message}`);
    } catch (error) {
      logger.error('Error skipping scenario:', error);
      setStatus('Error skipping scenario');
      const errorMsg = error.response?.data?.detail || 'Failed to skip scenario, please try again!';
      setError(errorMsg);
    } finally {
      setIsSkipping(false);
    }
  };

  return (
    <>      
      <Box sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        overflow: 'hidden',
        background: '#000',
        minHeight: '84vh',
        margin: 0,
        padding: 0
      }}>
        {/* Control Panel */}
        <Paper sx={{
          p: 1,
          mb: 1,
          mt: 0,
          boxShadow: 3,
          background: '#222',
          width: '100%',
          flex: '0 0 auto',
          position: 'relative',
          borderRadius: '8px'
        }}>
          <Grid container spacing={1} alignItems="center" sx={{ margin: 0, padding: 0 }}>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Scenarios</InputLabel>
                <Select
                  multiple
                  value={selectedScenarios}
                  label="Scenarios"
                  onChange={handleScenarioChange}
                  disabled={isRunning}
                  size="small"
                  renderValue={(selected) => {
                    if (selected.includes('all')) return 'All Scenarios';
                    return selected.join(', ');
                  }}
                >
                  <MenuItem value="all">All Scenarios</MenuItem>
                  {status === 'Error loading scenarios' ? (
                    <MenuItem disabled>Failed to load scenarios from server.</MenuItem>
                  ) : (
                    Array.isArray(scenarios) && scenarios.map((scenario) => (
                      <MenuItem key={scenario} value={scenario}>
                        {scenario}
                      </MenuItem>
                    ))
                  )}
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
                  color="warning"
                  startIcon={<SkipNextIcon />}
                  onClick={handleSkipScenario}
                  disabled={isSkipDisabled()}
                  size="small"
                  sx={{ 
                    '& .MuiButton-startIcon': { 
                      marginRight: 0.5,
                      marginLeft: 0
                    }
                  }}
                >
                  {isSkipping ? 'Skipping...' : 'Skip'}
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
            position: 'relative',
            borderRadius: '8px'
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
              opacity: (!isRunning || !hasReceivedFrame || isStopping || isSkipping) ? 1 : 0,
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
                opacity: isStopping || isSkipping ? 1 : (!isRunning || !hasReceivedFrame ? 1 : 0),
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
               isStopping ? status : 
               isSkipping ? status : 
               status === 'Ready to Start' ? 'Ready to Start' :
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