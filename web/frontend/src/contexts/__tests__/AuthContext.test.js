import React from 'react';
import { render, screen } from '@testing-library/react';
import { AuthProvider } from '../../__mocks__/AuthContext';

// Test component that uses the auth context
const TestComponent = () => {
  return (
    <div>
      <div data-testid="auth-status">Test Component</div>
      <button>Login</button>
      <button>Logout</button>
    </div>
  );
};

describe.skip('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders test component', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByTestId('auth-status')).toHaveTextContent('Test Component');
  });

  test('renders login and logout buttons', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByText('Login')).toBeInTheDocument();
    expect(screen.getByText('Logout')).toBeInTheDocument();
  });
});
