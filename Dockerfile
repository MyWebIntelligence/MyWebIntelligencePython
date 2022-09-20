FROM python:3.10-slim
RUN apt-get update \
    && apt-get install -y gcc git
RUN apt-get remove cmdtest yarn
RUN apt-get install -y nodejs npm \
    && apt-get clean
RUN npm install -g yarn \
    && yarn global add @postlight/mercury-parser

WORKDIR /app

COPY . .
RUN pip install -r requirements.txt
RUN python install.py
