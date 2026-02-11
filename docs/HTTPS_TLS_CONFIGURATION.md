# HTTPS/TLS Configuration Guide

## Overview

This document provides guidance on configuring HTTPS/TLS for the NASCAR DFS Axiomatic Engine services to ensure secure communication in production environments.

## Security Requirements

**CRITICAL**: All services must communicate over HTTPS in production. HTTP should only be used for local development.

## Service Configuration

### 1. Neo4j Database

#### Enable TLS in Neo4j

Update the Neo4j environment variables in `docker-compose.yml`:

```yaml
neo4j:
  environment:
    NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    NEO4J_TLS_LEVEL: REQUIRED  # Enforce TLS
    NEO4J_SERVER_CERTIFICATE: /certs/neo4j.crt
    NEO4J_SERVER_PRIVATE_KEY: /certs/neo4j.key
    NEO4J_TRUSTED_DIR: /certs
  volumes:
    - ./certs:/certs
```

#### Generate Self-Signed Certificates (Development Only)

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/neo4j.key -out certs/neo4j.crt -days 365 -nodes
```

#### Production Certificates

For production, use certificates from a trusted Certificate Authority (CA):
1. Purchase SSL certificate from CA (e.g., Let's Encrypt, DigiCert)
2. Place `.crt` and `.key` files in `certs/` directory
3. Update Neo4j configuration to use production certificates

#### Update Backend Connection

Update backend environment to use Bolt with TLS:

```yaml
backend:
  environment:
    NEO4J_URI: bolt+s://neo4j:7687  # Note: bolt+s for TLS
    NEO4J_TRUST: TRUST_CUSTOM_CA_SIGNED_CERTIFICATES
    NEO4J_CA_CERTIFICATES: /certs/neo4j.crt
```

### 2. FastAPI Backend

#### Enable HTTPS with Uvicorn

Update the backend command in `docker-compose.yml`:

```yaml
backend:
  command: [
    "uvicorn", 
    "app.main:app", 
    "--host", "0.0.0.0", 
    "--port", "8000",
    "--ssl-keyfile", "/certs/backend.key",
    "--ssl-certfile", "/certs/backend.crt"
  ]
  volumes:
    - ./certs:/certs
```

#### Generate Backend Certificates

```bash
# Development (self-signed)
openssl req -x509 -newkey rsa:4096 -keyout certs/backend.key -out certs/backend.crt -days 365 -nodes \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Production (use CA-issued certificates)
# Place CA-issued backend.crt and backend.key in certs/ directory
```

#### Configure Reverse Proxy (Recommended for Production)

For production, use a reverse proxy (Nginx, Traefik, or Caddy) for TLS termination:

**Example Nginx Configuration:**

```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/backend.crt;
    ssl_certificate_key /etc/nginx/ssl/backend.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Next.js Frontend

#### Enable HTTPS in Production

Update frontend environment variables:

```yaml
frontend:
  environment:
    NEXT_PUBLIC_API_URL: https://api.yourdomain.com  # Use HTTPS
```

#### Configure Nginx for Frontend

```nginx
server {
    listen 443 ssl http2;
    server_name www.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/frontend.crt;
    ssl_certificate_key /etc/nginx/ssl/frontend.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### 4. Airflow

#### Enable HTTPS for Airflow Webserver

```yaml
airflow:
  environment:
    AIRFLOW__CORE__BASE_URL: https://airflow.yourdomain.com
    AIRFLOW__WEBSERVER__ENABLE_PROXY_FIX: "True"
```

#### Configure Airflow Behind Reverse Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name airflow.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/airflow.crt;
    ssl_certificate_key /etc/nginx/ssl/airflow.key;

    location / {
        proxy_pass http://airflow:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $http_host;
        proxy_read_timeout 120s;
    }
}
```

