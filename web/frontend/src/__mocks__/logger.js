class MockLogger {
  constructor() {
    this.config = {
      logLevel: 'INFO',
      logToConsole: true,
      logToFile: false,
      logFormat: '%timestamp% - %level% - %message%',
      dateFormat: 'YYYY-MM-DD HH:mm:ss'
    };

    this.debug = jest.fn();
    this.info = jest.fn();
    this.warn = jest.fn();
    this.error = jest.fn();
    this.setLevel = jest.fn();
    this.setLogLevel = jest.fn();
    this.clearHistory = jest.fn();
    this.groupStart = jest.fn();
    this.groupEnd = jest.fn();
    this.logVehicleState = jest.fn();
    this.logSimulationEvent = jest.fn();
    this.close = jest.fn();
  }

  _shouldLog(level) {
    const levels = {
      'debug': 0,
      'info': 1,
      'warn': 2,
      'error': 3
    };
    return levels[level] >= levels[this.config.logLevel.toLowerCase()];
  }

  _formatMessage(level, message, timestamp) {
    return this.config.logFormat
      .replace('%timestamp%', timestamp)
      .replace('%level%', level.toUpperCase())
      .replace('%message%', message);
  }
}

const mockLogger = new MockLogger();
export default mockLogger;