module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.js'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(gif|ttf|eot|svg|png)$': '<rootDir>/__mocks__/fileMock.js',
    '^axios$': '<rootDir>/src/__mocks__/axios.js',
    '^../../contexts/AuthContext$': '<rootDir>/src/__mocks__/AuthContext.js',
    '^../contexts/AuthContext$': '<rootDir>/src/__mocks__/AuthContext.js',
    '^./contexts/AuthContext$': '<rootDir>/src/__mocks__/AuthContext.js',
    '^../utils/logger$': '<rootDir>/src/__mocks__/logger.js',
    '^../../contexts/AuthContext$': '<rootDir>/src/__mocks__/AuthContext.js',
    '^../contexts/AuthContext$': '<rootDir>/src/__mocks__/AuthContext.js'
  },
  testTimeout: 30000,
  globals: {
    'ts-jest': {
      isolatedModules: true
    }
  },

  transformIgnorePatterns: [
    'node_modules/(?!(@testing-library|react|react-dom|react-router|react-router-dom)/)'
  ],
  testEnvironmentOptions: {
    url: 'http://localhost'
  },
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.{js,jsx,ts,tsx}',
    '<rootDir>/src/**/*.{spec,test}.{js,jsx,ts,tsx}'
  ],
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': 'babel-jest'
  },
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/__tests__/',
    '/dist/'
  ],
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts'
  ]
};