## Docker Compose with Full TLS Configuration

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15.0-community
    container_name: nascar-neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
      NEO4J_TLS_LEVEL: REQUIRED
      NEO4J_SERVER_CERTIFICATE: /certs/neo4j.crt
      NEO4J_SERVER_PRIVATE_KEY: /certs/neo4j.key
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - ./certs:/certs
    networks:
      - nascar-network
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "https://localhost:7474"]
      interval: 30s
      timeout: 10s
      retries: 5

  backend:
    build:
      context: ./apps/backend
      dockerfile: Dockerfile
    container_name: nascar-backend
    ports:
      - "8000:8000"
    environment:
      NEO4J_URI: bolt+s://neo4j:7687
      NEO4J_TRUST: TRUST_CUSTOM_CA_SIGNED_CERTIFICATES
      NEO4J_CA_CERTIFICATES: /certs/neo4j.crt
      NEO4J_USER: ${NEO4J_USER}
      NEO4J_PASSWORD: ${NEO4J_PASSWORD}
    volumes:
      - ./apps/backend:/app
      - ./packages:/app/packages
      - ./certs:/certs
    depends_on:
      neo4j:
        condition: service_healthy
    networks:
      - nascar-network
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "https://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 40s

  nginx:
    image: nginx:alpine
    container_name: nascar-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend
      - airflow
    networks:
      - nascar-network
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M
    healthcheck:
      test: ["CMD", "curl", "-f", "https://localhost:443/health"]
      interval: 30s
      timeout: 10s
      retries: 5

networks:
  nascar-network:
    driver: bridge

volumes:
  neo4j_data:
  neo4j_logs:
```

## SSL Certificate Best Practices

1. **Always use valid certificates from trusted CA in production**
2. **Use strong cipher suites**: TLS 1.2 or 1.3 only
3. **Set appropriate certificate expiration**: 90-365 days
4. **Use separate certificates** for each service
5. **Implement certificate rotation**: Auto-renew before expiration
6. **Use HSTS (HTTP Strict Transport Security)** in reverse proxy

## Let's Encrypt Automation

For automatic certificate management, use Certbot:

```bash
# Install Certbot
sudo apt-get install certbot

# Generate certificate for your domain
sudo certbot certonly --standalone -d api.yourdomain.com -d www.yourdomain.com

# Certificates will be placed in /etc/letsencrypt/live/yourdomain.com/
# Mount this directory in Docker volumes
```

## Verification

Test TLS configuration:

```bash
# Test Neo4j TLS
openssl s_client -connect localhost:7474 -showcerts

# Test Backend TLS
openssl s_client -connect localhost:8000 -showcerts

# Check certificate chain
curl -vI https://api.yourdomain.com
```

## Security Checklist

- [ ] All services use HTTPS in production
- [ ] Certificates are from trusted CA (not self-signed)
- [ ] TLS 1.2 or 1.3 only (no SSLv3, TLS 1.0, 1.1)
- [ ] Strong cipher suites configured
- [ ] HSTS enabled on reverse proxy
- [ ] Certificate expiration monitoring in place
- [ ] Certificate rotation automation configured
- [ ] Security headers configured (CSP, X-Frame-Options, etc.)
- [ ] Regular security audits performed

## Troubleshooting

### Certificate Errors

**Error**: `certificate verify failed`

**Solution**: Ensure CA certificate is properly mounted and referenced in configuration.

### Connection Refused

**Error**: `Connection refused on port 443`

**Solution**: Verify reverse proxy is running and port 443 is exposed.

### Mixed Content Warnings

**Error**: Browser shows mixed content warnings

**Solution**: Ensure all resources (CSS, JS, images) are loaded via HTTPS.

## References

- [Neo4j Security Configuration](https://neo4j.com/docs/operations-manual/configuration-reference/security-settings/)
- [FastAPI HTTPS](https://fastapi.tiangolo.com/deployment/https/)
- [Nginx SSL Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [Let's Encrypt](https://letsencrypt.org/)
