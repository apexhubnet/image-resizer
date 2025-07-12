import os
import hashlib
import uuid
from io import BytesIO
from flask import Flask, request, jsonify
from PIL import Image
import boto3
from botocore.client import Config

app = Flask(__name__)

# Конфигурация S3 из переменных окружения
S3_BUCKET = os.getenv('S3_BUCKET')
S3_ENDPOINT = os.getenv('S3_ENDPOINT')
S3_REGION = os.getenv('S3_REGION', 'ru-1')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY')
WEBP_QUALITY = int(os.getenv('WEBP_QUALITY', 85))
WEBP_METHOD = int(os.getenv('WEBP_METHOD', 6))

# Инициализация клиента S3 для TimeWeb Cloud
s3 = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    region_name=S3_REGION,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    config=Config(signature_version='s3v4')
)

def generate_hash():
    """Генерация уникального 24-символьного хеша"""
    random_bytes = uuid.uuid4().bytes + os.urandom(16)
    return hashlib.sha256(random_bytes).hexdigest()[:24]

def resize_image(image, target_size):
    """Ресайз изображения с сохранением пропорций"""
    img = Image.open(image)
    
    # Рассчет новых размеров с сохранением пропорций
    original_width, original_height = img.size
    target_width, target_height = target_size
    
    ratio = min(
        target_width / original_width,
        target_height / original_height
    )
    new_size = (
        int(original_width * ratio),
        int(original_height * ratio)
    )
    
    img = img.resize(new_size, Image.LANCZOS)
    
    # Создание нового изображения с альфа-каналом
    result = Image.new('RGBA', target_size, (0, 0, 0, 0))
    offset = (
        (target_size[0] - new_size[0]) // 2,
        (target_size[1] - new_size[1]) // 2
    )
    result.paste(img, offset)
    
    return result

def resize_to_width(image, target_width):
    """Ресайз изображения по ширине с сохранением пропорций"""
    img = Image.open(image)
    
    # Рассчет новой высоты на основе пропорций
    original_width, original_height = img.size
    ratio = target_width / original_width
    new_height = int(original_height * ratio)
    
    # Изменение размера изображения
    img = img.resize((target_width, new_height), Image.LANCZOS)
    
    return img

def process_upload(file, sizes):
    """Обработка загрузки файла с заданными размерами"""
    if file.filename == '':
        return None, "Empty filename"
    
    unique_hash = generate_hash()
    image_bytes = file.read()
    
    for suffix, dimensions in sizes.items():
        # Проверяем тип размеров - кортеж (width, height) или только width
        if isinstance(dimensions, tuple):
            img = resize_image(BytesIO(image_bytes), dimensions)
        else:
            img = resize_to_width(BytesIO(image_bytes), dimensions)
        
        buffer = BytesIO()
        # Сохранение в формате WebP с оптимизацией
        img.save(buffer, format='WEBP', quality=WEBP_QUALITY, method=WEBP_METHOD)
        buffer.seek(0)
        
        # Используем put_object для загрузки с кэшированием
        s3_key = f"images/{unique_hash}{suffix}.webp"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=buffer.getvalue(),
            ContentType='image/webp',
            CacheControl='max-age=31536000'  # Кэшировать на 1 год
        )
    
    return unique_hash, None

def process_original_upload(file):
    """Обработка загрузки оригинального файла без изменения размеров"""
    if file.filename == '':
        return None, "Empty filename"
    
    unique_hash = generate_hash()
    image_bytes = file.read()
    
    # Открываем изображение
    img = Image.open(BytesIO(image_bytes))
    
    # Конвертируем в WebP
    buffer = BytesIO()
    img.save(buffer, format='WEBP', quality=WEBP_QUALITY, method=WEBP_METHOD)
    buffer.seek(0)
    
    # Загружаем на S3 с кэшированием
    s3_key = f"images/{unique_hash}.webp"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=buffer.getvalue(),
        ContentType='image/webp',
        CacheControl='max-age=31536000'  # Кэшировать на 1 год
    )
    
    return unique_hash, None

# Конфигурации для разных эндпоинтов
SIZES_CONFIG = {
    '64': {
        '': (64, 64),
        '@2x': (128, 128),
        '@3x': (185, 185),
        '@4x': (256, 256)
    },
    '80': {
        '': (80, 80),
        '@2x': (120, 120)
    },
    '100': {
        '': 100,
        '@2x': 200,
        '@3x': 600
    },
    '158': {
        '': (158, 158),
        '@2x': (316, 316),
        '@3x': (474, 474)
    },
    '400': {
        '': 400,
        '@2x': 800,
        '@3x': 1200
    },
    '600': {
        '': 600,
        '@2x': 1200,
        '@3x': 1800
    }
}

@app.route('/64', methods=['POST'])
def upload_64():
    return handle_upload('64')

@app.route('/80', methods=['POST'])
def upload_80():
    return handle_upload('80')

@app.route('/100', methods=['POST'])
def upload_100():
    return handle_upload('100')

@app.route('/158', methods=['POST'])
def upload_158():
    return handle_upload('158')

@app.route('/400', methods=['POST'])
def upload_400():
    return handle_upload('400')

@app.route('/600', methods=['POST'])
def upload_600():
    return handle_upload('600')

@app.route('/upload', methods=['POST'])
def upload_original():
    """Эндпоинт для загрузки оригинального изображения без изменения размеров"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    unique_hash, error = process_original_upload(file)
    
    if error:
        return jsonify({"error": error}), 400
    
    return jsonify({
        "hash": unique_hash,
        "endpoint": "original",
        "format": "webp"
    }), 200

def handle_upload(endpoint_type):
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    sizes = SIZES_CONFIG.get(endpoint_type, {})
    
    if not sizes:
        return jsonify({"error": "Invalid endpoint configuration"}), 500
    
    unique_hash, error = process_upload(file, sizes)
    
    if error:
        return jsonify({"error": error}), 400
    
    return jsonify({
        "hash": unique_hash,
        "endpoint": endpoint_type,
        "sizes": list(sizes.keys()),
        "format": "webp"
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)