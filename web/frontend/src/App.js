import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Dashboard from './components/Dashboard';
import Settings from './components/Settings';
import Layout from './components/Layout';
import logger from './utils/logger';
import Reports from './components/Reports';
import Logs from './components/Logs';
import Analytics from './components/Analytics';

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

function App() {
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
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/reports/:filename" element={<Reports />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/logs/:filename" element={<Logs />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </Layout>
      </Router>
      <img
        src={process.env.PUBLIC_URL + '/th-owl-logo.png'}
        alt="TH OWL Logo"
        style={{
          position: 'fixed',
          top: 12,
          left: 12,
          height: 56,
          zIndex: 1000,
          background: 'rgba(0,0,0,0.7)',
          borderRadius: 8,
          padding: 4,
          boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
        }}
      />
    </ThemeProvider>
  );
}

export default App; 