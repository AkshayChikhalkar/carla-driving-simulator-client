import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../../__mocks__/AuthContext';
import Dashboard from '../Dashboard';

// Mock the real AuthContext to use our mock
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { username: 'testuser', tenant_id: '1' },
    isAdmin: false,
    login: jest.fn(),
    logout: jest.fn(),
    register: jest.fn(),
    loading: false
  })
}));

describe.skip('Dashboard Component', () => {
  const renderDashboard = () => {
    return render(
      <BrowserRouter>
        <AuthProvider>
          <Dashboard />
        </AuthProvider>
      </BrowserRouter>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders dashboard component', () => {
    renderDashboard();
    // Just check that the component renders without crashing
    expect(screen.getByText(/CARLA Simulator/i)).toBeInTheDocument();
  });

  test('displays main interface elements', () => {
    renderDashboard();
    // Look for any key text that should be present
    const element = document.querySelector('.dashboard') || 
                   document.querySelector('[data-testid="dashboard"]') ||
                   screen.getByText(/CARLA Simulator/i);
    expect(element).toBeInTheDocument();
  });
});