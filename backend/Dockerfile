FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    CHROME_BIN=/usr/bin/google-chrome

WORKDIR /app/AI_Translation/App/backend

# Install system dependencies and Google Chrome for Selenium-based crawlers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        gnupg \
        ca-certificates \
        fonts-liberation \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libatspi2.0-0 \
        libdrm2 \
        libgtk-3-0 \
        libnss3 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        unzip \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt

RUN pip install --upgrade pip \
    && pip install --extra-index-url https://download.pytorch.org/whl/cpu -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY . /app/AI_Translation/App/backend

RUN mkdir -p /app/AI_Translation/App/backend/data /app/.cache/huggingface

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
