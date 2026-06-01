import os
from app import app, db, User, bcrypt

def init_db():
    """Создаёт базу данных и тестовых пользователей"""
    
    with app.app_context():
        # Путь к базе данных
        db_path = 'instance/site.db'
        
        # Если база уже существует, удаляем её
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"🗑️ Старая база данных удалена: {db_path}")
        
        # Создаём все таблицы заново
        db.create_all()
        print("✅ Таблицы созданы")
        
        # Создаём учителя
        hashed = bcrypt.generate_password_hash('teacher123').decode('utf-8')
        teacher = User(
            username='teacher',
            email='teacher@school.ru',
            password=hashed,
            role='teacher'
        )
        db.session.add(teacher)
        
        # Создаём тестового ученика
        hashed = bcrypt.generate_password_hash('student123').decode('utf-8')
        student = User(
            username='student',
            email='student@school.ru',
            password=hashed,
            role='student'
        )
        db.session.add(student)
        
        # Сохраняем в базу
        db.session.commit()
        
        print("✅ Пользователи созданы:")
        print("   👨‍🏫 Учитель: teacher / teacher123")
        print("   👩‍🎓 Ученик: student / student123")
        print(f"\n📁 База данных: {db_path}")

if __name__ == '__main__':
    init_db()