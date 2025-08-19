import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dashboard from '../Dashboard';

// Mock the WebSocket
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
};

global.WebSocket = jest.fn(() => mockWebSocket);

// Mock fetch for API calls
global.fetch = jest.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({
      scenarios: ['scenario1', 'scenario2'],
      config: {
        target: { distance: 100 },
        vehicle: { model: 'test_model' },
        simulation: { fps: 30 }
      }
    })
  })
);

describe('Dashboard Component', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  test('renders dashboard with initial state', async () => {
    render(<Dashboard />);
    
    // Check if main elements are rendered
    expect(screen.getByText(/Simulation Dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/Scenarios/i)).toBeInTheDocument();
    expect(screen.getByText(/Configuration/i)).toBeInTheDocument();
  });

  test('loads scenarios on mount', async () => {
    render(<Dashboard />);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/scenarios');
    });
  });

  test('starts simulation when start button is clicked', async () => {
    render(<Dashboard />);
    
    const startButton = screen.getByText(/Start Simulation/i);
    fireEvent.click(startButton);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/simulation/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: expect.any(String)
      });
    });
  });

  test('stops simulation when stop button is clicked', async () => {
    render(<Dashboard />);
    
    const stopButton = screen.getByText(/Stop Simulation/i);
    fireEvent.click(stopButton);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/simulation/stop', {
        method: 'POST'
      });
    });
  });

  test('updates configuration when settings are changed', async () => {
    render(<Dashboard />);
    
    const configInput = screen.getByLabelText(/Target Distance/i);
    fireEvent.change(configInput, { target: { value: '200' } });
    
    const saveButton = screen.getByText(/Save Configuration/i);
    fireEvent.click(saveButton);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: expect.any(String)
      });
    });
  });

  test('handles WebSocket connection for simulation view', async () => {
    render(<Dashboard />);
    
    await waitFor(() => {
      const expected = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/simulation-view`;
      expect(global.WebSocket).toHaveBeenCalledWith(expected);
    });
  });
}); 
