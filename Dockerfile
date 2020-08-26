FROM python:3.6-slim
RUN apt-get update \
    && apt-get install gcc -y \
    && apt-get clean

WORKDIR /app

COPY . .
RUN pip install -r requirements.txt
RUN python install.py
