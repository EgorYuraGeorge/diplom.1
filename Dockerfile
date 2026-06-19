# используется официальный облегчённый образ Python 3.11
FROM python:3.11-slim

# задаётся рабочая директория внутри контейнера
WORKDIR /app

# копируется файл зависимостей
COPY requirements.txt .

# устанавливаются все необходимые библиотеки проекта
RUN pip install --no-cache-dir -r requirements.txt

# копируется исходный код приложения
COPY . .

# создаются каталоги для хранения пользовательских файлов
RUN mkdir -p uploads \
    && mkdir -p uploads/videos \
    && mkdir -p uploads/homeworks \
    && mkdir -p uploads/answers \
    && mkdir -p uploads/chat_files

# открывается сетевой порт приложения
EXPOSE 5000

# запускается основной файл Flask-приложения
CMD ["python", "app.py"]