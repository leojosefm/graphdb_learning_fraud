FROM python:3.12-slim

WORKDIR /scripts

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt