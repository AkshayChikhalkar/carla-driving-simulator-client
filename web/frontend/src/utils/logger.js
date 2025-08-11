/**
 * Logger utility for the CARLA Driving Simulator web frontend.
 */

class Logger {
  constructor() {
    if (Logger.instance) {
      return Logger.instance;
    }
    Logger.instance = this;
    this._initialized = false;
    this._initialize();
  }

  _initialize() {
    if (this._initialized) return;

    // Default configuration
    this.config = {
      logLevel: process.env.NODE_ENV === 'development' ? 'DEBUG' : 'INFO',
      logToConsole: true,
      // Disable file logging by default to avoid noisy /api/logs/* traffic
      logToFile: false,
      logFormat: '%timestamp% - %level% - %message%',
      dateFormat: 'YYYY-MM-DD HH:mm:ss'
    };

    // Get API base URL
    this.apiBaseUrl = process.env.NODE_ENV === 'production' ? window.location.origin : '';

    // Initialize console methods
    this._setupConsoleMethods();
    this._initialized = true;

    // Initialize file logging
    if (this.config.logToFile) {
      this._initializeFileLogging();
    }
  }

  async _initializeFileLogging() {
    try {
      // Create logs directory if it doesn't exist
      const response = await fetch(`${this.apiBaseUrl}/api/logs/directory`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to create logs directory');
      }

      // Create a new file for today's logs
      const today = new Date().toISOString().split('T')[0];
      const logFileName = `web_simulation_${today}.log`;
      
      // Get the log file handle from the backend
      const fileResponse = await fetch(`${this.apiBaseUrl}/api/logs/file`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ filename: logFileName })
      });

      if (!fileResponse.ok) {
        throw new Error('Failed to create log file');
      }

      // Write header
      const header = `=== Web Simulation Log - ${today} ===\n`;
      const writeResponse = await fetch(`${this.apiBaseUrl}/api/logs/write`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content: header })
      });

      if (!writeResponse.ok) {
        throw new Error('Failed to write log header');
      }
      
      //console.log('File logging initialized successfully');
    } catch (error) {
      console.error('Failed to initialize file logging:', error);
      this.config.logToFile = false;
    }
  }

  _setupConsoleMethods() {
    // Create bound methods for each log level
    this.debug = this._createLogMethod('debug');
    this.info = this._createLogMethod('info');
    this.warn = this._createLogMethod('warn');
    this.error = this._createLogMethod('error');
  }

  _createLogMethod(level) {
    return async (message, ...args) => {
      if (!this._shouldLog(level)) return;

      const timestamp = new Date().toISOString();
      const formattedMessage = this._formatMessage(level, message, timestamp);
      
      if (this.config.logToConsole) {
        console[level](formattedMessage, ...args);
      }

      if (this.config.logToFile) {
        try {
          const logEntry = `${formattedMessage}\n`;
          const response = await fetch(`${this.apiBaseUrl}/api/logs/write`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content: logEntry })
          });

          if (!response.ok) {
            throw new Error(`Failed to write log: ${response.statusText}`);
          }
        } catch (error) {
          console.error('Failed to write to log file:', error);
          this.config.logToFile = false;
        }
      }
    };
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

  setLevel(level) {
    const validLevels = ['debug', 'info', 'warn', 'error'];
    if (!validLevels.includes(level.toLowerCase())) {
      this.error(`Invalid log level: ${level}. Must be one of: ${validLevels.join(', ')}`);
      return;
    }
    this.config.logLevel = level.toUpperCase();
    this.info(`Log level set to ${level.toUpperCase()}`);
  }

  // Specialized logging methods
  logVehicleState(state) {
    if (this._shouldLog('debug')) {
      this.debug('Vehicle State:', state);
    }
  }

  logSimulationEvent(event, details) {
    this.info(`[${event}] ${details}`);
  }

  async close() {
    if (this.config.logToFile) {
      try {
        await fetch(`${this.apiBaseUrl}/api/logs/close`, { method: 'POST' });
        //('Log file closed successfully');
      } catch (error) {
        console.error('Error closing log file:', error);
      }
    }
  }
}

// Create and export a singleton instance
const logger = new Logger();
export default logger; 
