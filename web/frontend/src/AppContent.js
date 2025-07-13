import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box } from '@mui/material';
import Dashboard from './components/Dashboard';
import Settings from './components/Settings';
import Layout from './components/Layout';
import Login from './components/Login';
import Register from './components/Register';
import ProtectedRoute from './components/ProtectedRoute';
import { useAuth } from './contexts/AuthContext';
import logger from './utils/logger';
import Reports from './components/Reports';
import Logs from './components/Logs';
import Analytics from './components/Analytics';
import Imprint from './components/Imprint';
import ForgotPassword from './components/ForgotPassword';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9',
    },
    secondary: {
      main: '#f48fb1',
    },
  },
});

function AppContent() {
  const { user, login, register } = useAuth();
  const location = useLocation();
  const [version, setVersion] = useState('');

  useEffect(() => {
    fetch('/api/version')
      .then(res => res.json())
      .then(data => {
        let safeVersion = 'dev';
        if (data && typeof data === 'object' && data.version) {
          safeVersion = typeof data.version === 'string' ? data.version : String(data.version);
        } else if (typeof data === 'string') {
          safeVersion = data;
        } else if (data) {
          safeVersion = String(data);
        }
        setVersion(safeVersion);
      })
      .catch(() => setVersion('dev'));
  }, []);

  // Log app start
  useEffect(() => {
    logger.info('Frontend app started');
  }, []);

  // Log route changes and user state
  useEffect(() => {
    logger.info(`Route changed: ${location.pathname}, user: ${user ? user.username : 'none'}`);
  }, [location, user]);

  useEffect(() => {
    // Initialize file logging when the app starts
    const initializeLogging = async () => {
      try {
        await logger._initializeFileLogging();
        logger.info('Application started');
      } catch (error) {
        console.error('Failed to initialize file logging:', error);
      }
    };

    initializeLogging();

    // Cleanup when the app unmounts
    return () => {
      logger.close();
    };
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Routes>
        <Route path="/login" element={<Login onLogin={login} />} />
        <Route path="/register" element={<Register onRegister={register} />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/imprint" element={<Imprint />} />
        <Route path="/" element={<ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><Layout><Settings /></Layout></ProtectedRoute>} />
        <Route path="/reports" element={<ProtectedRoute><Layout><Reports /></Layout></ProtectedRoute>} />
        <Route path="/reports/:filename" element={<ProtectedRoute><Layout><Reports /></Layout></ProtectedRoute>} />
        <Route path="/logs" element={<ProtectedRoute><Layout><Logs /></Layout></ProtectedRoute>} />
        <Route path="/logs/:filename" element={<ProtectedRoute><Layout><Logs /></Layout></ProtectedRoute>} />
        <Route path="/analytics" element={<ProtectedRoute><Layout><Analytics /></Layout></ProtectedRoute>} />
                <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
      <Box
        sx={{
          position: 'fixed',
          bottom: 8,
          left: 16,
          zIndex: 1300,
          color: 'rgba(255,255,255,0.5)',
          fontSize: 13,
          fontFamily: 'Roboto, sans-serif',
          letterSpacing: 1,
          userSelect: 'none',
        }}
      >
        {`Version: ${typeof version === 'string' ? version : String(version)}`}
      </Box>
      </ThemeProvider>
    );
}

export default AppContent; 