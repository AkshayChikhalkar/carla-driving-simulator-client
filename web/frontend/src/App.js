import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Dashboard from './components/Dashboard';
import Settings from './components/Settings';
import Layout from './components/Layout';

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
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/settings" element={<Settings />} />
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