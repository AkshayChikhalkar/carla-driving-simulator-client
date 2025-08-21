import { renderHook } from '@testing-library/react-hooks';
import { AuthProvider } from '../../__mocks__/AuthContext';
import { useWebSocketConnection } from '../useWebSocketConnection';

describe.skip('useWebSocketConnection Hook', () => {
  const wrapper = ({ children }) => (
    <AuthProvider>
      {children}
    </AuthProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('initializes with default state', () => {
    const mockProps = {
      setStatus: jest.fn(),
      setIsRunning: jest.fn(),
      setIsPaused: jest.fn(),
      setBackendState: jest.fn(),
      setHasReceivedFrame: jest.fn(),
      setIsStarting: jest.fn(),
      setIsStopping: jest.fn(),
      setIsSkipping: jest.fn(),
      isSkipping: false,
      backendState: { is_running: false },
      setHudData: jest.fn(),
      canvasRef: { current: document.createElement('canvas') }
    };

    const { result } = renderHook(() => useWebSocketConnection(mockProps), { wrapper });
    
    expect(result.current.wsRef).toBeDefined();
    expect(typeof result.current.sendMessage).toBe('function');
  });

  test('has wsRef property', () => {
    const mockProps = {
      setStatus: jest.fn(),
      setIsRunning: jest.fn(),
      setIsPaused: jest.fn(),
      setBackendState: jest.fn(),
      setHasReceivedFrame: jest.fn(),
      setIsStarting: jest.fn(),
      setIsStopping: jest.fn(),
      setIsSkipping: jest.fn(),
      isSkipping: false,
      backendState: { is_running: false },
      setHudData: jest.fn(),
      canvasRef: { current: document.createElement('canvas') }
    };

    const { result } = renderHook(() => useWebSocketConnection(mockProps), { wrapper });
    
    expect(result.current.wsRef).toBeDefined();
  });

  test('has sendMessage function', () => {
    const mockProps = {
      setStatus: jest.fn(),
      setIsRunning: jest.fn(),
      setIsPaused: jest.fn(),
      setBackendState: jest.fn(),
      setHasReceivedFrame: jest.fn(),
      setIsStarting: jest.fn(),
      setIsStopping: jest.fn(),
      setIsSkipping: jest.fn(),
      isSkipping: false,
      backendState: { is_running: false },
      setHudData: jest.fn(),
      canvasRef: { current: document.createElement('canvas') }
    };

    const { result } = renderHook(() => useWebSocketConnection(mockProps), { wrapper });
    
    expect(typeof result.current.sendMessage).toBe('function');
  });

  test('accepts required props', () => {
    const mockProps = {
      setStatus: jest.fn(),
      setIsRunning: jest.fn(),
      setIsPaused: jest.fn(),
      setBackendState: jest.fn(),
      setHasReceivedFrame: jest.fn(),
      setIsStarting: jest.fn(),
      setIsStopping: jest.fn(),
      setIsSkipping: jest.fn(),
      isSkipping: false,
      backendState: { is_running: false },
      setHudData: jest.fn(),
      canvasRef: { current: document.createElement('canvas') }
    };

    const { result } = renderHook(() => useWebSocketConnection(mockProps), { wrapper });
    
    expect(result.current).toBeDefined();
  });
});
