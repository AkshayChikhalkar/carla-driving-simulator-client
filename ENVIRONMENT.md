# Environment Configuration

This project uses a **hybrid approach** for environment variables that provides flexibility while maintaining simplicity.

## 🎯 **Strategy Overview**

### **Sensible Defaults in Dockerfile**
- ✅ **Built-in defaults** - Works out of the box
- ✅ **CI/CD friendly** - No external file dependencies
- ✅ **Consistent behavior** - Same defaults across environments

### **Optional .env Files**
- ✅ **Environment-specific** - Different values for dev/staging/prod
- ✅ **Easy customization** - No rebuild needed
- ✅ **Truly optional** - Works without .env file
- ✅ **Standard practice** - Widely used in development

## 📋 **Environment Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://carla_user:carla_password@localhost:5432/carla_simulator` | Database connection string |
| `CARLA_HOST` | `localhost` | CARLA server hostname |
| `CARLA_PORT` | `2000` | CARLA server port |
| `WEB_HOST` | `0.0.0.0` | Web server host |
| `WEB_PORT` | `8000` | Backend API port |
| `FRONTEND_PORT` | `3000` | Frontend port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DEBUG` | `false` (prod) / `true` (dev) | Debug mode |
| `TESTING` | `false` | Testing mode |

## 🚀 **Usage Options**

### **Option 1: Use Defaults (Simplest)**
```bash
# Just run with defaults - no .env file needed!
docker run -p 3000:3000 -p 8000:8000 akshaychikhalkar/carla-driving-simulator-client:latest

# Or with docker-compose
docker-compose up
```

### **Option 2: Override with .env File**
```bash
# Create .env file (optional)
cat > .env << EOF
DATABASE_URL=postgresql://user:pass@db:5432/carla
CARLA_HOST=carla-server
DEBUG=true
EOF

# Run with docker-compose
docker-compose up
```

### **Option 3: Override at Runtime**
```bash
# Override specific variables
docker run -p 3000:3000 -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/carla" \
  -e CARLA_HOST="carla-server" \
  -e DEBUG=true \
  akshaychikhalkar/carla-driving-simulator-client:latest
```

## 🔧 **Development Setup**

### **Local Development**
```bash
# Clone and setup
git clone https://github.com/AkshayChikhalkar/carla-driving-simulator-client.git
cd carla-driving-simulator-client

# Option 1: Use defaults (no .env needed)
docker-compose up

# Option 2: Create .env for customization (optional)
cp .env.example .env
# Edit .env with your settings
docker-compose up
```

### **Production Deployment**
```bash
# Use production image with defaults
docker pull akshaychikhalkar/carla-driving-simulator-client:latest
docker run -d -p 3000:3000 -p 8000:8000 \
  -e DATABASE_URL="your-production-db-url" \
  -e CARLA_HOST="your-carla-server" \
  akshaychikhalkar/carla-driving-simulator-client:latest
```

## 🛡️ **Security Best Practices**

### **Sensitive Data**
- ❌ **Never commit** `.env` files with secrets
- ✅ **Use environment variables** for production secrets
- ✅ **Use Docker secrets** for sensitive data in production

### **Example .env (Development)**
```bash
# Development environment
DATABASE_URL=postgresql://dev_user:dev_pass@localhost:5432/carla_dev
CARLA_HOST=localhost
DEBUG=true
LOG_LEVEL=DEBUG
```

### **Example .env (Production)**
```bash
# Production environment
DATABASE_URL=postgresql://prod_user:${DB_PASSWORD}@prod-db:5432/carla_prod
CARLA_HOST=carla-prod-server
DEBUG=false
LOG_LEVEL=WARNING
```

## 🔍 **Priority Order**

Environment variables are resolved in this order:

1. **Runtime environment variables** (highest priority)
2. **.env file** (if exists and variables are set)
3. **Dockerfile defaults** (lowest priority)

## 📝 **Examples**

### **Development with Custom Database**
```bash
# .env file (optional)
DATABASE_URL=postgresql://dev:password@localhost:5432/carla_dev
DEBUG=true
LOG_LEVEL=DEBUG

# Run
docker-compose up
```

### **Production with External Services**
```bash
# Runtime environment
docker run -d \
  -e DATABASE_URL="postgresql://user:pass@prod-db:5432/carla" \
  -e CARLA_HOST="carla-prod.company.com" \
  -e DEBUG=false \
  -e LOG_LEVEL=WARNING \
  -p 3000:3000 -p 8000:8000 \
  akshaychikhalkar/carla-driving-simulator-client:latest
```

## ✅ **Key Benefits**

- **Zero configuration** - Works immediately with defaults
- **CI/CD friendly** - No .env file dependencies
- **Flexible** - Can override any variable when needed
- **Secure** - Sensitive data handled properly
- **Standard** - Follows Docker best practices

This approach gives you the best of both worlds: **simplicity for quick starts** and **flexibility for customization**! 🎉 