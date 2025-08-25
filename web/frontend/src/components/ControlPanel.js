import React, { useState } from 'react';
import { Box, Paper, Typography, Grid, Chip, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import { useWebControls } from '../hooks/useWebControls';

const WebControlPanel = ({ isRunning, controllerType = 'web_keyboard' }) => {
  const [selectedGamepadIndex, setSelectedGamepadIndex] = useState(0);
  const { isConnected, currentControl, availableGamepads } = useWebControls(isRunning, controllerType, selectedGamepadIndex);

  const getControlColor = (value, isBoolean = false) => {
    if (isBoolean) {
      return value ? 'success' : 'default';
    }
    return value > 0 ? 'primary' : 'default';
  };

  const getControlLabel = (key, value) => {
    switch (key) {
      case 'throttle':
        return `Throttle: ${(value * 100).toFixed(0)}%`;
      case 'brake':
        return `Brake: ${(value * 100).toFixed(0)}%`;
      case 'steer':
        const direction = value > 0 ? 'Right' : value < 0 ? 'Left' : 'Center';
        return `Steer: ${direction} ${Math.abs(value * 100).toFixed(0)}%`;
      case 'hand_brake':
        return `Hand Brake: ${value ? 'ON' : 'OFF'}`;
      case 'reverse':
        return `Reverse: ${value ? 'ON' : 'OFF'}`;
      case 'manual_gear_shift':
        return `Manual: ${value ? 'ON' : 'OFF'}`;
      case 'gear':
        return `Gear: ${value}`;
      default:
        return `${key}: ${value}`;
    }
  };

  return (
    <Paper 
      elevation={3} 
      sx={{ 
        p: 2, 
        mb: 2,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        color: 'white',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}
    >
             <Typography variant="h6" gutterBottom sx={{ color: 'white', mb: 2 }}>
         Control Panel
         <Chip 
           label={controllerType.replace('web_', '').toUpperCase()} 
           size="small" 
           sx={{ ml: 1, backgroundColor: 'rgba(255, 255, 255, 0.1)' }}
         />
         <Chip 
           label={isConnected ? 'Connected' : 'Disconnected'} 
           color={isConnected ? 'success' : 'error'}
           size="small" 
           sx={{ ml: 1 }}
         />
         {controllerType === 'web_gamepad' && availableGamepads.length > 0 && (
           <Chip 
             label={`${availableGamepads.length} gamepad${availableGamepads.length > 1 ? 's' : ''} detected`}
             size="small" 
             color="info"
             sx={{ ml: 1 }}
           />
         )}
       </Typography>

       {/* Gamepad Selection */}
       {controllerType === 'web_gamepad' && availableGamepads.length > 1 && (
         <Box sx={{ mb: 2 }}>
           <FormControl fullWidth size="small">
             <InputLabel sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>Select Gamepad</InputLabel>
             <Select
               value={selectedGamepadIndex}
               onChange={(e) => setSelectedGamepadIndex(e.target.value)}
               sx={{
                 color: 'white',
                 '& .MuiOutlinedInput-notchedOutline': {
                   borderColor: 'rgba(255, 255, 255, 0.3)',
                 },
                 '&:hover .MuiOutlinedInput-notchedOutline': {
                   borderColor: 'rgba(255, 255, 255, 0.5)',
                 },
                 '& .MuiSvgIcon-root': {
                   color: 'rgba(255, 255, 255, 0.7)',
                 }
               }}
             >
               {availableGamepads.map((gamepad) => (
                 <MenuItem key={gamepad.index} value={gamepad.index}>
                   {gamepad.id} (Index: {gamepad.index})
                 </MenuItem>
               ))}
             </Select>
           </FormControl>
         </Box>
       )}

      <Grid container spacing={2}>
        {/* Primary Controls */}
        <Grid item xs={12} md={6}>
          <Typography variant="subtitle2" sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: 1 }}>
            Primary Controls
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Chip 
              label={getControlLabel('throttle', currentControl.throttle)}
              color={getControlColor(currentControl.throttle)}
              size="small"
            />
            <Chip 
              label={getControlLabel('brake', currentControl.brake)}
              color={getControlColor(currentControl.brake)}
              size="small"
            />
            <Chip 
              label={getControlLabel('steer', currentControl.steer)}
              color={getControlColor(currentControl.steer)}
              size="small"
            />
          </Box>
        </Grid>

        {/* Secondary Controls */}
        <Grid item xs={12} md={6}>
          <Typography variant="subtitle2" sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: 1 }}>
            Secondary Controls
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Chip 
              label={getControlLabel('hand_brake', currentControl.hand_brake)}
              color={getControlColor(currentControl.hand_brake, true)}
              size="small"
            />
            <Chip 
              label={getControlLabel('reverse', currentControl.reverse)}
              color={getControlColor(currentControl.reverse, true)}
              size="small"
            />
            <Chip 
              label={getControlLabel('manual_gear_shift', currentControl.manual_gear_shift)}
              color={getControlColor(currentControl.manual_gear_shift, true)}
              size="small"
            />
            {currentControl.manual_gear_shift && (
              <Chip 
                label={getControlLabel('gear', currentControl.gear)}
                color="secondary"
                size="small"
              />
            )}
          </Box>
        </Grid>

        {/* Instructions */}
        <Grid item xs={12}>
          <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)' }}>
            {controllerType === 'web_keyboard' ? (
              <>
                <strong>Keyboard Controls:</strong> WASD/Arrow Keys to drive, Space to brake, Q for hand brake, 
                R for reverse, M for manual mode, 1-6 for gears, Escape to quit
              </>
            ) : (
              <>
                <strong>Gamepad Controls:</strong> Left stick to steer, Right trigger for throttle, 
                Left trigger for brake, B for hand brake, X for reverse, Start to quit
              </>
            )}
          </Typography>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default WebControlPanel;
