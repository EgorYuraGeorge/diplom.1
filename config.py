import os

class Config:
    # Секретный ключ из переменной окружения или значение по умолчанию для разработки
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # База данных
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Папка для загрузок
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    # Ограничения
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    
    # Допустимые расширения
    ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
    ALLOWED_HOMEWORK_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'zip', 'rar', 'png', 'jpg', 'jpeg'}
    
    # Режим отладки (для продакшена должен быть False)
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = True

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False