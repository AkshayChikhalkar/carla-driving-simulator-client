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
      fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
        .then(res => {
          if (!res.ok) throw new Error('Invalid token');
          return res.json();
        })
        .then(user => {
          setUser(user);
          // Persist tenant id from JWT (if present via backend login) or backend me response (extend later)
          if (user && user.tenant_id) {
            localStorage.setItem('tenant_id', String(user.tenant_id));
          }
          logger.info(`AuthContext: Loaded user from backend: ${user.username}`);
        })
        .catch(() => {
          localStorage.removeItem('access_token');
          localStorage.removeItem('session_token');
          localStorage.removeItem('user');
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
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
