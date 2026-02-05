from app import db, app, User, Video, Homework, HomeworkResult
import os

def reset_database():
    with app.app_context():
        # Удаляем файл базы данных если он существует
        if os.path.exists('instance/school.db'):
            os.remove('instance/school.db')
            print("Старая база данных удалена")
        
        # Создаем все таблицы заново
        db.create_all()
        
        # Создаем тестового учителя
        from flask_bcrypt import Bcrypt
        bcrypt = Bcrypt(app)
        
        hashed_password = bcrypt.generate_password_hash('teacher123').decode('utf-8')
        teacher = User(username='teacher', email='teacher@school.ru', password=hashed_password, role='teacher')
        db.session.add(teacher)
        db.session.commit()
        
        print("База данных пересоздана успешно!")
        print("Логин учителя: teacher / teacher123")

if __name__ == '__main__':
    reset_database()