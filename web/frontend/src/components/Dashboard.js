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
import { useWebSocketConnection } from '../hooks/useWebSocketConnection';
import { getInstructionMessage } from '../utils/uiHelpers';

const API_BASE_URL =
  window.location.hostname === 'localhost'
    ? '/api'
    : `http://${window.location.hostname}:8081/api`;

// Memoized style computations for better performance
const computeButtonStates = ({
  isRunning,
  selectedScenariosLength,
  isStarting,
  isStopping,
  isSkipping,
  backendState
}) => {
  const anyTransition = isStarting || isStopping || isSkipping || 
                       backendState.is_starting || backendState.is_stopping || backendState.is_skipping;
  const isLastScenario = backendState.scenario_index >= backendState.total_scenarios;
  const isSingleScenario = backendState.total_scenarios <= 1;
  
  return {
    isStartDisabled: isRunning || !selectedScenariosLength || anyTransition,
    isStopDisabled: !isRunning || anyTransition,
    isPauseDisabled: !isRunning || anyTransition,
    isSkipDisabled: !isRunning || anyTransition || isLastScenario || isSingleScenario
  };
};

const computeCanvasStyle = ({
  isRunning,
  backendState,
  hasReceivedFrame,
  isStarting,
  isStopping,
  isSkipping
}) => {
  // Keep canvas visible during all transitions to prevent flickering
  // Only hide canvas when simulation is completely stopped and no frames received
  // For stop transitions, keep canvas visible even when not running to show last frame
  const shouldShow = (isRunning || backendState.is_running) && 
                    hasReceivedFrame && 
                    !(isStarting && !backendState.is_running);
  
  // Special case: keep canvas visible during stop transition even if not running
  const shouldShowDuringStop = isStopping || backendState.is_stopping;
  
  // Gradual fade-out effect: reduce opacity during stop transition
  let opacity = 1;
  if (shouldShowDuringStop && !shouldShow) {
    opacity = 0.6; // Gradual fade-out during stop transition
  } else if (!shouldShow && !shouldShowDuringStop) {
    opacity = 0; // Completely hidden when not showing
  }

  // Quicker transitions for start/skip, slower for stop
  let transition = 'opacity 1.2s ease-in-out';
  if (isStarting || backendState.is_starting || isSkipping || backendState.is_skipping) {
    transition = 'opacity 0.5s ease-in-out';
  }
  
  return {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    display: (shouldShow || shouldShowDuringStop) ? 'block' : 'none',
    background: '#000',
    margin: 0,
    padding: 0,
    position: 'absolute',
    top: 0,
    left: 0,
    opacity: opacity,
    transition,
    zIndex: 0
  };
};

const computeOverlayStyle = ({
  isStarting,
  backendState,
  isStopping,
  isSkipping,
  isRunning,
  hasReceivedFrame
}) => {
  // During skipping, always show the overlay
  if (isSkipping || backendState.is_skipping) {
    return {
      position: 'absolute',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'rgba(0, 0, 0, 0.7)',
      opacity: 1,
      transition: 'opacity 0.5s ease-in-out, background 0.5s ease-in-out',
      zIndex: 1
    };
  }
  const anyTransition = isStarting || isStopping || isSkipping || 
                       backendState.is_starting || backendState.is_stopping || backendState.is_skipping;
  
  // Show overlay during transitions or when no frames received
  // For stop transitions, show a lighter overlay to keep last frame visible
  const shouldShow = anyTransition || (!(isRunning || backendState.is_running) || !hasReceivedFrame);
  
  // Use lighter overlay during stop transition with gradual increase
  let overlayOpacity = 0.7;
  if (isStopping || backendState.is_stopping) {
    overlayOpacity = 0.3; // Very light overlay during stop to show last frame
  } else if (!(isRunning || backendState.is_running) && hasReceivedFrame) {
    overlayOpacity = 0.5; // Medium overlay when stopped but still showing last frame
  }

  // Quicker transitions for start/skip, slower for stop
  let transition = 'opacity 1.2s ease-in-out, background 1.2s ease-in-out';
  if (isStarting || backendState.is_starting || isSkipping || backendState.is_skipping) {
    transition = 'opacity 0.5s ease-in-out, background 0.5s ease-in-out';
  }
  
  return {
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    background: `rgba(0, 0, 0, ${overlayOpacity})`, // Dynamic overlay opacity
    opacity: shouldShow ? 1 : 0,
    transition,
    zIndex: 1
  };
};

