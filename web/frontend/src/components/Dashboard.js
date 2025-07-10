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

const API_BASE_URL =
  window.location.hostname === 'localhost'
    ? '/api'
    : `http://${window.location.hostname}:8081/api`;
const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss' : 'ws';
const WS_BASE_URL =
  window.location.hostname === 'localhost'
    ? `${WS_PROTOCOL}://localhost:8000/ws/simulation-view`
    : `${WS_PROTOCOL}://${window.location.hostname}:8081/ws/simulation-view`;

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
  
  // Backend state tracking for sync
  const [backendState, setBackendState] = useState({
    is_running: false,
    is_starting: false,
    is_stopping: false,
    is_skipping: false,
    is_transitioning: false,
    current_scenario: null,
    scenario_index: 0,
    total_scenarios: 0,
    status_message: 'Ready to Start'
  });

  // Add immediate reset of transition flags when backend state changes
  useEffect(() => {
    // Reset isStarting when backend confirms start is complete
    if (isStarting && backendState.is_running && !backendState.is_starting) {
      console.log('Immediate reset: Backend confirmed start complete');
      setIsStarting(false);
    }
  }, [isStarting, backendState.is_running, backendState.is_starting]);

  useEffect(() => {
    // Reset isStopping when backend confirms stop is complete
    if (isStopping && !backendState.is_running && !backendState.is_stopping) {
      console.log('Immediate reset: Backend confirmed stop complete');
      setIsStopping(false);
    }
  }, [isStopping, backendState.is_running, backendState.is_stopping]);

  useEffect(() => {
    // Reset isSkipping when backend confirms skip is complete
    if (isSkipping && !backendState.is_skipping) {
      console.log('Immediate reset: Backend confirmed skip complete');
      setIsSkipping(false);
    }
  }, [isSkipping, backendState.is_skipping]);

  // Add a fallback mechanism to reset transition flags if backend confirms but frontend doesn't update
  useEffect(() => {
    if (isStarting && backendState.is_running && !backendState.is_starting) {
      // Backend confirmed start is complete but frontend didn't reset
      const timer = setTimeout(() => {
        if (isStarting && backendState.is_running && !backendState.is_starting) {
          console.log('Fallback: Resetting isStarting flag after timeout');
          setIsStarting(false);
        }
      }, 5000); // 5 second timeout
      
      return () => clearTimeout(timer);
    }
  }, [isStarting, backendState.is_running, backendState.is_starting]);

  useEffect(() => {
    if (isStopping && !backendState.is_running && !backendState.is_stopping) {
      // Backend confirmed stop is complete but frontend didn't reset
      const timer = setTimeout(() => {
        if (isStopping && !backendState.is_running && !backendState.is_stopping) {
          console.log('Fallback: Resetting isStopping flag after timeout');
          setIsStopping(false);
        }
      }, 5000); // 5 second timeout
      
      return () => clearTimeout(timer);
    }
  }, [isStopping, backendState.is_running, backendState.is_stopping]);

  useEffect(() => {
    if (isSkipping && !backendState.is_skipping) {
      // Backend confirmed skip is complete but frontend didn't reset
      const timer = setTimeout(() => {
        if (isSkipping && !backendState.is_skipping) {
          console.log('Fallback: Resetting isSkipping flag after timeout');
          setIsSkipping(false);
        }
      }, 5000); // 5 second timeout
      
      return () => clearTimeout(timer);
    }
  }, [isSkipping, backendState.is_skipping]);

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
        if (process.env.NODE_ENV !== 'production') {
          logger.error('Error fetching scenarios:', error);
        }
      });

    // Setup WebSocket connection for both video and status
    let ws;
    let isUnmounted = false;
    let lastFrameTime = 0;
    const FRAME_INTERVAL = 1000 / 30; // Target 30 FPS

    const setupWebSocket = () => {
      ws = new WebSocket(WS_BASE_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (process.env.NODE_ENV !== 'production') {
          console.log('WebSocket connection opened');
        }
        setStatus('Connected to simulation server');
      };

      ws.onclose = () => {
        if (!isRunning) {
          setStatus('Ready to Start');
        }
        setIsRunning(false);
        setIsPaused(false);
        setStatus('Disconnected from simulation server');
        // Attempt to reconnect after 2 seconds, but only if not unmounted
        if (!isUnmounted) setTimeout(setupWebSocket, 2000);
      };

      ws.onerror = (e) => {
        if (e && e.code && (e.code === 1001 || e.code === 1005)) {
          // Suppress normal disconnect errors
          return;
        }
        if (process.env.NODE_ENV !== 'production') {
          console.error('WebSocket error', e);
        }
        setStatus('Error in simulation connection');
      };

      ws.onmessage = (event) => {
        try {
          // If it's a status message (JSON)
          if (event.data.startsWith('{')) {
            const data = JSON.parse(event.data);
            if (data.type === 'status') {
              // Update backend state for sync
              setBackendState({
                is_running: data.is_running || false,
                is_starting: data.is_starting || false,
                is_stopping: data.is_stopping || false,
                is_skipping: data.is_skipping || false,
                is_transitioning: data.is_transitioning || false,
                current_scenario: data.current_scenario,
                scenario_index: data.scenario_index || 0,
                total_scenarios: data.total_scenarios || 0,
                status_message: data.status_message || 'Ready to Start'
              });

              if (process.env.NODE_ENV !== 'production') {
                console.log('WebSocket received:', {
                  is_running: data.is_running,
                  is_starting: data.is_starting,
                  is_stopping: data.is_stopping,
                  is_skipping: data.is_skipping,
                  status_message: data.status_message,
                  local_isStarting: isStarting,
                  local_isStopping: isStopping,
                  local_isSkipping: isSkipping
                });
              }
              
              // Debug: Log when is_starting is true
              if (data.is_starting) {
                console.log('Backend reports is_starting=True');
              }

              // Always reset UI if backend says simulation is stopped
              if (!data.is_running && !data.is_starting && !data.is_stopping && !data.is_skipping) {
                setIsStopping(false);
                setIsStarting(false);
                setIsSkipping(false);
                setIsRunning(false);
                setHasReceivedFrame(false);
                setStatus('Ready to Start');
                return;
              }

              // Reset transition flags when backend confirms operations are complete
              if (isStarting && data.is_running && !data.is_starting) {
                // Backend confirmed start is complete
                if (process.env.NODE_ENV !== 'production') {
                  console.log('Resetting isStarting flag - backend confirmed start complete');
                }
                setIsStarting(false);
              }
              if (isStopping && !data.is_running && !data.is_stopping) {
                // Backend confirmed stop is complete
                if (process.env.NODE_ENV !== 'production') {
                  console.log('Resetting isStopping flag - backend confirmed stop complete');
                }
                setIsStopping(false);
              }
              if (isSkipping && !data.is_skipping) {
                // Backend confirmed skip is complete
                if (process.env.NODE_ENV !== 'production') {
                  console.log('Resetting isSkipping flag - backend confirmed skip complete');
                }
                setIsSkipping(false);
              }

              // Use backend status message - only override with local transition states for immediate UX feedback
              if (isStarting || data.is_starting) {
                // Show starting message if either frontend or backend thinks we're starting
                setStatus('Starting simulation...');
                if (process.env.NODE_ENV !== 'production') {
                  console.log('Setting status to "Starting simulation..." (isStarting=', isStarting, ', data.is_starting=', data.is_starting, ')');
                }
              } else if (isStopping || data.is_stopping) {
                // Show stopping message if either frontend or backend thinks we're stopping
                setStatus('Stopping simulation...');
              } else if (isSkipping || data.is_skipping) {
                // Show skipping message if either frontend or backend thinks we're skipping
                setStatus('Skipping scenario...');
              } else {
                // Trust the backend status message for other states
                setStatus(data.status_message || 'Ready to Start');
                if (process.env.NODE_ENV !== 'production') {
                  console.log('Setting status to backend message:', data.status_message || 'Ready to Start');
                }
              }

              // Update isRunning based on backend state
              setIsRunning(data.is_running || false);
            }
          } else {
            // It's a video frame (base64 string)
            setHasReceivedFrame(true);
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
        } catch (e) {
          logger.error('Error parsing WebSocket message:', e);
        }
      };
    };

    setupWebSocket();

    return () => {
      isUnmounted = true;
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []); // Only run on mount/unmount

  // --- Button handlers ---
  const handleStart = async () => {
    if (selectedScenarios.length === 0) {
      setError('Please select at least one scenario');
      return;
    }
    // Set local transition state immediately
    setIsStarting(true);
    setIsStopping(false);
    setIsSkipping(false);
    setStatus('Starting simulation...');
    setError(null);
    
    if (process.env.NODE_ENV !== 'production') {
      console.log('handleStart: Set isStarting=true, status="Starting simulation..."');
    }
    try {
      const response = await axios.post(`${API_BASE_URL}/simulation/start`, {
        scenarios: selectedScenarios,
        debug: debug,
        report: report
      });
      // Do not reset isStarting here; let WebSocket handle it
    } catch (e) {
      setIsStarting(false);
      setStatus('Ready to Start');
      setError('Failed to start simulation');
    }
  };

  const handleStop = async () => {
    setIsStopping(true);
    setIsStarting(false);
    setIsSkipping(false);
    setStatus('Stopping simulation...');
    setError(null);
    try {
      const response = await axios.post(`${API_BASE_URL}/simulation/stop`);
      // Do not reset isStopping here; let WebSocket handle it
    } catch (e) {
      setIsStopping(false);
      setStatus('Ready to Start');
      setError('Failed to stop simulation');
    }
  };

  const handlePause = () => {
    const newPauseState = !isPaused;
    setIsPaused(newPauseState);
    setStatus(newPauseState ? 'Simulation paused' : 'Simulation resumed');
    logger.info(`Simulation ${newPauseState ? 'paused' : 'resumed'}`);
  };

  // Helper function to determine if any button should be disabled during transitions
  const isAnyButtonDisabled = () => {
    // All buttons should be disabled if any transition state is active
    return isStarting || isStopping || isSkipping;
  };

  // Helper function to determine if start button should be disabled
  const isStartDisabled = () => {
    return isRunning || !selectedScenarios.length || isAnyButtonDisabled();
  };

  // Helper function to determine if stop button should be disabled
  const isStopDisabled = () => {
    return !isRunning || isAnyButtonDisabled();
  };

  // Helper function to determine if pause button should be disabled
  const isPauseDisabled = () => {
    return !isRunning || isAnyButtonDisabled();
  };

  // Helper function to determine if skip button should be disabled
  const isSkipDisabled = () => {
    return !isRunning || isAnyButtonDisabled();
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

  // Add state to control dropdown open/close
  const [dropdownOpen, setDropdownOpen] = useState(false);

  // Handle dropdown open/close
  const handleDropdownOpen = (event) => {
    setDropdownOpen(true);
  };

  const handleDropdownClose = () => {
    setDropdownOpen(false);
  };

  // Enhanced scenario change handler with auto-close
  const handleScenarioChangeEnhanced = (event) => {
    const value = event.target.value;
    
    // If selecting individual scenarios
    if (!value.includes('all')) {
      // If all individual scenarios are selected, switch to "all"
      if (value.length === scenarios.length) {
        setSelectedScenarios(['all']);
      } else {
        setSelectedScenarios(value);
      }
      // Auto-close dropdown after selection
      setTimeout(() => setDropdownOpen(false), 100);
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
      // Auto-close dropdown after selection
      setTimeout(() => setDropdownOpen(false), 100);
    }
  };

  // Add skip scenario handler
  const handleSkipScenario = async () => {
    setIsSkipping(true);
    setIsStarting(false);
    setIsStopping(false);
    setStatus('Skipping scenario...');
    setError(null);
    try {
      const response = await axios.post(`${API_BASE_URL}/simulation/skip`);
      // Do not reset isSkipping here; let WebSocket handle it
    } catch (e) {
      setIsSkipping(false);
      setStatus('Ready to Start');
      setError('Failed to skip scenario');
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
                  onChange={handleScenarioChangeEnhanced}
                  onOpen={handleDropdownOpen}
                  onClose={handleDropdownClose}
                  open={dropdownOpen}
                  disabled={isRunning}
                  size="small"
                  renderValue={(selected) => {
                    if (selected.includes('all')) return 'All Scenarios';
                    if (selected.length === 0) return 'Select scenarios...';
                    if (selected.length === 1) return selected[0];
                    return `${selected.length} scenarios selected`;
                  }}
                  MenuProps={{
                    PaperProps: {
                      style: {
                        maxHeight: 300,
                        width: 300 // Set fixed width for dropdown menu
                      }
                    },
                    anchorOrigin: {
                      vertical: 'bottom',
                      horizontal: 'left',
                    },
                    transformOrigin: {
                      vertical: 'top',
                      horizontal: 'left',
                    }
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
                    },
                    display: 'none' // Hide pause button but keep logic
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
              display: isRunning && hasReceivedFrame && !isStarting && !isStopping && !isSkipping ? 'block' : 'none',
              background: '#000',
              margin: 0,
              padding: 0,
              position: 'absolute',
              top: 0,
              left: 0,
              opacity: isRunning && hasReceivedFrame && !isStarting && !isStopping && !isSkipping ? 1 : 0,
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
              opacity: isStarting || isStopping || isSkipping || (!isRunning || !hasReceivedFrame) ? 1 : 0,
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
                opacity: isStarting || isStopping || isSkipping || (!isRunning || !hasReceivedFrame) ? 1 : 0,
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