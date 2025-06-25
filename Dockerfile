FROM python:3.10-bullseye
RUN apt-get update \
    && apt-get install -y gcc git curl
RUN apt-get remove -y cmdtest yarn \
    && apt-get autoremove -y \
    && apt-get clean
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean
RUN npm install -g yarn \
    && yarn global add @postlight/parser

WORKDIR /app

COPY . .
RUN pip install -r requirements.txt
RUN python install.py
