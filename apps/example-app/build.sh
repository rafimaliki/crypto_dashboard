#!/bin/bash
eval $(minikube docker-env)
docker build -t example-app:latest .
