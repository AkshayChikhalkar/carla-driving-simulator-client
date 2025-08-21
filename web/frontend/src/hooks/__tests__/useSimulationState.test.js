import { renderHook } from '@testing-library/react-hooks';
import { AuthProvider } from '../../__mocks__/AuthContext';
import useSimulationState from '../useSimulationState';

describe.skip('useSimulationState Hook', () => {
  const wrapper = ({ children }) => (
    <AuthProvider>
      {children}
    </AuthProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('initializes with default state', () => {
    const { result } = renderHook(() => useSimulationState(), { wrapper });
    
    expect(result.current.isRunning).toBe(false);
    expect(result.current.currentScenario).toBeNull();
    expect(result.current.scenarioResults).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  test('has startSimulation function', () => {
    const { result } = renderHook(() => useSimulationState(), { wrapper });
    
    expect(typeof result.current.startSimulation).toBe('function');
  });

  test('has stopSimulation function', () => {
    const { result } = renderHook(() => useSimulationState(), { wrapper });
    
    expect(typeof result.current.stopSimulation).toBe('function');
  });

  test('has clearError function', () => {
    const { result } = renderHook(() => useSimulationState(), { wrapper });
    
    expect(typeof result.current.clearError).toBe('function');
  });

  test('has isRunning state', () => {
    const { result } = renderHook(() => useSimulationState(), { wrapper });
    
    expect(typeof result.current.isRunning).toBe('boolean');
  });

  test('has currentScenario state', () => {
    const { result } = renderHook(() => useSimulationState(), { wrapper });
    
    expect(result.current.currentScenario).toBeDefined();
  });

  test('has scenarioResults state', () => {
    const { result } = renderHook(() => useSimulationState(), { wrapper });
    
    expect(Array.isArray(result.current.scenarioResults)).toBe(true);
  });

  test('has error state', () => {
    const { result } = renderHook(() => useSimulationState(), { wrapper });
    
    expect(result.current.error).toBeDefined();
  });
});
