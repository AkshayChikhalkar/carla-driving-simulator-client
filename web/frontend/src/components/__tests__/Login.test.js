import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../../__mocks__/AuthContext';
import Login from '../Login';

describe('Login Component', () => {
  const renderLogin = () => {
    return render(
      <BrowserRouter>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </BrowserRouter>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders login component', () => {
    renderLogin();
    expect(screen.getByText('CARLA Simulator')).toBeInTheDocument();
  });

  test('displays username field', () => {
    renderLogin();
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
  });

  test('displays password field', () => {
    renderLogin();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  test('displays login button', () => {
    renderLogin();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  test('displays register link', () => {
    renderLogin();
    expect(screen.getByText('Don\'t have an account? Sign Up')).toBeInTheDocument();
  });

  test('displays forgot password link', () => {
    renderLogin();
    expect(screen.getByText('Forgot password?')).toBeInTheDocument();
  });
});
