# Dockerfile for Legal Situation Analyzer

FROM python:3.9-slim

LABEL maintainer="Legal Analyzer Team"
LABEL description="Legal Situation Analyzer - Multilingual Legal Assistant"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    portaudio19-dev \
    python3-pyaudio \
    espeak \
    espeak-data \
    libespeak1 \
    libespeak-dev \
    pulseaudio \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('vader_lexicon')"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs models exports backups

# Set permissions
RUN chmod +x *.py

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "legal_analyzer.py", "--server.port=8501", "--server.address=0.0.0.0"]

---

# docker-compose.yml
version: '3.8'

services:
  legal-analyzer:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./backups:/app/backups
      - ./models:/app/models
    environment:
      - DATABASE_NAME=/app/data/legal_cases.db
      - LOG_LEVEL=INFO
      - TTS_RATE=150
      - DEFAULT_LANGUAGE=en
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Add a reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - legal-analyzer
    restart: unless-stopped

---

# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream legal_analyzer {
        server legal-analyzer:8501;
    }

    server {
        listen 80;
        server_name your-domain.com;
        
        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://legal_analyzer;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Static files
        location /_stcore/static {
            proxy_pass http://legal_analyzer;
            proxy_cache_valid 1y;
        }
    }
}

---

# deployment.sh
#!/bin/bash

# Legal Situation Analyzer Deployment Script

set -e

echo "🚀 Starting Legal Situation Analyzer Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="legal-analyzer"
DOCKER_IMAGE="legal-analyzer:latest"
COMPOSE_FILE="docker-compose.yml"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking system requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check available disk space (minimum 5GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [ $available_space -lt 5242880 ]; then
        log_warn "Low disk space. At least 5GB recommended."
    fi
    
    log_info "System requirements check passed ✅"
}

setup_directories() {
    log_info "Setting up directories..."
    
    mkdir -p data logs backups models exports ssl
    chmod 755 data logs backups models exports
    
    log_info "Directories created ✅"
}

build_image() {
    log_info "Building Docker image..."
    
    docker build -t $DOCKER_IMAGE .
    
    if [ $? -eq 0 ]; then
        log_info "Docker image built successfully ✅"
    else
        log_error "Failed to build Docker image ❌"
        exit 1
    fi
}

deploy_application() {
    log_info "Deploying application..."
    
    # Stop existing containers
    docker-compose down --remove-orphans
    
    # Start new containers
    docker-compose up -d
    
    if [ $? -eq 0 ]; then
        log_info "Application deployed successfully ✅"
    else
        log_error "Failed to deploy application ❌"
        exit 1
    fi
}

setup_ssl() {
    if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
        log_warn "SSL certificates not found. Generating self-signed certificates..."
        
        openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
            -subj "/C=IN/ST=Maharashtra/L=Mumbai/O=Legal Analyzer/CN=localhost"
        
        log_info "Self-signed SSL certificates generated ✅"
        log_warn "For production, please replace with proper SSL certificates"
    fi
}

wait_for_service() {
    log_info "Waiting for service to be ready..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8501/_stcore/health &> /dev/null; then
            log_info "Service is ready ✅"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "Service failed to start within expected time ❌"
    return 1
}

show_status() {
    log_info "Application Status:"
    docker-compose ps
    
    echo ""
    log_info "Application URLs:"
    echo "  - HTTP:  http://localhost:8501"
    echo "  - HTTPS: https://localhost"
    
    echo ""
    log_info "Useful Commands:"
    echo "  - View logs:    docker-compose logs -f"
    echo "  - Stop app:     docker-compose down"
    echo "  - Restart app:  docker-compose restart"
    echo "  - Update app:   ./deployment.sh update"
}

backup_data() {
    log_info "Creating data backup..."
    
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_dir="backups/backup_$timestamp"
    
    mkdir -p "$backup_dir"
    cp -r data/* "$backup_dir/" 2>/dev/null || true
    
    log_info "Backup created at $backup_dir ✅"
}

update_application() {
    log_info "Updating application..."
    
    # Create backup
    backup_data
    
    # Pull latest changes
    git pull origin main 2>/dev/null || log_warn "Not a git repository or no updates available"
    
    # Rebuild and deploy
    build_image
    deploy_application
    wait_for_service
    
    log_info "Application updated successfully ✅"
}

cleanup() {
    log_info "Cleaning up..."
    
    # Remove old images
    docker image prune -f
    
    # Remove old backups (keep last 10)
    ls -t backups/ | tail -n +11 | xargs -r rm -rf
    
    log_info "Cleanup completed ✅"
}

# Main deployment logic
case "${1:-deploy}" in
    "deploy")
        check_requirements
        setup_directories
        setup_ssl
        build_image
        deploy_application
        wait_for_service
        show_status
        ;;
    
    "update")
        update_application
        show_status
        ;;
    
    "backup")
        backup_data
        ;;
    
    "cleanup")
        cleanup
        ;;
    
    "status")
        show_status
        ;;
    
    "logs")
        docker-compose logs -f
        ;;
    
    "stop")
        log_info "Stopping application..."
        docker-compose down
        log_info "Application stopped ✅"
        ;;
    
    "restart")
        log_info "Restarting application..."
        docker-compose restart
        wait_for_service
        show_status
        ;;
    
    *)
        echo "Usage: $0 {deploy|update|backup|cleanup|status|logs|stop|restart}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Full deployment (default)"
        echo "  update   - Update application"
        echo "  backup   - Create data backup"
        echo "  cleanup  - Clean up old images and backups"
        echo "  status   - Show application status"
        echo "  logs     - View application logs"
        echo "  stop     - Stop application"
        echo "  restart  - Restart application"
        exit 1
        ;;
esac

log_info "Operation completed! 🎉"

---

# kubernetes.yaml (Optional Kubernetes deployment)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: legal-analyzer
  labels:
    app: legal-analyzer
spec:
  replicas: 2
  selector:
    matchLabels:
      app: legal-analyzer
  template:
    metadata:
      labels:
        app: legal-analyzer
    spec:
      containers:
      - name: legal-analyzer
        image: legal-analyzer:latest
        ports:
        - containerPort: 8501
        env:
        - name: DATABASE_NAME
          value: "/app/data/legal_cases.db"
        - name: LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
        - name: logs-volume
          mountPath: /app/logs
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /_stcore/health
            port: 8501
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: legal-analyzer-data
      - name: logs-volume
        persistentVolumeClaim:
          claimName: legal-analyzer-logs

---
apiVersion: v1
kind: Service
metadata:
  name: legal-analyzer-service
spec:
  selector:
    app: legal-analyzer
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8501
  type: LoadBalancer

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: legal-analyzer-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: legal-analyzer-logs
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi