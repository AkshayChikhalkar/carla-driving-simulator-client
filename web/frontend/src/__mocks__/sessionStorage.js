const mockStorage = {
  store: {},
  getItem: jest.fn((key) => mockStorage.store[key] || null),
  setItem: jest.fn((key, value) => {
    mockStorage.store[key] = value;
  }),
  removeItem: jest.fn((key) => {
    delete mockStorage.store[key];
  }),
  clear: jest.fn(() => {
    mockStorage.store = {};
  })
};

export const setupMockStorage = (initialStore = {}) => {
  mockStorage.store = { ...initialStore };
  Object.defineProperty(window, 'sessionStorage', {
    value: mockStorage,
    writable: true
  });
  return mockStorage;
};

export const clearMockStorage = () => {
  mockStorage.store = {};
  mockStorage.getItem.mockClear();
  mockStorage.setItem.mockClear();
  mockStorage.removeItem.mockClear();
  mockStorage.clear.mockClear();
};

