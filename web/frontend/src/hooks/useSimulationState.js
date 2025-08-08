import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const API_BASE_URL = window.location.hostname === 'localhost' ? '/api' : `http://${window.location.hostname}:8081/api`;

export const useSimulationState = () => {
  // Local transition states
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [isSkipping, setIsSkipping] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [hasReceivedFrame, setHasReceivedFrame] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState(null);

  // Backend state tracking
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

  // Improved state synchronization with quicker start/skip transitions
  useEffect(() => {
    // Reset isStarting when backend confirms start is complete
    if (isStarting && backendState.is_running && !backendState.is_starting) {
      const timer = setTimeout(() => {
        if (isStarting && backendState.is_running && !backendState.is_starting) {
          setIsStarting(false);
        }
      }, 1000); // Quicker start transition
      return () => clearTimeout(timer);
    }
    
    // Reset isStopping when backend confirms stop is complete
    if (isStopping && !backendState.is_running && !backendState.is_stopping) {
      const timer = setTimeout(() => {
        if (isStopping && !backendState.is_running && !backendState.is_stopping) {
          setIsStopping(false);
        }
      }, 3000); // Keep stop transition smooth
      return () => clearTimeout(timer);
    }
    
    // Reset isSkipping when backend confirms skip is complete
    if (isSkipping && !backendState.is_skipping) {
      const timer = setTimeout(() => {
        if (isSkipping && !backendState.is_skipping) {
          setIsSkipping(false);
        }
      }, 800); // Quicker skip transition
      return () => clearTimeout(timer);
    }
  }, [isStarting, isStopping, isSkipping, backendState.is_running, backendState.is_starting, backendState.is_stopping, backendState.is_skipping]);

  // Fallback mechanism - only for stuck states with longer timeouts
  useEffect(() => {
    const timers = [];
    
    if (isStarting && backendState.is_running && !backendState.is_starting) {
      const timer = setTimeout(() => {
        if (isStarting && backendState.is_running && !backendState.is_starting) {
          setIsStarting(false);
        }
      }, 5000); // Much longer fallback timeout
      timers.push(timer);
    }
    
    if (isStopping && !backendState.is_running && !backendState.is_stopping) {
      const timer = setTimeout(() => {
        if (isStopping && !backendState.is_running && !backendState.is_stopping) {
          setIsStopping(false);
        }
      }, 5000); // Much longer fallback timeout
      timers.push(timer);
    }
    
    if (isSkipping && !backendState.is_skipping) {
      const timer = setTimeout(() => {
        if (isSkipping && !backendState.is_skipping) {
          setIsSkipping(false);
        }
      }, 4000); // Longer fallback timeout
      timers.push(timer);
    }
    
    return () => timers.forEach(timer => clearTimeout(timer));
  }, [isStarting, isStopping, isSkipping, backendState.is_running, backendState.is_starting, backendState.is_stopping, backendState.is_skipping]);

  // Action handlers
  const startSimulation = useCallback(async (scenarios, debug, report) => {
    if (scenarios.length === 0) {
      setError('Please select at least one scenario');
      return false;
    }
    
    setIsStarting(true);
    setIsStopping(false);
    setIsSkipping(false);
    setStatus('Hang on,\nLoading Simulation...');
    setError(null);
    
    try {
      await axios.post(`${API_BASE_URL}/simulation/start`, {
        scenarios,
        debug,
        report
      });
      return true;
    } catch (e) {
      setIsStarting(false);
      setStatus('Ready to Start');
      setError('Failed to start simulation');
      return false;
    }
  }, []);

  const stopSimulation = useCallback(async () => {
    setIsStopping(true);
    setIsStarting(false);
    setIsSkipping(false);
    setStatus('Stopping simulation...\nPlease wait');
    setError(null);
    
    // Don't reset hasReceivedFrame immediately - let it fade out smoothly
    // The frame state will be reset by the WebSocket connection after a delay
    
    try {
      await axios.post(`${API_BASE_URL}/simulation/stop`);
      return true;
    } catch (e) {
      setIsStopping(false);
      setStatus('Ready to Start');
      setError('Failed to stop simulation');
      return false;
    }
  }, []);

  const skipScenario = useCallback(async () => {
    setIsSkipping(true);
    setIsStarting(false);
    setIsStopping(false);
    // Don't reset hasReceivedFrame during skip to keep canvas visible
    setStatus('Skipping scenario...');
    setError(null);
    
    try {
      await axios.post(`${API_BASE_URL}/simulation/skip`);
      return true;
    } catch (e) {
      setIsSkipping(false);
      setStatus('Ready to Start');
      setError('Failed to skip scenario');
      return false;
    }
  }, []);

  const pauseSimulation = useCallback(() => {
    const newPauseState = !isPaused;
    setIsPaused(newPauseState);
    setStatus(newPauseState ? 'Simulation paused' : 'Simulation resumed');
  }, [isPaused]);

  // Computed states
  const anyTransition = isStarting || isStopping || isSkipping;
  const isLastScenario = backendState.scenario_index >= backendState.total_scenarios;
  const isSingleScenario = backendState.total_scenarios <= 1;

  return {
    // State
    isStarting,
    isStopping,
    isSkipping,
    isRunning,
    isPaused,
    hasReceivedFrame,
    status,
    error,
    backendState,
    anyTransition,
    isLastScenario,
    isSingleScenario,
    
    // Setters
    setIsStarting,
    setIsStopping,
    setIsSkipping,
    setIsRunning,
    setIsPaused,
    setHasReceivedFrame,
    setStatus,
    setError,
    setBackendState,
    
    // Actions
    startSimulation,
    stopSimulation,
    skipScenario,
    pauseSimulation
  };
}; 
