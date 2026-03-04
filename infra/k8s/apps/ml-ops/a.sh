#!/bin/bash
# Run from project root directory

# 1. Build and push MLflow image
docker build -t localhost:5000/mlflow:v1 -f apps/ml-ops/mlflow/Dockerfile apps/ml-ops/mlflow/
docker push localhost:5000/mlflow:v1

# 2. Build and push ml-predict image
docker build -t localhost:5000/ml-predict:v1 --target predict -f apps/ml-ops/Dockerfile apps/ml-ops/
docker push localhost:5000/ml-predict:v1

# 3. Build and push ml-train image
docker build -t localhost:5000/ml-train:v1 --target train -f apps/ml-ops/Dockerfile apps/ml-ops/
docker push localhost:5000/ml-train:v1