FROM ghcr.io/mlflow/mlflow:v2.16.2

RUN pip install --no-cache-dir psycopg2-binary==2.9.9 && \
    apt-get update && apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /mlflow/artifacts && chmod -R 777 /mlflow/artifacts

EXPOSE 5000
ENTRYPOINT ["mlflow"]
CMD ["server"]