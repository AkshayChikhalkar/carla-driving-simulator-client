import { useEffect, useRef, useCallback, useState } from 'react';
import logger from '../utils/logger';

const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss' : 'ws';
// Build WS URL using per-tab storage for strict isolation between tabs/tenants
const getWebSocketUrl = () => {
  const base = `${WS_PROTOCOL}://${window.location.host}/ws/simulation-view`;
  const params = new URLSearchParams();
  const token = sessionStorage.getItem('access_token');
  const tenant = sessionStorage.getItem('tenant_id');
  if (tenant) params.set('tenant_id', tenant);
  if (token) params.set('token', token);
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
};

// In development, rely on setupProxy to forward '/api' to backend

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
  setHudData,
  canvasRef,
}) => {
  const wsRef = useRef(null);
  const backendStateRef = useRef(backendState);
  const isSkippingRef = useRef(isSkipping);
  const connectionEstablishedRef = useRef(false); // Track if connection is already established
  const [authVersion, setAuthVersion] = useState(0); // Bump when auth/tenant changes in this tab

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
      // Clear HUD data when simulation stops to prevent showing stale data
      if (setHudData) {
        setHudData(null);
      }
      // Only clear hasReceivedFrame when simulation is completely stopped (not during transitions)
      // This keeps the last frame visible until new frames arrive or simulation actually stops
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
  }, [setBackendState, setIsStopping, setIsStarting, setIsSkipping, setIsRunning, setHasReceivedFrame, setStatus, setHudData]);

  const handleVideoFrame = useCallback((frameData) => {
    // Always mark frame received during transitions to keep canvas visible and prevent freezing
    // This ensures other users don't see frozen views when one user skips
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
      const canvas = (canvasRef && canvasRef.current) ? canvasRef.current : document.getElementById('simulationCanvas');
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
  }, [setHasReceivedFrame, canvasRef]);

  // Optional HUD payloads (if backend sends them)
  const handleHudMessage = useCallback((data) => {
    try {
      if (setHudData) {
        // Only update HUD data if we're actively receiving frames
        // This prevents showing stale HUD data when simulation is stopped
        const currentBackendState = backendStateRef.current;
        if (currentBackendState.is_running || currentBackendState.is_skipping || currentBackendState.is_starting) {
          setHudData(data.payload);
        }
      }
    } catch (_) {}
  }, [setHudData]);

  useEffect(() => {
    let ws;
    let isUnmounted = false;
    let connectionAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;

    const openWebSocket = () => {
      // Close any existing connection before opening a new one
      if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        try { wsRef.current.close(); } catch (_) {}
      }
      try {
        ws = new WebSocket(getWebSocketUrl());
        wsRef.current = ws;
        logger.info('WebSocket connection attempt started');
        ws.onopen = () => {
          connectionAttempts = 0;
          connectionEstablishedRef.current = true;
          if (!backendStateRef.current.is_running) {
            setStatus('Connected to simulation server');
          }
        };
        ws.onclose = (e) => {
          connectionEstablishedRef.current = false;
          logger.info('WebSocket connection closed', e);
          if (!backendStateRef.current.is_running) {
            setStatus('Disconnected from simulation server');
          }
          if (!isUnmounted && connectionAttempts < MAX_RECONNECT_ATTEMPTS) {
            connectionAttempts += 1;
            setTimeout(() => {
              if (!isUnmounted) openWebSocket();
            }, 2000);
          }
        };
        ws.onerror = (e) => {
          logger.error('WebSocket error', e);
          setStatus('Error in simulation connection');
        };
        ws.onmessage = (event) => {
          try {
            if (typeof event.data === 'string' && event.data.startsWith('{')) {
              const data = JSON.parse(event.data);
              if (data.type === 'status') handleStatusMessage(data);
              else if (data.type === 'hud') handleHudMessage(data);
            } else {
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

    openWebSocket();

    // Listen for explicit auth change events to rebuild WS with new token/tenant
    const onAuthChanged = () => setAuthVersion((v) => v + 1);
    window.addEventListener('auth-changed', onAuthChanged);

    return () => {
      isUnmounted = true;
      window.removeEventListener('auth-changed', onAuthChanged);
      if (wsRef.current) {
        try { wsRef.current.close(); } catch (_) {}
        logger.info('WebSocket connection closed by component unmount');
      }
    };
    // Recreate socket when authVersion changes (login/logout/tenant switch)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handleStatusMessage, handleVideoFrame, setStatus, authVersion, setHudData]);

  return { wsRef };
}; 
