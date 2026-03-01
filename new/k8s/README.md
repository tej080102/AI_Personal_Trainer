# Build the Docker image
docker build -t your-docker-registry/ai-trainer:latest .

# Push to your registry
docker push your-docker-registry/ai-trainer:latest

# Update the ConfigMap and Secrets with your values
# Edit k8s/deployment.yaml and replace:
# - `your-docker-registry/ai-trainer:latest` with your actual image
# - Secret `DB_PASSWORD` with base64-encoded password: echo -n "your_password" | base64
# - Add `OPENAI_API_KEY` to secrets if using cloud mode

# Apply the Kubernetes configuration
kubectl apply -f k8s/deployment.yaml

# Verify deployments
kubectl get pods -n ai-trainer
kubectl get services -n ai-trainer

# Check API health
kubectl port-forward -n ai-trainer svc/trainer-api-service 8080:80
# Then visit: http://localhost:8080/health

# View logs
kubectl logs -n ai-trainer -l app=trainer-api --tail=50 -f

# Scale the API
kubectl scale deployment trainer-api-local -n ai-trainer --replicas=3

# Clean up
kubectl delete namespace ai-trainer
