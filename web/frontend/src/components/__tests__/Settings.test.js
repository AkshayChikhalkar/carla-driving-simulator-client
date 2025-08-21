import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../../__mocks__/AuthContext';
import Settings from '../Settings';

// Mock fetchJson to return a simple response
jest.mock('../../utils/fetchJson', () => ({
  fetchJson: jest.fn(() => Promise.resolve({ config: {} }))
}));

// Mock fetch for API calls
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ config: {} })
  })
);

describe('Settings Component', () => {
  const renderSettings = () => {
    return render(
      <BrowserRouter>
        <AuthProvider>
          <Settings />
        </AuthProvider>
      </BrowserRouter>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders settings component', () => {
    renderSettings();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  test('displays application tab', () => {
    renderSettings();
    expect(screen.getByText('Application')).toBeInTheDocument();
  });

  test('displays simulation tab', () => {
    renderSettings();
    expect(screen.getByText('Simulation')).toBeInTheDocument();
  });

  test('displays server section', () => {
    renderSettings();
    expect(screen.getAllByText('Server')[0]).toBeInTheDocument();
  });

  test('displays display section', () => {
    renderSettings();
    expect(screen.getAllByText('Display')[0]).toBeInTheDocument();
  });

  test('displays save settings button', () => {
    renderSettings();
    expect(screen.getByText('Save Settings')).toBeInTheDocument();
  });

  test('displays reset button', () => {
    renderSettings();
    expect(screen.getByText('Reset')).toBeInTheDocument();
  });
});