#!/bin/bash

# Verify required environment variables
required_vars=(
    "PROJECT_ID"
    "REGION"
    "DBUSER"
    "DBPASS"
    "DBNAME"
    "ACCESS_SECRET_KEY"
    "REFRESH_SECRET_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set in .env file"
        exit 1
    fi
done

# Verify gcloud is installed and configured
echo "Checking gcloud installation..."
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud is not installed. Please install Google Cloud SDK first."
    exit 1
fi

echo "Checking gcloud authentication..."
gcloud auth list

# Verify kubectl is installed
echo "Checking kubectl installation..."
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Set GCP project and region
echo "Setting GCP project and region..."
gcloud config set project $PROJECT_ID
gcloud config set compute/region $REGION

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    sqladmin.googleapis.com \
    container.googleapis.com \
    containerregistry.googleapis.com \
    compute.googleapis.com

# Create GKE cluster (if not exists)
echo "Creating GKE cluster..."
gcloud container clusters create ntu-cluster \
    --region $REGION \
    --num-nodes 3 \
    --machine-type e2-standard-4

# Get cluster credentials
echo "Getting cluster credentials..."
gcloud container clusters get-credentials ntu-cluster --region $REGION

# Create namespace
echo "Creating Kubernetes namespace..."
kubectl create namespace ntu

# Create secrets
echo "Creating Kubernetes secrets..."
kubectl create secret generic ntu-secrets \
    --namespace=ntu \
    --from-literal=db_user=$DBUSER \
    --from-literal=db_password=$DBPASS \
    --from-literal=db_name=$DBNAME \
    --from-literal=access_secret_key=$ACCESS_SECRET_KEY \
    --from-literal=refresh_secret_key=$REFRESH_SECRET_KEY

# Build and push Docker images
echo "Building and pushing Docker images..."
docker build -t gcr.io/$PROJECT_ID/ntu-backend:latest -f backend/Dockerfile .
docker push gcr.io/$PROJECT_ID/ntu-backend:latest

docker build -t gcr.io/$PROJECT_ID/ntu-frontend:latest -f frontend/Dockerfile .
docker push gcr.io/$PROJECT_ID/ntu-frontend:latest

# Apply Kubernetes configurations
echo "Applying Kubernetes configurations..."
kubectl apply -f infrastructure/k8s/

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
for i in {1..10}; do
    echo "Checking deployment status... (attempt $i)"
    kubectl get pods -n ntu
    sleep 30
done

# Print final status
echo "\nDeployment completed!"
echo "Checking final status:"

# Get services
echo "\nServices:"
kubectl get svc -n ntu

# Get pods
echo "\nPods:"
kubectl get pods -n ntu

# Get ingress
echo "\nIngress:"
kubectl get ingress -n ntu

# Print success message
echo "\nDeployment successful!"
echo "Your application should now be accessible at:"
echo "Frontend: https://ntu.example.com"
echo "API: https://ntu.example.com/api"
