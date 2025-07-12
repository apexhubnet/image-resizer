FROM python:3.10-slim-bullseye

# Установка зависимостей для Pillow
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV GUNICORN_CMD_ARGS="--bind=0.0.0.0:5000 --workers=4"

EXPOSE 5000
CMD ["gunicorn", "app:app"]