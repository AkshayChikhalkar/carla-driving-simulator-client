import { useEffect, useRef, useCallback, useState } from 'react';
import logger from '../utils/logger';

const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss' : 'ws';

// Build WebSocket URL for control commands
const getControlWebSocketUrl = () => {
  const base = `${WS_PROTOCOL}://${window.location.host}/ws/control`;
  const params = new URLSearchParams();
  const token = sessionStorage.getItem('access_token');
  const tenant = sessionStorage.getItem('tenant_id');
  if (tenant) params.set('tenant_id', tenant);
  if (token) params.set('token', token);
  const qs = params.toString();
  return qs ? `${base}?${qs}` : base;
};

export const useWebControls = (isRunning = false, controllerType = 'web_keyboard', selectedGamepadIndex = 0) => {
  const wsRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentControl, setCurrentControl] = useState({
    throttle: 0.0,
    brake: 0.0,
    steer: 0.0,
    hand_brake: false,
    reverse: false,
    manual_gear_shift: false,
    gear: 1,
    quit: false
  });
  const [availableGamepads, setAvailableGamepads] = useState([]);

  // Keyboard state tracking
  const keysPressed = useRef(new Set());
  const gamepadState = useRef(null);

  // Send control command to backend
  const sendControlCommand = useCallback((control) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && isRunning) {
      try {
        wsRef.current.send(JSON.stringify({
          controller_type: controllerType,
          control: control
        }));
      } catch (error) {
        logger.error('Failed to send control command:', error);
      }
    }
  }, [controllerType, isRunning]);

  // Update control state and send to backend
  const updateControl = useCallback((newControl) => {
    setCurrentControl(prev => {
      const updated = { ...prev, ...newControl };
      if (isRunning) {
        sendControlCommand(updated);
      }
      return updated;
    });
  }, [isRunning, sendControlCommand]);

  // Keyboard event handlers
  const handleKeyDown = useCallback((event) => {
    if (!isRunning) return;
    
    const key = event.key.toLowerCase();
    keysPressed.current.add(key);
    
    let controlUpdate = {};
    
    // Map keys to controls
    switch (key) {
      case 'w':
      case 'arrowup':
        controlUpdate.throttle = 1.0;
        break;
      case 's':
      case 'arrowdown':
        controlUpdate.brake = 1.0;
        break;
      case 'a':
      case 'arrowleft':
        controlUpdate.steer = -0.7;
        break;
      case 'd':
      case 'arrowright':
        controlUpdate.steer = 0.7;
        break;
      case ' ':
        controlUpdate.brake = 1.0;
        break;
      case 'q':
        controlUpdate.hand_brake = true;
        break;
      case 'r':
        controlUpdate.reverse = !currentControl.reverse;
        break;
      case 'escape':
        controlUpdate.quit = true;
        break;
      case '1':
      case '2':
      case '3':
      case '4':
      case '5':
      case '6':
        if (currentControl.manual_gear_shift) {
          controlUpdate.gear = parseInt(key);
        }
        break;
      case 'm':
        controlUpdate.manual_gear_shift = !currentControl.manual_gear_shift;
        break;
    }
    
    if (Object.keys(controlUpdate).length > 0) {
      updateControl(controlUpdate);
    }
  }, [isRunning, currentControl, updateControl]);

  const handleKeyUp = useCallback((event) => {
    if (!isRunning) return;
    
    const key = event.key.toLowerCase();
    keysPressed.current.delete(key);
    
    let controlUpdate = {};
    
    // Reset controls when keys are released
    switch (key) {
      case 'w':
      case 'arrowup':
        controlUpdate.throttle = 0.0;
        break;
      case 's':
      case 'arrowdown':
        controlUpdate.brake = 0.0;
        break;
      case 'a':
      case 'arrowleft':
      case 'd':
      case 'arrowright':
        controlUpdate.steer = 0.0;
        break;
      case ' ':
        controlUpdate.brake = 0.0;
        break;
      case 'q':
        controlUpdate.hand_brake = false;
        break;
    }
    
    if (Object.keys(controlUpdate).length > 0) {
      updateControl(controlUpdate);
    }
  }, [isRunning, updateControl]);

  // Gamepad support
  const pollGamepad = useCallback(() => {
    if (!isRunning || controllerType !== 'web_gamepad') return;
    
    const gamepads = navigator.getGamepads();
    const gamepad = gamepads[selectedGamepadIndex];
    
    if (gamepad) {
      gamepadState.current = gamepad;
      
      // Map gamepad axes and buttons to controls
      const controlUpdate = {
        throttle: Math.max(0, gamepad.axes[5] || 0), // Right trigger
        brake: Math.max(0, gamepad.axes[4] || 0),    // Left trigger
        steer: gamepad.axes[0] || 0,                 // Left stick X
        hand_brake: gamepad.buttons[1]?.pressed || false, // B button
        reverse: gamepad.buttons[2]?.pressed || false,    // X button
        quit: gamepad.buttons[9]?.pressed || false,       // Start button
        gamepad_index: selectedGamepadIndex              // Include gamepad index
      };
      
      updateControl(controlUpdate);
    }
  }, [isRunning, controllerType, selectedGamepadIndex, updateControl]);

  // Detect available gamepads
  const detectGamepads = useCallback(() => {
    const gamepads = navigator.getGamepads();
    const connected = [];
    
    for (let i = 0; i < gamepads.length; i++) {
      const gamepad = gamepads[i];
      if (gamepad) {
        connected.push({
          index: i,
          id: gamepad.id || `Gamepad ${i}`,
          connected: gamepad.connected
        });
      }
    }
    
    setAvailableGamepads(connected);
  }, []);

  // Gamepad connection/disconnection handlers
  const handleGamepadConnected = useCallback((event) => {
    logger.info(`Gamepad connected: ${event.gamepad.id} (index: ${event.gamepad.index})`);
    detectGamepads();
  }, [detectGamepads]);

  const handleGamepadDisconnected = useCallback((event) => {
    logger.info(`Gamepad disconnected: ${event.gamepad.id} (index: ${event.gamepad.index})`);
    detectGamepads();
  }, [detectGamepads]);

  // WebSocket connection
  useEffect(() => {
    if (!isRunning) {
      setIsConnected(false);
      return;
    }

    let ws;
    let gamepadInterval;

    const connectWebSocket = () => {
      try {
        ws = new WebSocket(getControlWebSocketUrl());
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
          logger.info('Control WebSocket connected');
        };

        ws.onclose = (event) => {
          setIsConnected(false);
          if (event.code === 1000) {
            logger.info('Control WebSocket disconnected normally');
          } else if (event.code === 1005) {
            logger.info('Control WebSocket connection closed (no status received)');
          } else {
            logger.info(`Control WebSocket disconnected with code: ${event.code}`);
          }
        };

        ws.onerror = (error) => {
          logger.error('Control WebSocket error:', error);
          setIsConnected(false);
          // Don't try to reconnect immediately - let the useEffect handle it
        };

      } catch (error) {
        logger.error('Failed to create control WebSocket:', error);
      }
    };

    connectWebSocket();

    // Set up gamepad polling
    if (controllerType === 'web_gamepad') {
      gamepadInterval = setInterval(pollGamepad, 16); // ~60fps
    }

    // Detect initial gamepads
    detectGamepads();

    return () => {
      if (ws) {
        ws.close();
      }
      if (gamepadInterval) {
        clearInterval(gamepadInterval);
      }
    };
  }, [isRunning, controllerType, pollGamepad]);

  // Keyboard event listeners
  useEffect(() => {
    if (!isRunning || controllerType !== 'web_keyboard') return;

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('keyup', handleKeyUp);
    };
  }, [isRunning, controllerType, handleKeyDown, handleKeyUp]);

  // Gamepad connection event listeners
  useEffect(() => {
    if (controllerType !== 'web_gamepad') return;

    window.addEventListener('gamepadconnected', handleGamepadConnected);
    window.addEventListener('gamepaddisconnected', handleGamepadDisconnected);

    return () => {
      window.removeEventListener('gamepadconnected', handleGamepadConnected);
      window.removeEventListener('gamepaddisconnected', handleGamepadDisconnected);
    };
  }, [controllerType, handleGamepadConnected, handleGamepadDisconnected]);

  // Reset controls when simulation stops
  useEffect(() => {
    if (!isRunning) {
      setCurrentControl({
        throttle: 0.0,
        brake: 0.0,
        steer: 0.0,
        hand_brake: false,
        reverse: false,
        manual_gear_shift: false,
        gear: 1,
        quit: false
      });
      keysPressed.current.clear();
      gamepadState.current = null;
    }
  }, [isRunning]);

  return {
    isConnected,
    currentControl,
    updateControl,
    availableGamepads,
    selectedGamepadIndex
  };
};
