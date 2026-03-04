FROM python:3.11-slim as base

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY train.py .
COPY predict.py .

FROM base as train
EXPOSE 8000
CMD ["uvicorn", "train:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base as predict
EXPOSE 8000
CMD ["uvicorn", "predict:app", "--host", "0.0.0.0", "--port", "8000"]
