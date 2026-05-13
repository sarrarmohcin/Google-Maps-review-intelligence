FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
 && rm -rf /var/lib/apt/lists/*
 
# Copy requirements
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt