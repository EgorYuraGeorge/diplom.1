import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from werkzeug.utils import secure_filename
import config

app = Flask(__name__)
app.config.from_object(config.Config)

# папки для загрузок
try:
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'homeworks'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'videos'), exist_ok=True)
    print("Upload directories created successfully")
except FileExistsError:
  
    pass
except Exception as e:
    print(f"Warning: {e}")

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Модели базы данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    video_url = db.Column(db.String(500), nullable=False)
    video_type = db.Column(db.String(20), nullable=False, default='youtube')
    subject = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    video_filename = db.Column(db.String(200))  
    video_file_path = db.Column(db.String(200))  
    teacher = db.relationship('User', backref=db.backref('videos', lazy=True))

class Homework(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    subject = db.Column(db.String(20), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime)
    max_points = db.Column(db.Integer, default=100)
    file_path = db.Column(db.String(200))
    file_name = db.Column(db.String(200))
    teacher = db.relationship('User', backref=db.backref('homeworks', lazy=True))

class HomeworkResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    homework_id = db.Column(db.Integer, db.ForeignKey('homework.id'), nullable=False)
    answer = db.Column(db.Text)
    grade = db.Column(db.Integer)
    teacher_comment = db.Column(db.Text)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(200))
    file_name = db.Column(db.String(200))
    student = db.relationship('User', backref=db.backref('homework_results', lazy=True))
    homework = db.relationship('Homework', backref=db.backref('results', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_HOMEWORK_EXTENSIONS']

# проверка видеофайлов
def allowed_video_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_VIDEO_EXTENSIONS']

# Создаем таблицы и тестового учителя
with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='teacher').first():
        hashed_password = bcrypt.generate_password_hash('teacher123').decode('utf-8')
        teacher = User(username='teacher', email='teacher@school.ru', password=hashed_password, role='teacher')
        db.session.add(teacher)
        db.session.commit()

# Главная страница
@app.route('/')
def index():
    videos_count = Video.query.count()
    homeworks_count = Homework.query.count()
    students_count = User.query.filter_by(role='student').count()
    
    return render_template('index.html', 
                         videos=videos_count,
                         homeworks=homeworks_count,
                         students=students_count)

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form.get('role', 'student')
        
        if password != confirm_password:
            flash('Пароли не совпадают!', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Это имя пользователя уже занято!', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Этот email уже используется!', 'error')
            return redirect(url_for('register'))
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь войдите в систему.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            if user.role == 'teacher':
                return redirect(next_page) if next_page else redirect(url_for('teacher_dashboard'))
            else:
                return redirect(next_page) if next_page else redirect(url_for('videos'))
        else:
            flash('Неверное имя пользователя или пароль!', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

# Выход
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Панель учителя
@app.route('/teacher')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('index'))
    
    # Динамические счетчики
    videos_count = Video.query.filter_by(teacher_id=current_user.id).count()
    homeworks_count = Homework.query.filter_by(teacher_id=current_user.id).count()
    students_count = User.query.filter_by(role='student').count()
    submitted_works = HomeworkResult.query.join(Homework).filter(
        Homework.teacher_id == current_user.id
    ).count()
    
    # Последние активности
    recent_activities = HomeworkResult.query.join(Homework).filter(
        Homework.teacher_id == current_user.id
    ).order_by(HomeworkResult.date_submitted.desc()).limit(5).all()
    
    return render_template('teacher_dashboard.html', 
                         videos_count=videos_count,
                         homeworks_count=homeworks_count, 
                         students_count=students_count,
                         submitted_works=submitted_works,
                         recent_activities=recent_activities)

# Добавление видео
@app.route('/teacher/add_video', methods=['GET', 'POST'])
@login_required
def add_video():
    if current_user.role != 'teacher':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form['title']
        video_url = request.form.get('video_url', '')
        subject = request.form['subject']
        description = request.form['description']
        video_type = request.form['video_type']
        
        processed_url = video_url
        video_filename = None
        video_file_path = None
        
        # Обработка загрузки видеофайла
        if 'video_file' in request.files:
            file = request.files['video_file']
            if file and file.filename != '' and allowed_video_file(file.filename):
                filename = secure_filename(file.filename)
                video_filename = filename
                
               
                videos_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'videos')
                os.makedirs(videos_dir, exist_ok=True)
                
                video_file_path = os.path.join('videos', f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}")
                full_path = os.path.join(app.config['UPLOAD_FOLDER'], video_file_path)
                
                file.save(full_path)
                video_type = 'uploaded'
                processed_url = url_for('static', filename=f'uploads/{video_file_path}', _external=True)
        
        # Если не загружен файл, обрабатываем ссылку
        elif video_url:
            if video_type == 'youtube':
                if 'youtube.com/watch?v=' in video_url:
                    video_id = video_url.split('v=')[1].split('&')[0]
                    processed_url = f'https://www.youtube.com/embed/{video_id}'
                elif 'youtu.be/' in video_url:
                    video_id = video_url.split('youtu.be/')[1].split('?')[0]
                    processed_url = f'https://www.youtube.com/embed/{video_id}'
            elif video_type == 'vimeo':
                if 'vimeo.com/' in video_url:
                    video_id = video_url.split('vimeo.com/')[1].split('/')[-1]
                    processed_url = f'https://player.vimeo.com/video/{video_id}'
        else:
            flash('Пожалуйста, либо загрузите видеофайл, либо укажите ссылку', 'error')
            return redirect(url_for('add_video'))
        
        new_video = Video(
            title=title, 
            video_url=processed_url, 
            subject=subject, 
            description=description,
            video_type=video_type,
            teacher_id=current_user.id,
            video_filename=video_filename,
            video_file_path=video_file_path
        )
        db.session.add(new_video)
        db.session.commit()
        
        flash('Видео успешно добавлено!', 'success')
        return redirect(url_for('videos'))
    
    return render_template('add_video.html')

