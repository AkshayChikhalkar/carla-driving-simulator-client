import React, { createContext, useContext, useState, useEffect } from 'react';
import logger from '../utils/logger';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in on app start
    const token = localStorage.getItem('access_token');
    const userData = localStorage.getItem('user');
    
    if (token && userData) {
      try {
        const user = JSON.parse(userData);
        setUser(user);
        logger.info(`AuthContext: Loaded user from localStorage: ${user.username}`);
      } catch (error) {
        logger.error('AuthContext: Error parsing user data:', error);
        localStorage.removeItem('access_token');
        localStorage.removeItem('session_token');
        localStorage.removeItem('user');
      }
    } else {
      logger.info('AuthContext: No user found in localStorage');
    }
    setLoading(false);
  }, []);

  const login = (userData) => {
    setUser(userData);
    logger.info(`AuthContext: User logged in: ${userData.username}`);
  };

  const logout = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (token) {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });
      }
      logger.info('AuthContext: User logged out');
    } catch (error) {
      logger.error('AuthContext: Logout error:', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('session_token');
      localStorage.removeItem('user');
      setUser(null);
    }
  };

  const register = (userData) => {
    logger.info(`AuthContext: User registered: ${userData.username}`);
    // Registration doesn't automatically log in the user
    // They need to login separately
  };

  const value = {
    user,
    login,
    logout,
    register,
    loading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}; 