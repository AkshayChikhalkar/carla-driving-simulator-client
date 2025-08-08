import { useEffect, useRef, useCallback } from 'react';
import logger from '../utils/logger';

const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss' : 'ws';
// Always use current host and let dev proxy forward to backend in development
const WS_BASE_URL = `${WS_PROTOCOL}://${window.location.host}/ws/simulation-view`;

// In development, rely on setupProxy to forward '/api' to backend

// Global flag to prevent multiple WebSocket initializations
let globalWebSocketInitialized = false;

export const useWebSocketConnection = ({
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
}) => {
  const wsRef = useRef(null);
  const backendStateRef = useRef(backendState);
  const isSkippingRef = useRef(isSkipping);
  const connectionEstablishedRef = useRef(false); // Track if connection is already established

  // Keep refs updated with latest values
  useEffect(() => {
    backendStateRef.current = backendState;
  }, [backendState]);

  useEffect(() => {
    isSkippingRef.current = isSkipping;
  }, [isSkipping]);

  const handleStatusMessage = useCallback((data) => {
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

    // Only log significant state changes (major transitions only)
    const currentBackendState = backendStateRef.current;
    const hasMajorStateChange = 
      (data.is_running && !currentBackendState.is_running) ||
      (!data.is_running && currentBackendState.is_running) ||
      (data.is_starting && !currentBackendState.is_starting) ||
      (data.is_stopping && !currentBackendState.is_stopping) ||
      (data.is_skipping && !currentBackendState.is_skipping);
    
    // Only log significant state changes to reduce log flood
    if (hasMajorStateChange) {
      // Only log start/stop events, not every minor transition
      if ((data.is_running && !currentBackendState.is_running) || 
          (!data.is_running && currentBackendState.is_running)) {
        logger.info(`Simulation state change: is_running=${data.is_running}, is_starting=${data.is_starting}, is_stopping=${data.is_stopping}, is_skipping=${data.is_skipping}, status_message=${data.status_message}`);
      }
    }

    // Always reset UI if backend says simulation is stopped
    if (!data.is_running && !data.is_starting && !data.is_stopping && !data.is_skipping) {
      setIsStopping(false);
      setIsStarting(false);
      setIsSkipping(false);
      setIsRunning(false);
      // Don't reset hasReceivedFrame immediately - let it fade out smoothly
      setTimeout(() => {
        setHasReceivedFrame(false);
      }, 6000); // Keep last frame visible for 4 seconds after stop for smoother transition
      setStatus('Ready to Start');
      return;
    }

    // Reset transition flags when backend confirms operations are complete
    if (data.is_running && !data.is_starting) {
      setTimeout(() => {
        setIsStarting(false);
      }, 2000); // Longer delay for smoother transition
    }
    if (!data.is_running && !data.is_stopping) {
      setTimeout(() => {
        setIsStopping(false);
      }, 2000); // Longer delay for smoother transition
    }
    if (!data.is_skipping) {
      // Add a small delay to ensure skip operation is fully complete
      setTimeout(() => {
        setIsSkipping(false);
      }, 1500); // Longer delay for smoother transition
    }

    // Use backend status message - only override with local transition states for immediate UX feedback
    if (data.is_starting) {
      setStatus(data.status_message || 'Hang on,\nLoading Simulation...');
    } else if (data.is_stopping) {
      setStatus(data.status_message || 'Stopping simulation...\nPlease wait');
      
      // Don't clear canvas or reset frame state during stop to prevent flickering
      // The canvas will remain visible with the last frame during stop transition
    } else if (data.is_skipping) {
      setStatus(data.status_message || 'Skipping scenario...');
      
      // Don't clear canvas or reset frame state during skip to prevent flickering
      // The canvas will remain visible with the last frame during skip transition
    } else if (data.is_running && data.status_message) {
      // If simulation is running, use the backend status message
      setStatus(data.status_message);
    } else {
      // Default status
      const newStatus = data.status_message || 'Ready to Start';
      setStatus(newStatus);
    }

    // Update isRunning based on backend state
    setIsRunning(data.is_running || false);
  }, [setBackendState, setIsStopping, setIsStarting, setIsSkipping, setIsRunning, setHasReceivedFrame, setStatus]);

  const handleVideoFrame = useCallback((frameData) => {
    // Don't block drawing during transitions - let frames come through for smoother experience
    // Only mark frame received if not in any transition
    const currentIsSkipping = isSkippingRef.current;
    const currentBackendState = backendStateRef.current;
    
    // Mark frame received if not in any transition
    if (!currentIsSkipping && !currentBackendState.is_skipping && 
        !currentBackendState.is_starting && !currentBackendState.is_stopping) {
      setHasReceivedFrame(true);
    }
    
    // Always draw frames during transitions to keep canvas updated
    const img = new Image();
    img.onload = () => {
      const canvas = document.getElementById('simulationCanvas'); // Get canvas by ID
      if (canvas) {
        const ctx = canvas.getContext('2d');
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0);
        // logger.debug('Frame drawn on canvas', { width: img.width, height: img.height }); // Uncomment for debug
      }
    };
    img.src = `data:image/jpeg;base64,${frameData}`;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setHasReceivedFrame]);

  useEffect(() => {
    // Prevent multiple initializations across component re-renders
    if (globalWebSocketInitialized) {
      return;
    }
    
    let ws;
    let isUnmounted = false;
    let connectionAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;
    let setupCompleted = false; // Prevent multiple setups

    const setupWebSocket = () => {
      // Prevent multiple setups
      if (setupCompleted) {
        return;
      }
      
      // Prevent multiple connections - check if already connected or connecting
      if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        return;
      }
      
      // Prevent excessive reconnection attempts
      if (connectionAttempts >= MAX_RECONNECT_ATTEMPTS) {
        logger.warn('Max WebSocket reconnection attempts reached');
        return;
      }
      
      // Prevent duplicate connections if already established
      if (connectionEstablishedRef.current) {
        return;
      }
      
      setupCompleted = true; // Mark setup as completed
      connectionAttempts++;
      try {
        ws = new WebSocket(WS_BASE_URL);
        wsRef.current = ws;
        logger.info('WebSocket connection attempt started');
        ws.onopen = () => {
          connectionAttempts = 0; // Reset on successful connection
          connectionEstablishedRef.current = true; // Mark as established
          globalWebSocketInitialized = true; // Mark as globally initialized
          // Only show connected message if simulation is not running
          if (!backendStateRef.current.is_running) {
            setStatus('Connected to simulation server');
          }
        };

        ws.onclose = (e) => {
          connectionEstablishedRef.current = false; // Mark as disconnected
          globalWebSocketInitialized = false; // Reset global flag
          logger.info('WebSocket connection closed', e);
          // Only show disconnected message if simulation is not running
          if (!backendStateRef.current.is_running) {
            setStatus('Disconnected from simulation server');
          }
          // Attempt to reconnect after 2 seconds, but only if not unmounted
          if (!isUnmounted && connectionAttempts < MAX_RECONNECT_ATTEMPTS) {
            setTimeout(() => {
              if (!isUnmounted) {
                setupWebSocket();
              }
            }, 2000);
          }
        };

        ws.onerror = (e) => {
          logger.error('WebSocket error', e);
          setStatus('Error in simulation connection');
        };

        ws.onmessage = (event) => {
          try {
            // If it's a status message (JSON)
            if (event.data.startsWith('{')) {
              const data = JSON.parse(event.data);
              if (data.type === 'status') {
                handleStatusMessage(data);
              }
            } else {
              // It's a video frame (base64 string)
              handleVideoFrame(event.data);
            }
          } catch (e) {
            logger.error('Error parsing WebSocket message', e);
          }
        };
      } catch (err) {
        logger.error('WebSocket setup failed', err);
      }
    };

    setupWebSocket();

    return () => {
      isUnmounted = true;
      connectionEstablishedRef.current = false; // Reset connection state
      globalWebSocketInitialized = false; // Reset global flag
      if (wsRef.current) {
        wsRef.current.close();
        logger.info('WebSocket connection closed by component unmount');
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handleStatusMessage, handleVideoFrame, setStatus]);

  return { wsRef };
}; 
