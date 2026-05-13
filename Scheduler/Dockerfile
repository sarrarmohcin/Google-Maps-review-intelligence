FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    xvfb \
    supervisor \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    fonts-liberation \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app .
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

RUN python -m camoufox fetch

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]