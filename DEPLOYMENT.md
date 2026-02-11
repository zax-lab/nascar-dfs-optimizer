# Deployment Guide

This guide covers deployment strategies for the Axiomatic NASCAR DFS Engine, including Docker deployment, environment configuration, and CI/CD pipeline setup.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [Monitoring and Logging](#monitoring-and-logging)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Disk Space**: Minimum 20GB free space
- **Operating System**: Linux, macOS, or Windows with WSL2

### External Dependencies

- **Neo4j**: 5.15+ Community Edition
- **NASCAR API**: Access to NASCAR data API
- **TinyLlama Model**: Model checkpoint files for ML predictions

## Environment Variables

### Required Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env
```

### Variable Reference

| Variable | Description | Required | Default | Notes |
|----------|-------------|----------|---------|-------|
| `NEO4J_URI` | Neo4j connection URI | Yes | `bolt://neo4j:7687` | Use `bolt://localhost:7687` for local |
| `NEO4J_USER` | Neo4j username | Yes | `neo4j` | Default admin user |
| `NEO4J_PASSWORD` | Neo4j password | Yes | `nascar_password` | Change in production |
| `NASCAR_API_URL` | NASCAR API endpoint | Yes | `https://api.nascar.com` | Official NASCAR API |
| `TINYLLAMA_CHECKPOINT` | Model checkpoint path | No | `/models/tinyllama` | For ML predictions |
| `API_URL` | Backend API URL | Yes | `http://localhost:8000` | Frontend uses this |
| `NEXT_PUBLIC_API_URL` | Public API URL | Yes | `http://localhost:8000` | Exposed to client |
| `NEXT_PUBLIC_API_KEY` | Frontend API key | Yes | `dev-key-12345` | Must match `API_KEYS` |
| `API_KEYS` | Comma-separated API keys | Yes | `dev-key-12345` | Required for non-health endpoints |
| `API_KEY_HEADER` | API key header name | No | `X-API-Key` | Header for auth |
| `RATE_LIMIT_DEFAULT` | Default rate limit | No | `100/hour` | Applies to all non-health endpoints |
| `RATE_LIMIT_OPTIMIZE` | Optimize rate limit | No | `10/hour` | Optimize endpoints |
| `RATE_LIMIT_OWNERSHIP` | Ownership rate limit | No | `30/hour` | Ownership endpoints |
| `RATE_LIMIT_CONTEST` | Contest rate limit | No | `20/hour` | Contest simulation |
| `RATE_LIMIT_LEVERAGE` | Leverage rate limit | No | `10/hour` | Leverage optimization |
| `RATE_LIMIT_STORAGE_URL` | Rate limit storage | No | `redis://redis:6379/1` | Redis backend for limits |
| `CORS_ALLOW_ORIGINS` | CORS allowlist | No | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated |

**Note:** All non-health endpoints (including `/docs` and `/openapi.json`) require `X-API-Key`.

### Production Environment Variables

For production deployment, use stronger security:

```bash
# Neo4j
NEO4J_URI=bolt://neo4j-prod:7687
NEO4J_USER=nascar_admin
NEO4J_PASSWORD=<strong-random-password>

# NASCAR API
NASCAR_API_URL=https://api.nascar.com/v2

# Model
TINYLLAMA_CHECKPOINT=/models/tinyllama-prod

# API
API_URL=https://api.yourdomain.com
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_API_KEY=<strong-random-api-key>

# API Auth + Rate Limits
API_KEYS=<strong-random-api-key>
API_KEY_HEADER=X-API-Key
RATE_LIMIT_DEFAULT=100/hour
RATE_LIMIT_OPTIMIZE=10/hour
RATE_LIMIT_OWNERSHIP=30/hour
RATE_LIMIT_CONTEST=20/hour
RATE_LIMIT_LEVERAGE=10/hour
RATE_LIMIT_STORAGE_URL=redis://redis:6379/1

# CORS
CORS_ALLOW_ORIGINS=https://yourdomain.com
```

### Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use strong passwords** for all services
3. **Rotate secrets regularly** (every 90 days)
4. **Use secrets management** tools (AWS Secrets Manager, HashiCorp Vault)
5. **Enable TLS/SSL** for all external connections

## Docker Deployment

### Quick Start

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Docker Compose Services

The [`docker-compose.yml`](docker-compose.yml) defines the following services:

#### 1. Neo4j Database

```yaml
neo4j:
  image: neo4j:5.15.0-community
  ports:
    - "7474:7474"  # HTTP
    - "7687:7687"  # Bolt
  environment:
    NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    NEO4J_PLUGINS: '["apoc"]'
  volumes:
    - neo4j_data:/data
    - neo4j_logs:/logs
```

**Access Points:**
- HTTP: http://localhost:7474
- Bolt: bolt://localhost:7687
- Default credentials: `neo4j` / `nascar_password`

#### 2. FastAPI Backend

```yaml
backend:
  build:
    context: ./apps/backend
    dockerfile: Dockerfile
  ports:
    - "8000:8000"
  depends_on:
    neo4j:
      condition: service_healthy
```

**Access Points:**
- API: http://localhost:8000
- Health: http://localhost:8000/health
- Docs: http://localhost:8000/docs

#### 3. Next.js Frontend

```yaml
frontend:
  build:
    context: ./apps/frontend
    dockerfile: Dockerfile
  ports:
    - "3000:3000"
  depends_on:
    - backend
```

**Access Points:**
- Web App: http://localhost:3000

#### 4. Airflow

```yaml
airflow:
  build:
    context: ./apps/airflow
    dockerfile: Dockerfile
  ports:
    - "8080:8080"
  depends_on:
    neo4j:
      condition: service_healthy
```

**Access Points:**
- Web UI: http://localhost:8080
- Default credentials: `admin` / `admin`

### Building Images

```bash
# Build all images
docker-compose build

# Build specific service
docker-compose build backend

# Build with no cache
docker-compose build --no-cache
```

### Managing Services

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers and volumes
docker-compose down -v

# Restart specific service
docker-compose restart backend

# Scale services (if needed)
docker-compose up -d --scale backend=3
```

### Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect nascar-model_neo4j_data

# Remove volume (WARNING: deletes data)
docker volume rm nascar-model_neo4j_data

# Backup Neo4j data
docker run --rm -v nascar-model_neo4j_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/neo4j-backup.tar.gz /data

# Restore Neo4j data
docker run --rm -v nascar-model_neo4j_data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/neo4j-backup.tar.gz -C /
```

## Production Deployment

### Production Architecture

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │    (Nginx)      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
    ┌─────────▼──────┐ ┌─────▼──────┐ ┌────▼─────────┐
    │  Frontend      │ │  Backend   │ │  Airflow     │
    │  (Next.js)     │ │  (FastAPI) │ │  (Scheduler) │
    └────────────────┘ └─────┬──────┘ └────┬─────────┘
                            │             │
                    ┌───────▼─────────────▼───────┐
                    │         Neo4j Cluster        │
                    │   (Primary + Replicas)      │
                    └──────────────────────────────┘
```

### Deployment Options

#### Option 1: Docker Swarm

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml nascar-dfs

# Scale services
docker service scale nascar-dfs_backend=3

# View services
docker service ls

# View logs
docker service logs -f nascar-dfs_backend
```

#### Option 2: Kubernetes

Create [`k8s/`](k8s/) directory with manifests:

**`k8s/namespace.yaml`**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nascar-dfs
```

**`k8s/neo4j-deployment.yaml`**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: neo4j
  namespace: nascar-dfs
spec:
  replicas: 1
  selector:
    matchLabels:
      app: neo4j
  template:
    metadata:
      labels:
        app: neo4j
    spec:
      containers:
      - name: neo4j
        image: neo4j:5.15.0-community
        ports:
        - containerPort: 7474
        - containerPort: 7687
        env:
        - name: NEO4J_AUTH
          value: "neo4j/nascar_password"
        volumeMounts:
        - name: neo4j-data
          mountPath: /data
      volumes:
      - name: neo4j-data
        persistentVolumeClaim:
          claimName: neo4j-pvc
```

**`k8s/backend-deployment.yaml`**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: nascar-dfs
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: nascar-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: NEO4J_URI
          value: "bolt://neo4j:7687"
        - name: NEO4J_USER
          valueFrom:
            secretKeyRef:
              name: neo4j-secrets
              key: username
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: neo4j-secrets
              key: password
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: nascar-dfs
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

**Deploy to Kubernetes:**
```bash
# Apply all manifests
kubectl apply -f k8s/

# Check pods
kubectl get pods -n nascar-dfs

# Check services
kubectl get services -n nascar-dfs

# View logs
kubectl logs -f deployment/backend -n nascar-dfs
```

#### Option 3: Cloud Platforms

**AWS ECS/Fargate:**
```bash
# Create ECR repository
aws ecr create-repository --repository-name nascar-backend

# Build and push image
docker build -t nascar-backend ./apps/backend
docker tag nascar-backend:latest <account-id>.dkr.ecr.<region>.amazonaws.com/nascar-backend:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/nascar-backend:latest

# Deploy using ECS task definition
aws ecs run-task --cluster nascar-cluster --task-definition nascar-backend
```

**Google Cloud Run:**
```bash
# Build and deploy backend
gcloud builds submit --tag gcr.io/<project-id>/nascar-backend ./apps/backend
gcloud run deploy nascar-backend --image gcr.io/<project-id>/nascar-backend --platform managed

# Build and deploy frontend
gcloud builds submit --tag gcr.io/<project-id>/nascar-frontend ./apps/frontend
gcloud run deploy nascar-frontend --image gcr.io/<project-id>/nascar-frontend --platform managed
```

**Azure Container Instances:**
```bash
# Create resource group
az group create --name nascar-rg --location eastus

# Create container instance
az container create \
  --resource-group nascar-rg \
  --name nascar-backend \
  --image nascar-backend:latest \
  --ports 8000 \
  --environment-variables NEO4J_URI=bolt://neo4j:7687
```

### Database Setup

#### Neo4j Production Configuration

**`neo4j.conf`** (for production):
```properties
# Memory settings
dbms.memory.heap.initial_size=2G
dbms.memory.heap.max_size=4G
dbms.memory.pagecache.size=2G

# Network settings
dbms.default_listen_address=0.0.0.0
dbms.connector.bolt.listen_address=:7687
dbms.connector.http.listen_address=:7474

# Security
dbms.security.auth_enabled=true
dbms.security.procedures.unrestricted=apoc.*
dbms.security.procedures.allowlist=apoc.*

# Logging
dbms.logs.debug.level=INFO
```

#### Neo4j Backup Strategy

```bash
# Enable online backup
dbms.backup.enabled=true
dbms.backup.address=0.0.0.0:6362

# Create backup
neo4j-admin backup --from=bolt://localhost:7687 \
  --backup-dir=/backups/neo4j \
  --name=graph.db-backup \
  --fallback-to-full=true

# Schedule daily backups (cron)
0 2 * * * neo4j-admin backup --from=bolt://localhost:7687 --backup-dir=/backups/neo4j --name=daily-$(date +\%Y\%m\%d)
```

## CI/CD Pipeline

### GitHub Actions Workflow

The project includes a GitHub Actions workflow at [`.github/workflows/docker.yml`](.github/workflows/docker.yml).

**Workflow Stages:**

1. **Lint and Test**
   - Run Python linters (flake8, black)
   - Run TypeScript linters (ESLint)
   - Execute unit tests
   - Run integration tests

2. **Build Docker Images**
   - Build backend image
   - Build frontend image
   - Build Airflow image

3. **Push to Registry**
   - Tag images with commit SHA
   - Push to Docker Hub or ECR
   - Tag latest version

4. **Deploy**
   - Deploy to staging environment
   - Run smoke tests
   - Promote to production (manual approval)

### Custom CI/CD Pipeline

**`.github/workflows/ci-cd.yml`**:
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd apps/backend
          pip install -r requirements.txt
      
      - name: Run backend tests
        run: |
          cd apps/backend
          pytest --cov=app --cov-report=xml
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install frontend dependencies
        run: |
          cd apps/frontend
          npm ci
      
      - name: Run frontend tests
        run: |
          cd apps/frontend
          npm test -- --coverage
      
      - name: Run integration tests
        run: |
          python tests/integration_test.py

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push backend
        uses: docker/build-push-action@v4
        with:
          context: ./apps/backend
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/backend:latest,${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/backend:${{ github.sha }}
      
      - name: Build and push frontend
        uses: docker/build-push-action@v4
        with:
          context: ./apps/frontend
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/frontend:latest,${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/frontend:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Deploy to production
        run: |
          # Add deployment commands here
          echo "Deploying to production..."
```

### Environment-Specific Deployments

**Staging Environment:**
- Auto-deploy on push to `develop` branch
- Run full test suite
- Deploy to staging cluster
- Run smoke tests

**Production Environment:**
- Manual approval required
- Deploy on push to `main` branch
- Run smoke tests
- Monitor for 30 minutes before marking success

### Rollback Strategy

```bash
# Rollback to previous version
docker-compose down
docker-compose up -d --scale backend=0
docker tag nascar-backend:previous nascar-backend:latest
docker-compose up -d

# Kubernetes rollback
kubectl rollout undo deployment/backend -n nascar-dfs

# ECS rollback
aws ecs update-service --cluster nascar-cluster --service backend --task-definition nascar-backend:previous
```

## Monitoring and Logging

### Health Checks

**Backend Health Check:**
```bash
curl http://localhost:8000/health
```

**Service Status:**
```bash
docker-compose ps
```

### Logging

**View All Logs:**
```bash
docker-compose logs -f
```

**View Specific Service Logs:**
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f neo4j
```

**Log Levels:**
- Backend: Configure in [`main.py`](apps/backend/app/main.py)
- Neo4j: Configure in `neo4j.conf`
- Airflow: Configure in `airflow.cfg`

### Monitoring Metrics

**Prometheus Integration:**

Add to [`apps/backend/app/main.py`](apps/backend/app/main.py):
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

**Key Metrics to Monitor:**
- Request rate and latency
- Error rate
- Database connection pool
- Memory and CPU usage
- Queue depth (Airflow)

**Grafana Dashboards:**
- API performance
- Database performance
- Airflow DAG status
- System resources

### Alerting

**Alert Conditions:**
- Backend health check fails for > 5 minutes
- Error rate > 5%
- Response time > 2 seconds (p95)
- Neo4j connection failures
- Disk space < 10%

**Alert Channels:**
- Email
- Slack
- PagerDuty (critical alerts)

## Troubleshooting

### Common Issues

#### Backend Won't Start

**Symptom:** Backend container exits immediately

**Solutions:**
```bash
# Check logs
docker-compose logs backend

# Check Neo4j connection
docker-compose logs neo4j

# Verify environment variables
docker-compose config

# Restart services
docker-compose restart backend
```

#### Frontend Can't Connect to Backend

**Symptom:** API calls fail in browser

**Solutions:**
```bash
# Check backend is running
curl http://localhost:8000/health

# Check API key is configured (non-health endpoints require X-API-Key)
curl -H "X-API-Key: <your-key>" http://localhost:8000/ready

# Check API_URL environment variable
docker-compose exec frontend env | grep API_URL

# Check CORS allowlist (CORS_ALLOW_ORIGINS)
docker-compose exec backend env | grep CORS_ALLOW_ORIGINS

# Check network connectivity
docker-compose exec frontend ping backend
```

#### Neo4j Connection Issues

**Symptom:** "Unable to connect to Neo4j" errors

**Solutions:**
```bash
# Check Neo4j is running
docker-compose ps neo4j

# Check Neo4j logs
docker-compose logs neo4j

# Test connection
docker-compose exec backend python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', 'nascar_password')); driver.verify_connectivity()"

# Reset Neo4j (WARNING: deletes data)
docker-compose down -v
docker-compose up -d neo4j
```

#### Tests Failing

**Symptom:** Unit or integration tests fail

**Solutions:**
```bash
# Run tests with verbose output
pytest -v apps/backend/tests/

# Run specific test
pytest apps/backend/tests/test_kernel.py::test_validate_position

# Check test dependencies
pip list | grep pytest

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Debug Mode

**Enable Debug Logging:**

Backend (add to `.env`):
```bash
LOG_LEVEL=DEBUG
```

Neo4j (add to `neo4j.conf`):
```properties
dbms.logs.debug.level=DEBUG
```

**Enable FastAPI Debug Mode:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
```

### Performance Issues

**Slow API Responses:**

```bash
# Check database performance
docker-compose exec neo4j cypher-shell -u neo4j -p nascar_password "CALL dbms.queryJmx('org.neo4j:*') YIELD attributes WHERE attributes.name = 'QueryExecutionTime' RETURN attributes.value"

# Check memory usage
docker stats

# Profile slow queries
docker-compose exec backend python -c "import cProfile; cProfile.run('your_function()')"
```

**High Memory Usage:**

```bash
# Check memory limits
docker-compose config | grep mem_limit

# Increase memory limits in docker-compose.yml
# Add: mem_limit: 2g

# Clear caches
docker system prune -a
```

### Data Recovery

**Restore from Backup:**

```bash
# Stop Neo4j
docker-compose stop neo4j

# Remove existing data
docker volume rm nascar-model_neo4j_data

# Create new volume
docker volume create nascar-model_neo4j_data

# Restore backup
docker run --rm -v nascar-model_neo4j_data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/neo4j-backup.tar.gz -C /

# Start Neo4j
docker-compose start neo4j
```

## Maintenance

### Regular Tasks

**Daily:**
- Check service health
- Review error logs
- Monitor resource usage

**Weekly:**
- Review performance metrics
- Check disk space
- Update dependencies

**Monthly:**
- Security updates
- Backup verification
- Capacity planning

### Updates and Upgrades

**Update Docker Images:**
```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose up -d --build
```

**Update Dependencies:**

Backend:
```bash
cd apps/backend
pip list --outdated
pip install --upgrade <package>
```

Frontend:
```bash
cd apps/frontend
npm outdated
npm update
```

**Database Migration:**
```bash
# Backup before migration
./scripts/backup-neo4j.sh

# Run migration
docker-compose exec neo4j cypher-shell -u neo4j -p nascar_password < migration.cql
```

## Security

### Security Checklist

- [ ] Change default passwords
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Vulnerability scanning
- [ ] Access control (RBAC)
- [ ] Secrets management

### SSL/TLS Configuration

**Enable SSL for Neo4j:**

```properties
# neo4j.conf
dbms.ssl.policy.bolt.enabled=true
dbms.ssl.policy.bolt.base_directory=certificates/bolt
dbms.ssl.policy.bolt.private_key=private.key
dbms.ssl.policy.bolt.public_certificate=public.crt
dbms.ssl.policy.bolt.client_auth=NONE
```

**Enable SSL for FastAPI:**

```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Run with SSL
uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

### Firewall Rules

```bash
# Allow only necessary ports
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 22/tcp    # SSH
ufw deny 7474/tcp   # Neo4j HTTP (internal only)
ufw deny 7687/tcp   # Neo4j Bolt (internal only)
ufw enable
```

## Support

For deployment issues:
1. Check this guide
2. Review logs
3. Check GitHub Issues
4. Contact support team

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Neo4j Documentation](https://neo4j.com/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Airflow Documentation](https://airflow.apache.org/docs/)
