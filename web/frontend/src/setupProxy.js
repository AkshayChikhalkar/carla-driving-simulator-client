const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  const backendHost = process.env.BACKEND_HOST || 'localhost';
  const backendPort = process.env.BACKEND_PORT || '8000';
  const httpTarget = `http://${backendHost}:${backendPort}`;
  const wsTarget = `ws://${backendHost}:${backendPort}`;

  // Proxy all API calls to the backend
  app.use(
    '/api', 
    createProxyMiddleware({
      target: httpTarget,
      changeOrigin: true,
      logLevel: 'debug',
    })
  );
  
  // Proxy WebSocket connections
  app.use(
    '/ws',
    createProxyMiddleware({
      target: wsTarget,
      ws: true,
      changeOrigin: true,
      logLevel: 'debug',
    })
  );
}; 
