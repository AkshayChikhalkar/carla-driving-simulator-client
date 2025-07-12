import React, { useState, useRef } from 'react';
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
import { useSimulationState } from '../hooks/useSimulationState';
import { useWebSocketConnection } from '../hooks/useWebSocketConnection';
import { useScenarioSelection } from '../hooks/useScenarioSelection';
import { 
  computeButtonStates, 
  computeCanvasStyle, 
  computeOverlayStyle, 
  computeLoadingImageStyle,
  getInstructionMessage 
} from '../utils/uiHelpers';

function Dashboard({ onThemeToggle, isDarkMode }) {
  const [debug, setDebug] = useState(false);
  const [report, setReport] = useState(false);
  const canvasRef = useRef(null);

  // Use custom hooks for state management
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

  // Memoized button states
  const buttonStates = React.useMemo(() => 
    computeButtonStates({
      isRunning,
      selectedScenariosLength: selectedScenarios.length,
      isStarting,
      isStopping,
      isSkipping,
      backendState
    }), 
    [isRunning, selectedScenarios.length, isStarting, isStopping, isSkipping, backendState]
  );

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

  // Button handlers
  const handleStart = async () => {
    await startSimulation(selectedScenarios, debug, report);
  };

  const handleStop = async () => {
    await stopSimulation();
  };

  const handleSkip = async () => {
    await skipScenario();
  };

  const handlePause = () => {
    pauseSimulation();
  };

  // Instruction message
  const instructionMessage = getInstructionMessage({
    selectedScenariosLength: selectedScenarios.length,
    isRunning,
    backendState,
    isStarting,
    isStopping,
    isSkipping
  });

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
                  disabled={isStarting || isStopping || isSkipping || isRunning || backendState.is_running || backendState.is_skipping}
                  size="small"
                  renderValue={getRenderValue}
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
                    display: 'none'
                  }}
                >
                  {isPaused ? 'Resume' : 'Pause'}
                </Button>
                <Button
                  variant="contained"
                  color="warning"
                  startIcon={<SkipNextIcon />}
                  onClick={handleSkip}
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
            {!error && !isStarting && !isStopping && !isSkipping && (
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