# Удаление видео
@app.route('/teacher/delete_video/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    if current_user.role != 'teacher':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('index'))
    
    video = Video.query.get_or_404(video_id)
    
    # Проверяем,  видео принадлежит  учителю
    if video.teacher_id != current_user.id:
        flash('Вы можете удалять только свои видео!', 'error')
        return redirect(url_for('videos'))
    
   
    try:
        # Если это загруженный файл и есть путь к файлу
        if (hasattr(video, 'video_type') and video.video_type == 'uploaded' and 
            hasattr(video, 'video_file_path') and video.video_file_path):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], video.video_file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
    except Exception as e:
        print(f"Ошибка при удалении файла: {e}")
    
    db.session.delete(video)
    db.session.commit()
    
    flash('Видео успешно удалено!', 'success')
    return redirect(url_for('videos'))

# Просмотр видео
@app.route('/videos')
@login_required
def videos():
    videos = Video.query.order_by(Video.date_added.desc()).all()
    return render_template('videos.html', videos=videos)

# Добавление домашнего задания
@app.route('/teacher/add_homework', methods=['GET', 'POST'])
@login_required
def add_homework():
    if current_user.role != 'teacher':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        subject = request.form['subject']
        deadline = request.form.get('deadline')
        max_points = request.form.get('max_points', 100)
        
        file_path = None
        file_name = None
        
        # Обработка загрузки файла
        if 'homework_file' in request.files:
            file = request.files['homework_file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = f"homeworks/{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_path))
                file_name = filename
        
        new_homework = Homework(
            title=title, 
            description=description, 
            subject=subject, 
            teacher_id=current_user.id,
            deadline=datetime.strptime(deadline, '%Y-%m-%d') if deadline else None,
            max_points=int(max_points),
            file_path=file_path,
            file_name=file_name
        )
        db.session.add(new_homework)
        db.session.commit()
        
        flash('Домашнее задание успешно добавлено!', 'success')
        return redirect(url_for('homeworks'))
    
    return render_template('add_homework.html')

# Скачивание файлов
@app.route('/download/<path:filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Просмотр домашних заданий
@app.route('/homeworks')
@login_required
def homeworks():
    homeworks = Homework.query.order_by(Homework.date_added.desc()).all()
    now = datetime.utcnow()
    return render_template('homeworks.html', homeworks=homeworks, now=now)

# Сдача домашнего задания
@app.route('/submit_homework/<int:homework_id>', methods=['POST'])
@login_required
def submit_homework(homework_id):
    if current_user.role != 'student':
        flash('Только ученики могут сдавать задания!', 'error')
        return redirect(url_for('homeworks'))
    
    answer = request.form.get('answer', '')
    file_path = None
    file_name = None
    
    # Обработка загрузки файла ответа
    if 'answer_file' in request.files:
        file = request.files['answer_file']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = f"answers/{current_user.id}_{homework_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_path))
            file_name = filename
    
    # Проверяем, не сдавал ли уже ученик это задание
    existing_result = HomeworkResult.query.filter_by(
        student_id=current_user.id,
        homework_id=homework_id
    ).first()
    
    if existing_result:
        flash('Вы уже сдали это задание!', 'error')
        return redirect(url_for('homeworks'))
    
    new_result = HomeworkResult(
        student_id=current_user.id,
        homework_id=homework_id,
        answer=answer,
        file_path=file_path,
        file_name=file_name
    )
    db.session.add(new_result)
    db.session.commit()
    
    flash('Задание успешно сдано на проверку!', 'success')
    return redirect(url_for('homeworks'))

# Результаты учеников
@app.route('/teacher/results')
@login_required
def results():
    if current_user.role != 'teacher':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('index'))
    
    results = HomeworkResult.query.all()
    return render_template('results.html', results=results)

# Оценка работы
@app.route('/teacher/grade_result/<int:result_id>', methods=['POST'])
@login_required
def grade_result(result_id):
    if current_user.role != 'teacher':
        flash('Доступ запрещен!', 'error')
        return redirect(url_for('index'))
    
    result = HomeworkResult.query.get_or_404(result_id)
    grade = request.form.get('grade')
    comment = request.form.get('comment', '')
    
    if grade:
        try:
            result.grade = int(grade)
            result.teacher_comment = comment
            db.session.commit()
            flash('Оценка сохранена!', 'success')
        except ValueError:
            flash('Ошибка: оценка должна быть числом', 'error')
    else:
        flash('Ошибка: введите оценку', 'error')
    
    return redirect(url_for('results'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)