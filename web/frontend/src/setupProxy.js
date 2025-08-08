const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Dev proxy: keep simple defaults; frontend will talk to same-origin in prod
  const backendHost = 'localhost';
  const backendPort = '8000';
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
