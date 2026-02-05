import os

class Config:
    # Секретный ключ для защиты 
    SECRET_KEY = 'your-very-secret-key-12345-change-this-in-production'
    
    # Настройки базы данных
    SQLALCHEMY_DATABASE_URI = 'sqlite:///school.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Папка для загрузки файлов
    UPLOAD_FOLDER = 'static/uploads'
    
    # Максимальный размер файла (500MB)
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024
    
    # Разрешенные расширения для домашних заданий
    ALLOWED_HOMEWORK_EXTENSIONS = {
        'pdf', 'doc', 'docx', 'txt', 
        'zip', 'rar', 'jpg', 'jpeg', 
        'png', 'gif'
    }
    
    # Разрешенные расширения для видеофайлов
    ALLOWED_VIDEO_EXTENSIONS = {
        'mp4', 'mov', 'avi', 'mkv', 
        'webm', 'flv', 'wmv', 'm4v',
        '3gp', 'ogg'
    }