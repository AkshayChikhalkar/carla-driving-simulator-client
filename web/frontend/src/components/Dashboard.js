import React, { useState, useRef, useCallback } from 'react';
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
  Paper,
  CircularProgress
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Pause as PauseIcon,
  SkipNext as SkipNextIcon
} from '@mui/icons-material';
import logger from '../utils/logger';
import { useWebSocketConnection } from '../hooks/useWebSocketConnection';
import { useSimulationState } from '../hooks/useSimulationState';
import { useScenarioSelection } from '../hooks/useScenarioSelection';
import { getInstructionMessage } from '../utils/uiHelpers';

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

// Memoized Control Panel Component
const ControlPanel = React.memo(({
  scenarios,
  selectedScenarios,
  status,
  debug,
  report,
  buttonStates,
  isStarting,
  isStopping,
  isSkipping,
  isPaused,
  backendState,
  isRunning,
  dropdownOpen,
  onScenarioChange,
  onDropdownOpen,
  onDropdownClose,
  onDebugChange,
  onReportChange,
  onStart,
  onStop,
  onPause,
  onSkip
}) => {
  const renderValue = useCallback((selected) => {
    if (selected.includes('all')) return 'All Scenarios';
    if (selected.length === 0) return 'Select scenarios...';
    if (selected.length === 1) return selected[0];
    return `${selected.length} scenarios selected`;
  }, []);

  return (
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
              onChange={onScenarioChange}
              onOpen={onDropdownOpen}
              onClose={onDropdownClose}
                  open={dropdownOpen}
              disabled={isStarting || isStopping || isSkipping || backendState.is_starting || backendState.is_stopping || backendState.is_skipping || isRunning || backendState.is_running}
                  size="small"
              renderValue={renderValue}
                  MenuProps={{
                    PaperProps: {
                      style: {
                        maxHeight: 300,
                    width: 300
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
                  onChange={onDebugChange}
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
                  onChange={onReportChange}
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
              onClick={onStart}
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
              onClick={onPause}
              disabled={buttonStates.isPauseDisabled}
                  size="small"
                  sx={{
                    '& .MuiButton-startIcon': {
                      marginRight: 0.5,
                      marginLeft: 0
                    },
                display: 'none'
                  }}
                >
                  {isPaused ? 'Resume' : 'Pause'}
                </Button>
                <Button
                  variant="contained"
                  color="warning"
                  startIcon={<SkipNextIcon />}
              onClick={onSkip}
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
              onClick={onStop}
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
  );
});

// Memoized Simulation View Component
const SimulationView = React.memo(({
  canvasRef,
  canvasStyle,
  overlayStyle,
  loadingImageStyle,
  error,
  status,
  instructionMessage
}) => {
  return (
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
  );
});

// Loading Component
const LoadingSpinner = React.memo(() => (
  <Box
    sx={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '200px',
      width: '100%'
    }}
  >
    <CircularProgress size={60} />
    <Typography variant="h6" sx={{ ml: 2 }}>
      Loading scenarios...
    </Typography>
  </Box>
));

function Dashboard({ onThemeToggle, isDarkMode }) {
  const [debug, setDebug] = useState(false);
  const [report, setReport] = useState(false);
  const canvasRef = useRef(null);
  
  // Use existing hooks for state management
  const {
    isStarting,
    isStopping,
    isSkipping,
    isRunning,
    isPaused,
    hasReceivedFrame,
    status,
    error,
    backendState,
    setIsStarting,
    setIsStopping,
    setIsSkipping,
    setIsRunning,
    setIsPaused,
    setHasReceivedFrame,
    setStatus,
    setBackendState,
    startSimulation,
    stopSimulation,
    skipScenario,
    pauseSimulation
  } = useSimulationState();

  const {
    scenarios,
    selectedScenarios,
    dropdownOpen,
    handleScenarioChangeEnhanced,
    handleDropdownOpen,
    handleDropdownClose,
    getRenderValue
  } = useScenarioSelection();

  // Use WebSocket connection hook
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
    canvasRef
  });

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

  // Optimized event handlers with useCallback
  const handleStart = useCallback(async () => {
    await startSimulation(selectedScenarios, debug, report);
  }, [startSimulation, selectedScenarios, debug, report]);

  const handleStop = useCallback(async () => {
    await stopSimulation();
  }, [stopSimulation]);

  const handleSkip = useCallback(async () => {
    await skipScenario();
  }, [skipScenario]);

  const handlePause = useCallback(() => {
    pauseSimulation();
  }, [pauseSimulation]);

  // Optimized checkbox handlers with useCallback
  const handleDebugChange = useCallback((e) => {
    setDebug(e.target.checked);
  }, []);

  const handleReportChange = useCallback((e) => {
    setReport(e.target.checked);
  }, []);

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

  // Show loading spinner while scenarios are loading
  if (scenarios.length === 0 && status !== 'Error loading scenarios') {
    return <LoadingSpinner />;
  }

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
        <ControlPanel
          scenarios={scenarios}
          selectedScenarios={selectedScenarios}
          status={status}
          debug={debug}
          report={report}
          buttonStates={buttonStates}
          isStarting={isStarting}
          isStopping={isStopping}
          isSkipping={isSkipping}
          isPaused={isPaused}
          backendState={backendState}
          isRunning={isRunning}
          dropdownOpen={dropdownOpen}
          onScenarioChange={handleScenarioChangeEnhanced}
          onDropdownOpen={handleDropdownOpen}
          onDropdownClose={handleDropdownClose}
          onDebugChange={handleDebugChange}
          onReportChange={handleReportChange}
          onStart={handleStart}
          onStop={handleStop}
          onPause={handlePause}
          onSkip={handleSkip}
        />
        <SimulationView
          canvasRef={canvasRef}
          canvasStyle={canvasStyle}
          overlayStyle={overlayStyle}
          loadingImageStyle={loadingImageStyle}
          error={error}
          status={status}
          instructionMessage={instructionMessage}
        />
      </Box>
    </>
  );
}

export default React.memo(Dashboard); 