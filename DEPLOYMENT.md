# ERP System - Deployment Guide

This guide covers deployment options for the ERP System: local development with Docker, and production deployment.

## Prerequisites

- Docker & Docker Compose installed
- PostgreSQL (for non-Docker local dev)
- Redis (for caching and Celery)
- Python 3.11+ (for local development without Docker)

## Local Development with Docker

### Quick Start

1. **Clone and navigate to the project:**
   ```bash
   cd erp-system
   ```

2. **Create `.env` file from example:**
   ```bash
   cp .env.example .env
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Run migrations:**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

5. **Create super admin:**
   ```bash
   docker-compose exec web python manage.py create_super_admin
   ```

6. **Setup roles and permissions:**
   ```bash
   docker-compose exec web python manage.py setup_roles
   ```

7. **Access the application:**
   - Web UI: http://localhost:8000
   - API Docs: http://localhost:8000/api/docs/
   - Admin: http://localhost:8000/admin/
   - Health Check: http://localhost:8000/health/

### Services in Docker Compose

- **postgres**: PostgreSQL 15 database
- **redis**: Redis cache & message broker
- **web**: Django application server
- **celery**: Celery worker for async tasks
- **celery-beat**: Celery beat scheduler for periodic tasks

### Useful Docker Commands

```bash
# View logs
docker-compose logs -f web
docker-compose logs -f celery
docker-compose logs -f postgres

# Execute commands
docker-compose exec web python manage.py shell
docker-compose exec web python manage.py collectstatic

# Stop services
docker-compose down

# Clean up volumes (WARNING: deletes data)
docker-compose down -v

# Rebuild images
docker-compose build --no-cache
```

## Production Deployment

### Option 1: Docker with Environment Configuration

1. **Set production environment variables:**
   ```bash
   export DEBUG=False
   export SECRET_KEY="your-very-long-random-secret-key"
   export ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"
   export DB_PASSWORD="your-secure-password"
   export REDIS_URL="redis://redis-host:6379/1"
   export EMAIL_HOST="smtp.gmail.com"
   export EMAIL_HOST_USER="your-email@gmail.com"
   export EMAIL_HOST_PASSWORD="your-app-password"
   export SECURE_SSL_REDIRECT=True
   export SESSION_COOKIE_SECURE=True
   export CSRF_COOKIE_SECURE=True
   ```

2. **Create production `.env` file:**
   ```bash
   cat > .env.production << EOF
   DEBUG=False
   SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   DB_NAME=erp_prod
   DB_USER=erp_user
   DB_PASSWORD=your-secure-db-password
   DB_HOST=your-db-host
   DB_PORT=5432
   REDIS_URL=redis://your-redis-host:6379/1
   CELERY_BROKER_URL=redis://your-redis-host:6379/0
   CELERY_RESULT_BACKEND=redis://your-redis-host:6379/0
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   SECURE_SSL_REDIRECT=True
   SESSION_COOKIE_SECURE=True
   CSRF_COOKIE_SECURE=True
   SECURE_HSTS_SECONDS=31536000
   SECURE_HSTS_INCLUDE_SUBDOMAINS=True
   SECURE_HSTS_PRELOAD=True
   EOF
   ```

3. **Start services:**
   ```bash
   docker-compose --env-file .env.production up -d
   ```

### Option 2: Manual Server Deployment (Ubuntu/Debian)

1. **Install dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3.11 python3.11-venv python3.11-dev postgresql redis-server nginx supervisor
   ```

