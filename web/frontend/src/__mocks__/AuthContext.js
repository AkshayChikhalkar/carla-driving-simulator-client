import React, { createContext, useContext, useState } from 'react';

const AuthContext = createContext();
AuthContext.displayName = 'AuthContext';

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user] = useState({ username: 'testuser', tenant_id: '1', isAdmin: false });
  const [loading] = useState(false);

  const login = jest.fn();
  const logout = jest.fn();
  const register = jest.fn();

  const value = {
    user,
    isAdmin: !!(user && (user.is_admin || user.isAdmin)),
    login,
    logout,
    register,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export { AuthContext };
