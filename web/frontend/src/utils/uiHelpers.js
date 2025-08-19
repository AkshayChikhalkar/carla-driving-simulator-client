// Button state computation
export const computeButtonStates = ({
  isRunning,
  selectedScenariosLength,
  isStarting,
  isStopping,
  isSkipping,
  backendState
}) => {
  // eslint-disable-next-line no-unused-vars
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

// Canvas style computation
export const computeCanvasStyle = ({
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

// Overlay style computation
export const computeOverlayStyle = ({
  isStarting,
  backendState,
  isStopping,
  isSkipping,
  isRunning,
  hasReceivedFrame
}) => {
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

// Loading image style computation
export const computeLoadingImageStyle = ({
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

// Instruction message helper
export const getInstructionMessage = ({
  selectedScenariosLength,
  isRunning,
  backendState,
  isStarting,
  isStopping,
  isSkipping
}) => {
  if (selectedScenariosLength === 0) {
    return 'Select one or more scenarios from the dropdown and click Start';
  }
  
  if (isRunning || backendState.is_running) {
    return '';
  }
  
  // Helper function to get progress text
  const getProgressText = () => {
    if (backendState.scenario_index && backendState.total_scenarios) {
      return ` (${backendState.scenario_index}/${backendState.total_scenarios})`;
    }
    return '';
  };
  
  // Helper function to get current scenario name
  const getCurrentScenarioName = () => {
    if (backendState.current_scenario) {
      return `\nCurrent: ${backendState.current_scenario}`;
    }
    return '';
  };
  
  if (isStarting || backendState.is_starting) {
    return `Please wait while the system initializes`;
  }
  
  if (isStopping || backendState.is_stopping) {
    return `\nPlease wait while the system shuts down`;
  }
  
  if (isSkipping || backendState.is_skipping) {
    return `Skipping scenario...${getProgressText()}${getCurrentScenarioName()}`;
  }
  
  return 'Click Start button to start the simulation';
}; 
