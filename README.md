# Ntu - Modular Monolith Platform

A scalable platform for linguistic data processing and analysis, built as a modular monolith optimized for Kubernetes deployment on GCP.

## Project Structure

```
/crowd-data-platform
  /frontend
    └── React application for UI
  /backend
    └── FastAPI services for API, job queues, and authentication
  /model-inference
    └── FastAPI service for AI/ML model serving
  /llm-expert
    └── HuggingFace-hosted LLM models and prompt logic
  /database
    └── Database schemas, migrations, and GCP Datastore config
  /infrastructure
    ├── docker-compose.yml
    ├── k8s/
    │   └── Kubernetes deployment YAMLs
    └── terraform/
        └── GCP infrastructure setup
  /shared
    └── Common code, types, and utilities
```

## Services

### Frontend
Modern React application built with Vite and TypeScript.

### Backend
FastAPI-based services including:
- Authentication
- Data processing
- Job queues
- API endpoints

### Model Inference
Separate FastAPI service for AI/ML model serving.

### LLM Expert
HuggingFace-hosted LLM models with custom prompt logic.

### Database
- PostgreSQL for relational data
- GCP Datastore for large files (audio, images)
- Migrations and schema management

## Infrastructure

### Kubernetes
Kubernetes deployment YAMLs for each service.

### GCP
- GKE cluster for Kubernetes
- Cloud Storage for file storage
- Cloud SQL for PostgreSQL
- Datastore for large files
- Terraform for infrastructure as code

## Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
```

3. Start development servers:
```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend
cd frontend
npm run dev
```

## Deployment

1. Build Docker images:
```bash
docker-compose build
```

2. Deploy to Kubernetes:
```bash
kubectl apply -k infrastructure/k8s/
```
