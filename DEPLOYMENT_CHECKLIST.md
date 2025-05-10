# Ntu Deployment Checklist

## Prerequisites
- [ ] Google Cloud SDK installed and configured
- [ ] kubectl installed and configured
- [ ] Docker installed and configured
- [ ] Domain registered (ntu.example.com)
- [ ] SSL certificate configured

## 1. Google Cloud Project Setup
- [ ] Set project ID: `bantuai`
- [ ] Set region: `africa-south1`
- [ ] Enable required APIs:
  - Cloud SQL Admin API
  - Container Registry API
  - Compute Engine API
  - Container API

## 2. Build and Push Docker Images
```bash
# Build and push backend
export PROJECT_ID=bantuai
docker build -t gcr.io/$PROJECT_ID/ntu-backend:latest -f backend/Dockerfile .
docker push gcr.io/$PROJECT_ID/ntu-backend:latest

# Build and push frontend
docker build -t gcr.io/$PROJECT_ID/ntu-frontend:latest -f frontend/Dockerfile .
docker push gcr.io/$PROJECT_ID/ntu-frontend:latest
```

## 3. Kubernetes Cluster Setup
```bash
# Create cluster
gcloud container clusters create ntu-cluster \
    --region africa-south1 \
    --num-nodes 3 \
    --machine-type e2-standard-4

# Get credentials
gcloud container clusters get-credentials ntu-cluster --region africa-south1
```

## 4. Create Kubernetes Namespace
```bash
kubectl create namespace ntu
```

## 5. Create Secrets
```bash
kubectl create secret generic ntu-secrets \
    --namespace=ntu \
    --from-literal=db_user=$DBUSER \
    --from-literal=db_password=$DBPASS \
    --from-literal=db_name=$DBNAME \
    --from-literal=access_secret_key=$ACCESS_SECRET_KEY \
    --from-literal=refresh_secret_key=$REFRESH_SECRET_KEY
```

## 6. Deploy Services
```bash
# Apply all configurations
kubectl apply -f infrastructure/k8s/

# Verify deployments
kubectl get pods -n ntu
kubectl get services -n ntu
```

## 7. Verify Deployment
```bash
# Check ingress status
kubectl get ingress -n ntu

# Get external IP
kubectl get svc -n ntu

# Check logs
kubectl logs -n ntu <pod-name>
```

## 8. Post-Deployment
- [ ] Verify frontend is accessible at https://ntu.example.com
- [ ] Verify API is accessible at https://ntu.example.com/api
- [ ] Verify database connection
- [ ] Verify Redis connection (when implemented)
- [ ] Verify health check endpoint

## Troubleshooting Commands
```bash
# Check pod status
kubectl get pods -n ntu

# Check pod logs
kubectl logs -n ntu <pod-name>

# Check service status
kubectl get svc -n ntu

# Check deployment status
kubectl get deployments -n ntu

# Describe pod
kubectl describe pod -n ntu <pod-name>

# Port-forward for local testing
kubectl port-forward -n ntu svc/ntu-backend 8000:8000
```
