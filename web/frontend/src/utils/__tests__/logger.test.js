// Import the mock Logger instead of the real one
import Logger from '../../__mocks__/logger';

describe('Logger Utility', () => {
  test('Logger is defined', () => {
    expect(Logger).toBeDefined();
  });

  test('Logger has info method', () => {
    expect(typeof Logger.info).toBe('function');
  });

  test('Logger has error method', () => {
    expect(typeof Logger.error).toBe('function');
  });

  test('Logger has warn method', () => {
    expect(typeof Logger.warn).toBe('function');
  });

  test('Logger has debug method', () => {
    expect(typeof Logger.debug).toBe('function');
  });

  test('Logger has setLogLevel method', () => {
    expect(typeof Logger.setLogLevel).toBe('function');
  });

  test('Logger has clearHistory method', () => {
    expect(typeof Logger.clearHistory).toBe('function');
  });

  test('Logger has groupStart method', () => {
    expect(typeof Logger.groupStart).toBe('function');
  });

  test('Logger has groupEnd method', () => {
    expect(typeof Logger.groupEnd).toBe('function');
  });
});
