FROM python:3.10-bullseye

# Install system dependencies including Playwright dependencies
RUN apt-get update \
    && apt-get install -y gcc git curl \
    && apt-get install -y libnss3-dev libatk-bridge2.0-dev libdrm2 libxkbcommon0 libgtk-3-0 libgbm-dev libasound2 \
    && apt-get remove -y cmdtest yarn \
    && apt-get autoremove -y \
    && apt-get clean

# Install Node.js and Mercury Parser
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean
# Install Mercury Parser CLI globally (official package)
RUN npm install -g @postlight/mercury-parser

WORKDIR /app

COPY . .

# Install Python dependencies including Playwright
RUN pip install -r requirements.txt

# Install Playwright browsers (Chromium for dynamic media extraction)
RUN python -m playwright install chromium --with-deps

# Run setup script
RUN python install.py
