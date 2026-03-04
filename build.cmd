@echo off

echo ======================================
echo Building Docker Images (v1)
echo ======================================

echo.
echo Building DataOps images...
echo Building dataops-listener:v1
minikube image build -t dataops-listener:v1 -f apps/dataops/Dockerfile --build-opt=target=listener apps/dataops

echo Building dataops-persistence:v1
minikube image build -t dataops-persistence:v1 -f apps/dataops/Dockerfile --build-opt=target=persistence apps/dataops

echo.
echo Building ML-Ops images...
echo Building ml-train:v1
minikube image build -t ml-train:v1 -f apps/ml-ops/Dockerfile --build-opt=target=train apps/ml-ops

echo Building ml-predict:v1
minikube image build -t ml-predict:v1 -f apps/ml-ops/Dockerfile --build-opt=target=predict apps/ml-ops

echo Building mlflow:v1
minikube image build -t mlflow:v1 apps/ml-ops/mlflow

echo.
echo Building Superset image...
echo Building superset-pgdriver:v1
minikube image build -t superset-pgdriver:v1 apps/superset

echo.
echo ======================================
echo All images built successfully!
echo ======================================
echo.
echo Built images:
echo   - dataops-listener:v1
echo   - dataops-persistence:v1
echo   - ml-train:v1
echo   - ml-predict:v1
echo   - mlflow:v1
echo   - superset-pgdriver:v1
echo.