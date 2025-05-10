# Ntu Architecture

## Project Structure

```mermaid
graph TD
    subgraph Local Development
        Frontend[Frontend (React/Vue)]
        Backend[Backend (FastAPI)]
        LocalDB[Local PostgreSQL]
        LocalRedis[Local Redis]
    end

    subgraph Google Cloud Platform
        GKE[GKE Cluster]
        subgraph Kubernetes
            FrontendService[ntu-frontend Service]
            BackendService[ntu-backend Service]
            Ingress[Ingress Controller]
            FrontendDeploy[Frontend Deployment]
            BackendDeploy[Backend Deployment]
        end
        
        subgraph Cloud Services
            CloudSQL[Cloud SQL (PostgreSQL)]
            Redis[Memorystore (Redis)]
            GCS[GCS Bucket]
        end
    end

    subgraph External
        Domain[ntu.example.com]
    end

    %% Connections
    Frontend --> Backend
    Backend --> LocalDB
    Backend --> LocalRedis
    Frontend --> LocalDB
    Frontend --> LocalRedis

    FrontendDeploy --> FrontendService
    BackendDeploy --> BackendService
    FrontendService --> Ingress
    BackendService --> Ingress
    Ingress --> Domain

    BackendDeploy --> CloudSQL
    BackendDeploy --> Redis
    FrontendDeploy --> CloudSQL
    FrontendDeploy --> Redis
    BackendDeploy --> GCS
    FrontendDeploy --> GCS

    %% Styling
    classDef service fill:#f9f,stroke:#333,stroke-width:2px
    classDef deployment fill:#bbf,stroke:#333,stroke-width:2px
    classDef database fill:#bfb,stroke:#333,stroke-width:2px
    classDef external fill:#fbb,stroke:#333,stroke-width:2px
    
    class FrontendService,BackendService,Ingress service
    class FrontendDeploy,BackendDeploy deployment
    class CloudSQL,Redis,GCS database
    class Domain external
```

## Component Details

### 1. Frontend
- Built with React/Vue
- Served via Nginx
- Communicates with backend API
- State management with Redis
- Served through GKE Ingress

### 2. Backend
- FastAPI application
- PostgreSQL database connection
- Redis integration
- GCS for storage
- Health check endpoint
- JWT authentication

### 3. Database Layer
- Cloud SQL (PostgreSQL)
  - Managed PostgreSQL instance
  - Connection pooling
  - Automatic backups
  
- Memorystore (Redis)
  - In-memory data store
  - Session management
  - Caching layer

### 4. Storage
- Google Cloud Storage
  - File uploads
  - Static assets
  - Backup storage

### 5. Kubernetes Components
- Frontend Deployment
  - 2 replicas
  - Health checks
  - Resource limits
  
- Backend Deployment
  - 3 replicas
  - Resource limits
  - Environment variables
  
- Ingress Controller
  - SSL termination
  - Path-based routing
  - Load balancing

### 6. Deployment Flow
1. Build Docker images
2. Push to Container Registry
3. Create/Update GKE cluster
4. Deploy Kubernetes resources
5. Configure Ingress
6. Set up SSL certificate

## Security Features
- JWT authentication
- Environment variable management
- Secret management
- SSL/TLS encryption
- Resource isolation

## Monitoring & Maintenance
- Health checks
- Resource limits
- Automatic scaling
- Backup configuration
- Logging configuration