2. **Clone project and setup virtual environment:**
   ```bash
   git clone <repo-url> /var/www/erp-system
   cd /var/www/erp-system
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Collect static files:**
   ```bash
   python manage.py collectstatic --noinput
   ```

4. **Create systemd service for Django:**
   ```bash
   sudo cat > /etc/systemd/system/erp-web.service << EOF
   [Unit]
   Description=ERP System Django Application
   After=network.target postgresql.service redis-server.service

   [Service]
   Type=notify
   User=www-data
   WorkingDirectory=/var/www/erp-system
   Environment="PATH=/var/www/erp-system/venv/bin"
   EnvironmentFile=/var/www/erp-system/.env
   ExecStart=/var/www/erp-system/venv/bin/gunicorn \
             config.wsgi:application \
             --bind unix:/run/erp.sock \
             --workers 4 \
             --threads 2 \
             --timeout 60 \
             --max-requests 500 \
             --max-requests-jitter 50

   [Install]
   WantedBy=multi-user.target
   EOF

   sudo systemctl daemon-reload
   sudo systemctl enable erp-web.service
   sudo systemctl start erp-web.service
   ```

5. **Create systemd service for Celery:**
   ```bash
   sudo cat > /etc/systemd/system/erp-celery.service << EOF
   [Unit]
   Description=ERP System Celery Worker
   After=network.target redis-server.service

   [Service]
   Type=forking
   User=www-data
   WorkingDirectory=/var/www/erp-system
   Environment="PATH=/var/www/erp-system/venv/bin"
   EnvironmentFile=/var/www/erp-system/.env
   ExecStart=/var/www/erp-system/venv/bin/celery multi start worker \
             -A config \
             --pidfile=/var/run/%n.pid \
             --logfile=/var/log/celery/%n%I.log \
             --loglevel=info

   [Install]
   WantedBy=multi-user.target
   EOF

   sudo systemctl daemon-reload
   sudo systemctl enable erp-celery.service
   sudo systemctl start erp-celery.service
   ```

6. **Configure Nginx reverse proxy:**
   ```bash
   sudo cat > /etc/nginx/sites-available/erp-system << EOF
   upstream erp {
       server unix:/run/erp.sock fail_timeout=0;
   }

   server {
       listen 80;
       server_name yourdomain.com;
       client_max_body_size 10M;

       location = /favicon.ico {
           access_log off;
           log_not_found off;
       }

       location /static/ {
           alias /var/www/erp-system/staticfiles/;
           expires 30d;
       }

       location /media/ {
           alias /var/www/erp-system/media/;
           expires 7d;
       }

       location /health/ {
           access_log off;
           proxy_pass http://erp;
           proxy_set_header Host \$host;
           proxy_set_header X-Real-IP \$remote_addr;
       }

       location / {
           proxy_pass http://erp;
           proxy_set_header Host \$host;
           proxy_set_header X-Real-IP \$remote_addr;
           proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto \$scheme;
           proxy_redirect off;
       }
   }
   EOF

   sudo ln -s /etc/nginx/sites-available/erp-system /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

7. **Setup SSL with Let's Encrypt:**
   ```bash
   sudo apt-get install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

## Health Monitoring

The application exposes a health check endpoint at `/health/` that monitors:
- Database connectivity
- Cache (Redis) connectivity
- Application status

Health check returns:
```json
{
  "status": "healthy|degraded|unhealthy",
  "database": "ok|error: ...",
  "cache": "ok|error: ..."
}
```

Use this for monitoring and load balancer health checks:
```bash
curl http://localhost:8000/health/
```

## API Documentation

Automatically generated API documentation is available at:
- **Swagger UI**: http://yourdomain.com/api/docs/
- **ReDoc**: http://yourdomain.com/api/redoc/
- **OpenAPI Schema**: http://yourdomain.com/api/schema/

## Logging

Logs are written to:
- **Application logs**: `logs/django.log`
- **Error logs**: `logs/error.log`

In Docker, view logs with:
```bash
docker-compose logs -f web
```

## Backup & Restore

### Backup Database
```bash
# Docker
docker-compose exec postgres pg_dump -U postgres erp > backup.sql

# Manual server
pg_dump -U postgres erp > backup.sql
```

### Restore Database
```bash
# Docker
docker-compose exec -T postgres psql -U postgres erp < backup.sql

# Manual server
psql -U postgres erp < backup.sql
```

## Troubleshooting

### Port already in use
```bash
# Find process using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>
```

### Database connection issues
```bash
# Check database service
docker-compose logs postgres

# Verify connection
docker-compose exec postgres psql -U postgres -c "SELECT 1"
```

### Redis connection issues
```bash
# Check Redis service
docker-compose logs redis

# Test connection
docker-compose exec redis redis-cli ping
```

### Clear cache
```bash
docker-compose exec redis redis-cli FLUSHDB
```

### Celery not processing tasks
```bash
# Check Celery worker logs
docker-compose logs celery

# Check Redis queue
docker-compose exec redis redis-cli LLEN celery
```

## Performance Tuning

1. **Database Connection Pooling**: Configured in settings with max 20 connections, 10 reusable
2. **Redis Compression**: Enabled by default for cached data
3. **Static Files**: Served with compression via WhiteNoise
4. **Gunicorn Workers**: Adjust `--workers` based on CPU cores
5. **Celery Workers**: Adjust concurrency based on requirements

For production, monitor:
- Database query times
- Cache hit rates
- Celery task queue depth
- Server resource usage (CPU, memory, disk)
