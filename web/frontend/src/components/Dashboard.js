import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
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
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Pause as PauseIcon,
} from '@mui/icons-material';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

function Dashboard() {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState('');
  const [debug, setDebug] = useState(false);
  const [report, setReport] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [status, setStatus] = useState('');

  useEffect(() => {
    // Fetch available scenarios
    axios.get(`${API_BASE_URL}/scenarios`)
      .then(response => {
        setScenarios(response.data.scenarios);
        if (response.data.scenarios.length > 0) {
          setSelectedScenario(response.data.scenarios[0]);
        }
      })
      .catch(error => {
        console.error('Error fetching scenarios:', error);
        setStatus('Error loading scenarios');
      });
  }, []);

  const handleStart = async () => {
    try {
      setIsRunning(true);
      setStatus('Starting simulation...');
      
      const response = await axios.post(`${API_BASE_URL}/simulation/start`, {
        scenario: selectedScenario,
        debug,
        report,
      });

      setStatus(response.data.message);
    } catch (error) {
      console.error('Error starting simulation:', error);
      setStatus('Error starting simulation');
    } finally {
      setIsRunning(false);
    }
  };

  const handleStop = () => {
    setIsRunning(false);
    setIsPaused(false);
    setStatus('Simulation stopped');
  };

  const handlePause = () => {
    setIsPaused(!isPaused);
    setStatus(isPaused ? 'Simulation resumed' : 'Simulation paused');
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h5" gutterBottom>
              Simulation Control
            </Typography>
            
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} md={4}>
                <FormControl fullWidth>
                  <InputLabel>Scenario</InputLabel>
                  <Select
                    value={selectedScenario}
                    label="Scenario"
                    onChange={(e) => setSelectedScenario(e.target.value)}
                    disabled={isRunning}
                  >
                    {scenarios.map((scenario) => (
                      <MenuItem key={scenario} value={scenario}>
                        {scenario}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid item xs={12} md={4}>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={debug}
                      onChange={(e) => setDebug(e.target.checked)}
                      disabled={isRunning}
                    />
                  }
                  label="Debug Mode"
                />
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={report}
                      onChange={(e) => setReport(e.target.checked)}
                      disabled={isRunning}
                    />
                  }
                  label="Generate Report"
                />
              </Grid>

              <Grid item xs={12} md={4}>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    variant="contained"
                    color="primary"
                    startIcon={<PlayIcon />}
                    onClick={handleStart}
                    disabled={isRunning || !selectedScenario}
                  >
                    Start
                  </Button>
                  <Button
                    variant="contained"
                    color="secondary"
                    startIcon={<PauseIcon />}
                    onClick={handlePause}
                    disabled={!isRunning}
                  >
                    {isPaused ? 'Resume' : 'Pause'}
                  </Button>
                  <Button
                    variant="contained"
                    color="error"
                    startIcon={<StopIcon />}
                    onClick={handleStop}
                    disabled={!isRunning}
                  >
                    Stop
                  </Button>
                </Box>
              </Grid>
            </Grid>

            {status && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body1" color="text.secondary">
                  Status: {status}
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Simulation View
              </Typography>
              <Box
                sx={{
                  width: '100%',
                  height: 400,
                  bgcolor: 'background.paper',
                  border: '1px solid',
                  borderColor: 'divider',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Typography variant="body1" color="text.secondary">
                  CARLA Simulation Window
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Dashboard; 