const computeLoadingImageStyle = ({
  isStarting,
  backendState,
  isStopping,
  isSkipping,
  isRunning,
  hasReceivedFrame
}) => {
  const anyTransition = isStarting || isStopping || isSkipping || 
                       backendState.is_starting || backendState.is_stopping || backendState.is_skipping;
  
  const shouldShow = anyTransition || (!(isRunning || backendState.is_running) || !hasReceivedFrame);
  
  // Gradual fade-out for loading image during stop transition
  let opacity = shouldShow ? 1 : 0;
  if (isStopping || backendState.is_stopping) {
    opacity = 0.8; // Slightly fade loading image during stop
  }

  // Quicker transitions for start/skip, slower for stop
  let transition = 'opacity 1.2s ease-in-out';
  if (isStarting || backendState.is_starting || isSkipping || backendState.is_skipping) {
    transition = 'opacity 0.5s ease-in-out';
  }
  
  return {
    width: '50%',
    height: '50%',
    objectFit: 'contain',
    display: 'block',
    background: 'transparent',
    margin: 0,
    padding: 0,
    opacity: opacity,
    transition
  };
};



function Dashboard({ onThemeToggle, isDarkMode }) {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenarios, setSelectedScenarios] = useState([]);
  const [debug, setDebug] = useState(false);
  const [report, setReport] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [status, setStatus] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const isStartingRef = useRef(isStarting);
  const [isStopping, setIsStopping] = useState(false);
  const [hasReceivedFrame, setHasReceivedFrame] = useState(false);
  const [error, setError] = useState(null);
  const [isSkipping, setIsSkipping] = useState(false);
  const wsRef = useRef(null);
  const canvasRef = useRef(null);
  
  // Add debounce refs for button states to prevent flickering
  const buttonDebounceRef = useRef({
    isStartDisabled: false,
    isStopDisabled: true,
    isPauseDisabled: true,
    isSkipDisabled: true
  });
  
  
  // Track previous state to detect changes
  const previousStateRef = useRef({
    is_running: false,
    is_starting: false,
    is_stopping: false,
    is_skipping: false,
    status_message: ''
  });

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
      //console.log('Immediate reset: Backend confirmed start complete');
      setIsStarting(false);
    }
  }, [isStarting, backendState.is_running, backendState.is_starting]);

  useEffect(() => {
    // Reset isStopping when backend confirms stop is complete
    if (isStopping && !backendState.is_running && !backendState.is_stopping) {
      //console.log('Immediate reset: Backend confirmed stop complete');
      setIsStopping(false);
    }
  }, [isStopping, backendState.is_running, backendState.is_stopping]);

  useEffect(() => {
    // Reset isSkipping when backend confirms skip is complete
    if (isSkipping && !backendState.is_skipping) {
      //console.log('Immediate reset: Backend confirmed skip complete');
      setIsSkipping(false);
    }
  }, [isSkipping, backendState.is_skipping]);

  // Add a fallback mechanism to reset transition flags if backend confirms but frontend doesn't update
  useEffect(() => {
    if (isStarting && backendState.is_running && !backendState.is_starting) {
      // Backend confirmed start is complete but frontend didn't reset
      const timer = setTimeout(() => {
        if (isStarting && backendState.is_running && !backendState.is_starting) {
          //console.log('Fallback: Resetting isStarting flag after timeout');
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
          //console.log('Fallback: Resetting isStopping flag after timeout');
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
          //console.log('Fallback: Resetting isSkipping flag after timeout');
          setIsSkipping(false);
        }
      }, 5000); // 5 second timeout

      return () => clearTimeout(timer);
    }
  }, [isSkipping, backendState.is_skipping]);

  // Refined: Only reset isSkipping when skip is complete AND either a new scenario is running or simulation is stopped
  useEffect(() => {
    if (
      isSkipping &&
      !backendState.is_skipping &&
      (
        backendState.is_running || // new scenario running
        (!backendState.is_running && !backendState.is_starting && !backendState.is_stopping && !backendState.is_skipping) // simulation stopped
      )
    ) {
      //console.log('Refined: Backend confirmed skip complete and new scenario running or stopped');
      setIsSkipping(false);
    }
  }, [isSkipping, backendState.is_skipping, backendState.is_running, backendState.is_starting, backendState.is_stopping]);

  useEffect(() => {
    isStartingRef.current = isStarting;
  }, [isStarting]);

  useWebSocketConnection({
    setStatus,
    setIsRunning,
    setIsPaused,
    setBackendState,
    setHasReceivedFrame,
    setIsStarting,
    setIsStopping,
    setIsSkipping,
    isSkipping,
    backendState,
  });

  useEffect(() => {
    logger.info('Dashboard useEffect triggered - setting up WebSocket connection');
    
    // Fetch available scenarios
    axios.get(`${API_BASE_URL}/scenarios`)
      .then(response => {
        setScenarios(Array.isArray(response.data.scenarios) ? response.data.scenarios : []);
        setStatus('Ready to Start');
      })
      .catch(error => {
        setScenarios([]);
        setStatus('Error loading scenarios');
        if (process.env.NODE_ENV !== 'production') {
          logger.error('Error fetching scenarios:', error);
        }
      });
  }, []);

  // Memoized button states with debounce to prevent flickering
  const buttonStates = React.useMemo(() => {
    const computedStates = computeButtonStates({
      isRunning,
      selectedScenariosLength: selectedScenarios.length,
      isStarting,
      isStopping,
      isSkipping,
      backendState
    });
    
    // Apply debounce logic to prevent rapid state changes
    const anyTransition = isStarting || isStopping || isSkipping || 
                         backendState.is_starting || backendState.is_stopping || backendState.is_skipping;
    
    // If any transition is active, disable all buttons to prevent flickering
    if (anyTransition) {
      return {
        isStartDisabled: true,
        isStopDisabled: true,
        isPauseDisabled: true,
        isSkipDisabled: true
      };
    }
    
    return computedStates;
  }, [isRunning, selectedScenarios.length, isStarting, isStopping, isSkipping, backendState]);

  // Memoized styles
  const canvasStyle = React.useMemo(() => 
    computeCanvasStyle({
      isRunning,
      backendState,
      hasReceivedFrame,
      isStarting,
      isStopping,
      isSkipping
    }), 
    [isRunning, backendState, hasReceivedFrame, isStarting, isStopping, isSkipping]
  );

  const overlayStyle = React.useMemo(() => 
    computeOverlayStyle({
      isStarting,
      backendState,
      isStopping,
      isSkipping,
      isRunning,
      hasReceivedFrame
    }), 
    [isStarting, backendState, isStopping, isSkipping, isRunning, hasReceivedFrame]
  );

  const loadingImageStyle = React.useMemo(() => 
    computeLoadingImageStyle({
      isStarting,
      backendState,
      isStopping,
      isSkipping,
      isRunning,
      hasReceivedFrame
    }), 
    [isStarting, backendState, isStopping, isSkipping, isRunning, hasReceivedFrame]
  );

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
    setStatus('Hang on,\nLoading Simulation...');
    setError(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/simulation/start`, {
        scenarios: selectedScenarios,
        debug: debug,
        report: report
      });

      // Do not reset isStarting here; let WebSocket handle it
    } catch (e) {
      console.error('handleStart: API call failed:', e);
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
      await axios.post(`${API_BASE_URL}/simulation/stop`);
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
    //console.log('handleSkipScenario: Starting skip process');
    
    // Set states immediately for instant visual feedback
    setIsSkipping(true);
    setIsStarting(false);
    setIsStopping(false);
    setStatus('Skipping scenario...'); // Set immediate status for UX feedback
    setError(null);
    
    // Note: Canvas will be managed by the style computations
    // No need to manually clear or hide it
    
    // Force a re-render to ensure overlay appears immediately
    setTimeout(() => {
      if (isSkipping) {
        //console.log('handleSkipScenario: Ensuring overlay is visible');
      }
    }, 0);
    
    try {
      await axios.post(`${API_BASE_URL}/simulation/skip`);
      //console.log('handleSkipScenario: Skip API call successful');
      // Do not reset isSkipping here; let WebSocket handle it
    } catch (e) {
      //console.log('handleSkipScenario: Skip API call failed', e);
      setIsSkipping(false);
      setStatus('Ready to Start');
      setError('Failed to skip scenario');
    }
  };

  // Instruction message
  const instructionMessage = React.useMemo(() => 
    getInstructionMessage({
      selectedScenariosLength: selectedScenarios.length,
      isRunning,
      backendState,
      isStarting,
      isStopping,
      isSkipping
    }), 
    [selectedScenarios.length, isRunning, backendState, isStarting, isStopping, isSkipping]
  );

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
                  disabled={isStarting || isStopping || isSkipping || backendState.is_starting || backendState.is_stopping || backendState.is_skipping || isRunning || backendState.is_running}
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
                      disabled={buttonStates.isStartDisabled || isRunning || isSkipping || backendState.is_skipping}
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
                      disabled={buttonStates.isStartDisabled || isRunning || isSkipping || backendState.is_skipping}
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
                  disabled={buttonStates.isStartDisabled}
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
                  disabled={buttonStates.isPauseDisabled}
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
                  disabled={buttonStates.isSkipDisabled}
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
                  disabled={buttonStates.isStopDisabled}
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
            id="simulationCanvas"
            ref={canvasRef}
            style={canvasStyle}
          />
          <Box sx={overlayStyle}>
            <img
              src="/wavy_logo_loading.gif"
              alt="Loading"
              style={loadingImageStyle}
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
              {error ? error : status}
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
            {!error && (
              <Typography
                variant="body2"
                sx={{
                  color: '#888',
                  mt: 1,
                  textAlign: 'center',
                  textShadow: '0 1px 2px rgba(0,0,0,0.5)'
                }}
              >
                {instructionMessage}
              </Typography>
            )}
          </Box>
        </Box>
      </Box>
    </>
  );
}

export default Dashboard; 