from app import app, db
import os

def update_database():
    with app.app_context():
        try:
            print("🔄 Обновляем базу данных...")
            
            # Удаляем все таблицы
            db.drop_all()
            print("✅ Старые таблицы удалены")
            
            # Создаем таблицы с новой структурой
            db.create_all()
            print("✅ Новые таблицы созданы")
            
            # Создаем тестового учителя
            from flask_bcrypt import Bcrypt
            from app import User
            
            bcrypt = Bcrypt(app)
            hashed_password = bcrypt.generate_password_hash('teacher123').decode('utf-8')
            teacher = User(username='teacher', email='teacher@school.ru', password=hashed_password, role='teacher')
            db.session.add(teacher)
            db.session.commit()
            
            print("✅ Тестовый учитель создан")
            print("\n🎯 Логин учителя: teacher / teacher123")
            print("📁 База данных успешно обновлена!")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    update_database()