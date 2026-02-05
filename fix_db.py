import os
import sqlite3
from app import app, db

def recreate_database():
    with app.app_context():
        try:
            # Удаляем таблицы
            db.drop_all()
            print("✅ Старые таблицы удалены")
            
            # Создаем новые таблицы 
            db.create_all()
            print("✅ Новые таблицы созданы")
            
            # Создаем тестового учителя
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt(app)
            from app import User
            
            # Проверяем, нет ли уже учителя
            if not User.query.filter_by(username='teacher').first():
                hashed_password = bcrypt.generate_password_hash('teacher123').decode('utf-8')
                teacher = User(username='teacher', email='teacher@school.ru', password=hashed_password, role='teacher')
                db.session.add(teacher)
                db.session.commit()
                print("✅ Тестовый учитель создан")
            else:
                print("✅ Учитель уже существует")
            
            print("\n🎯 Логин учителя: teacher / teacher123")
            print("📁 База данных успешно обновлена!")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("Попробуйте остановить сервер Flask (Ctrl+C) и запустить скрипт снова")

if __name__ == '__main__':
    recreate_database()