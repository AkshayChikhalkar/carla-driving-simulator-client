import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Settings from '../Settings';

// Mock fetch for API calls
global.fetch = jest.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve({
      target: { distance: 100 },
      vehicle: { model: 'test_model' },
      simulation: { fps: 30 }
    })
  })
);

describe('Settings Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders settings form with initial values', async () => {
    render(<Settings />);
    
    // Check if form elements are rendered
    expect(screen.getByLabelText(/Target Distance/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Vehicle Model/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/FPS/i)).toBeInTheDocument();
  });

  test('loads configuration on mount', async () => {
    render(<Settings />);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/config');
    });
  });

  test('updates configuration when form is submitted', async () => {
    render(<Settings />);
    
    // Fill in form fields
    const distanceInput = screen.getByLabelText(/Target Distance/i);
    const modelInput = screen.getByLabelText(/Vehicle Model/i);
    const fpsInput = screen.getByLabelText(/FPS/i);
    
    fireEvent.change(distanceInput, { target: { value: '200' } });
    fireEvent.change(modelInput, { target: { value: 'new_model' } });
    fireEvent.change(fpsInput, { target: { value: '60' } });
    
    // Submit form
    const submitButton = screen.getByText(/Save Settings/i);
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          config_data: {
            target: { distance: 200 },
            vehicle: { model: 'new_model' },
            simulation: { fps: 60 }
          }
        })
      });
    });
  });

  test('shows success message after successful save', async () => {
    render(<Settings />);
    
    // Mock successful save
    global.fetch.mockImplementationOnce(() =>
      Promise.resolve({
        json: () => Promise.resolve({ message: 'Configuration updated successfully' })
      })
    );
    
    const submitButton = screen.getByText(/Save Settings/i);
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/Settings saved successfully/i)).toBeInTheDocument();
    });
  });

  test('shows error message when save fails', async () => {
    render(<Settings />);
    
    // Mock failed save
    global.fetch.mockImplementationOnce(() =>
      Promise.reject(new Error('Failed to save'))
    );
    
    const submitButton = screen.getByText(/Save Settings/i);
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/Failed to save settings/i)).toBeInTheDocument();
    });
  });
}); 
