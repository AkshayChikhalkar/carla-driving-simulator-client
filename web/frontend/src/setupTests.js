// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { act } from '@testing-library/react-hooks';
import { setupMockStorage, clearMockStorage } from './__mocks__/sessionStorage';

// Polyfill setImmediate for tests
global.setImmediate = (callback) => setTimeout(callback, 0);
global.clearImmediate = (id) => clearTimeout(id);

// Automatically cleanup after each test
beforeEach(() => {
  setupMockStorage({
    access_token: 'test-token',
    tenant_id: '1',
    user: JSON.stringify({ username: 'testuser', tenant_id: '1', isAdmin: false })
  });
});

afterEach(() => {
  cleanup();
  clearMockStorage();
});

// Increase the default timeout for async operations
jest.setTimeout(30000);

// Mock createRoot for React 18
const originalError = console.error;
const originalInfo = console.info;
const originalLog = console.log;

console.error = (...args) => {
  if (args[0]?.includes('ReactDOM.render is no longer supported') ||
      args[0]?.includes('unmountComponentAtNode is deprecated') ||
      args[0]?.includes('ReactDOMTestUtils.act is deprecated') ||
      args[0]?.includes('WebSocket error')) {
    return;
  }
  originalError.call(console, ...args);
};

console.info = (...args) => {
  // Suppress excessive logging during tests
  if (args[0]?.includes('WebSocket connection') || 
      args[0]?.includes('Simulation state change')) {
    return;
  }
  originalInfo.call(console, ...args);
};

console.log = (...args) => {
  // Suppress excessive logging during tests
  if (args[0]?.includes('WebSocket') || 
      args[0]?.includes('Simulation')) {
    return;
  }
  originalLog.call(console, ...args);
};

// Mock createRoot
const originalCreateRoot = global.document.createElement.bind(global.document);
global.document.createElement = (type, ...args) => {
  const element = originalCreateRoot(type, ...args);
  if (type === 'div') {
    element.createRoot = () => ({
      render: (component) => {
        element.innerHTML = '';
        element.appendChild(component);
      },
      unmount: () => {
        element.innerHTML = '';
      }
    });
  }
  return element;
};

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock IntersectionObserver
class MockIntersectionObserver {
  constructor() {
    this.observe = jest.fn();
    this.unobserve = jest.fn();
    this.disconnect = jest.fn();
  }
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: MockIntersectionObserver
});

// Mock ResizeObserver
class MockResizeObserver {
  constructor() {
    this.observe = jest.fn();
    this.unobserve = jest.fn();
    this.disconnect = jest.fn();
  }
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: MockResizeObserver
});
