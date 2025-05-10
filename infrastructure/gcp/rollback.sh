#!/bin/bash

# Verify required environment variables
required_vars=(
    "PROJECT_ID"
    "REGION"
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

# Get cluster credentials
echo "Getting cluster credentials..."
gcloud container clusters get-credentials ntu-cluster --region $REGION

# Delete deployments
echo "Deleting deployments..."
kubectl delete deployment -n ntu ntu-backend ntu-frontend --ignore-not-found

# Delete services
echo "Deleting services..."
kubectl delete svc -n ntu ntu-backend ntu-frontend --ignore-not-found

# Delete ingress
echo "Deleting ingress..."
kubectl delete ingress -n ntu ntu-ingress --ignore-not-found

# Delete secrets
echo "Deleting secrets..."
kubectl delete secret -n ntu ntu-secrets --ignore-not-found

# Delete configmaps
echo "Deleting configmaps..."
kubectl delete configmap -n ntu --all --ignore-not-found

# Delete namespace (will fail if resources are still terminating)
echo "Deleting namespace..."
kubectl delete namespace ntu --ignore-not-found

# Delete Docker images
echo "Deleting Docker images..."
gcloud container images delete gcr.io/$PROJECT_ID/ntu-backend:latest --quiet
gcloud container images delete gcr.io/$PROJECT_ID/ntu-frontend:latest --quiet

# Delete GKE cluster (optional)
read -p "Do you want to delete the GKE cluster? (y/n): " delete_cluster
if [ "$delete_cluster" = "y" ]; then
    echo "Deleting GKE cluster..."
    gcloud container clusters delete ntu-cluster --region $REGION --quiet
fi

# Print final status
echo "\nRollback completed!"
echo "All Kubernetes resources have been deleted."
echo "Docker images have been removed from Container Registry."
echo "If you deleted the GKE cluster, you'll need to recreate it for future deployments."
