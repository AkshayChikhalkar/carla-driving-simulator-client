import { renderHook } from '@testing-library/react-hooks';
import { AuthProvider } from '../../__mocks__/AuthContext';
import { useScenarioSelection } from '../useScenarioSelection';

describe.skip('useScenarioSelection Hook', () => {
  const wrapper = ({ children }) => (
    <AuthProvider>
      {children}
    </AuthProvider>
  );

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock axios to return scenarios data
    const axios = require('axios');
    axios.get.mockResolvedValue({
      data: {
        scenarios: ['scenario1', 'scenario2', 'scenario3']
      }
    });
  });

    test('initializes with default state', () => {
    const { result } = renderHook(() => useScenarioSelection(), { wrapper });

    expect(Array.isArray(result.current.scenarios)).toBe(true);
    expect(Array.isArray(result.current.selectedScenarios)).toBe(true);
    expect(typeof result.current.handleScenarioChange).toBe('function');
    expect(typeof result.current.handleDropdownOpen).toBe('function');
  });

  test('has scenarios state', () => {
    const { result } = renderHook(() => useScenarioSelection(), { wrapper });
    
    expect(Array.isArray(result.current.scenarios)).toBe(true);
  });

  test('has selectedScenarios state', () => {
    const { result } = renderHook(() => useScenarioSelection(), { wrapper });
    
    expect(Array.isArray(result.current.selectedScenarios)).toBe(true);
  });

  test('has handleScenarioChange function', () => {
    const { result } = renderHook(() => useScenarioSelection(), { wrapper });
    
    expect(typeof result.current.handleScenarioChange).toBe('function');
  });

  test('has dropdownOpen state', () => {
    const { result } = renderHook(() => useScenarioSelection(), { wrapper });
    
    expect(typeof result.current.dropdownOpen).toBe('boolean');
  });
});
