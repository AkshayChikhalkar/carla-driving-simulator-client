import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { CircularProgress, Box } from '@mui/material';
import logger from '../utils/logger';

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        bgcolor="background.default"
      >
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    logger.info('ProtectedRoute: No user, redirecting to /login');
    return <Navigate to="/login" replace />;
  }

  logger.info(`ProtectedRoute: User authenticated: ${user.username}`);
  return children;
};

export default ProtectedRoute; 