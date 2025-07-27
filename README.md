# Обработка и загрузка изображений в S3 (Timeweb Cloud) 🌌

REST API для обработки и загрузки изображений в S3-совместимое хранилище Timeweb Cloud. Сервис автоматически конвертирует изображения в формат WebP, применяет ресайзинг по заданным параметрам и обеспечивает кэширование на стороне хранилища.

## 📦 Структура проекта
```
├── Dockerfile            # Конфигурация контейнера
├── app.py                # Основная логика
└── .env.example          # Шаблон конфигурации
```

## 🌟 Основные возможности

- Автоматическая конвертация в WebP с настраиваемым качеством
- Ресайз изображений по нескольким стратегиям
- Проверка CORS и Токена аутентификации
- Генерация уникальных имен файлов через хеширование
- Загрузка в S3 с настройкой кэширования
- Поддержка ретина-дисплеев (@2x, @3x, @4x версии)
- Health-check для мониторинга работоспособности

## ⚠️ Конфигурация  эндпоинтов

```
Эндпоинт    Размеры                              Тип обработки
/64       - [64x64, 128x128, 185x185, 256x256] - Квадратные превью
/80       - [80x80, 120x120]                   - Квадратные превью
/100      - [100px, 200px, 600px]              - По ширине
/158      - [158x158, 316x316, 474x474]        - Квадратные превью
/400      - [400px, 800px, 1200px]             - По ширине
/600      - [600px, 1200px, 1800px]            - По ширине
/upload   - [Оригинальный размер]              - Без ресайза

```

## 🆕 Добавление нового эндпоинта

### 1. Добавление конфигурации размеров

Откройте файл **app.py** и добавьте новую конфигурацию в словарь **SIZES_CONFIG**:
```
SIZES_CONFIG = {
    # ... существующие конфигурации ...
    '200': {  # Новый эндпоинт для 200px
        '': 200,          # Базовая версия (ширина 200px)
        '@2x': 400,       # Для ретина-дисплеев (2x)
        '@3x': 600        # Для HiDPI-дисплеев (3x)
    },
    '300-square': {  # Квадратные превью 300x300
        '': (300, 300),
        '@2x': (600, 600)
    }
}
```
### 2. Создание обработчика эндпоинта
Добавьте новый обработчик для эндпоинта в том же файле **app.py**:
```
@app.route('/200', methods=['POST', 'OPTIONS'])
@token_required
def upload_200():
    return handle_upload('200')

@app.route('/300-square', methods=['POST', 'OPTIONS'])
@token_required
def upload_300_square():
    return handle_upload('300-square')
```
### 3. Обновление Docker-образа (если требуется)
Если вы изменили зависимости, обновите **requirements.txt**:
```
echo "new-package==1.0.0" >> requirements.txt
```
Пересоберите Docker-образ:
```
docker-compose build --no-cache
```
Перезапуск сервиса
```
docker-compose up -d --force-recreate
```

### Дополнительные настройки
- Типы обработки:
  - Для ресайза по ширине используйте целое число: **'': 200**
  - Для квадратных превью используйте кортеж: **'': (300, 300)**
- Множители для ретина-дисплеев:
  - Добавляйте суффиксы **@2x**, **@3x**, **@4x** с соответствующими размерами
  - Размеры должны быть пропорциональны базовой версии
- Качество изображения:
  - Настройте параметры в **.env** файле:

```
API_TOKEN=your_strong_secret_token              # Authorization: Bearer <TOKEN>
CORS_ORIGIN=https://domain.com                  # Домен для CORS, по умолчанию *
WEBP_QUALITY=90                                 # Качество от 1 до 100
WEBP_METHOD=6                                   # Метод сжатия (0-6)
```
### Примеры конфигураций
Ресайз по высоте (новый тип обработки):
- Добавьте новую функцию обработки в **app.py**:
```
def resize_to_height(image, target_height):
    img = Image.open(image)
    original_width, original_height = img.size
    ratio = target_height / original_height
    new_width = int(original_width * ratio)
    return img.resize((new_width, target_height), Image.LANCZOS)
```
- Модифицируйте **process_upload** для поддержки нового типа:
```
def process_upload(file, sizes):
    # ...
    if isinstance(dimensions, tuple):
        # Квадратная обработка
    elif isinstance(dimensions, int):
        # Ресайз по ширине
    elif isinstance(dimensions, str) and dimensions.startswith('h'):
        # Новый тип: ресайз по высоте
        target_height = int(dimensions[1:])
        img = resize_to_height(BytesIO(image_bytes), target_height)
    # ...
```
- Добавьте конфигурацию:
```
'portrait': {
    '': 'h300',     # Высота 300px
    '@2x': 'h600'   # Высота 600px
}
```
## 💡 Использование API

### Загрузка изображения
```
curl -X POST \
  -H "Authorization: Bearer YOUR_SECRET_TOKEN" \
  -H "Origin: https://your-domain.com" \
  -F "file=@image.jpg" \
  http://localhost:5000/100
```
### Пример успешного ответа
```
{
  "hash": "a1b2c3d4e5f6g7h8i9j0k1l2",
  "endpoint": "100",
  "sizes": ["", "@2x", "@3x"],
  "format": "webp"
}
```
### 🏥 Health check
```curl http://localhost:5000/health```

## Настройка окружения
Создайте файл **.env** на основе **.env.example**:
```
# S3 Configuration
S3_BUCKET=your_bucket_name
S3_ENDPOINT=https://s3.timeweb.com
S3_REGION=ru-1
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key

# Настройки CORS
API_TOKEN=your_strong_secret_token
#CORS_ORIGIN=https://domain.com, по умолчанию *

# WebP quality settings
WEBP_QUALITY=85
WEBP_METHOD=6
```
## 🚀 Запуск сервиса
Сборка Docker-образа
```docker build -t image-resizer .```
Запуск через Docker Compose
```docker-compose up -d```

### Особенности реализации:
- Генерация уникального 24-символьного хеша для имен файлов
- Оптимизированное сжатие WebP с настраиваемыми параметрами
- Автоматическое создание версий для ретина-дисплеев
- Кэширование на стороне S3 на 1 год
- Обработка ошибок и валидация входных данных

## Требования к окружению
- Python 3.10+
- Docker
- S3-совместимое хранилище [Timeweb Cloud](https://timeweb.cloud/r/mo45)

## Зависимости
- Flask (веб-сервер)
- Pillow (обработка изображений)
- Boto3 (работа с S3)
- Gunicorn (WSGI-сервер)