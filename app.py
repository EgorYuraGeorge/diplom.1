import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import json
import config

app = Flask(__name__)
app.config.from_object(config.Config)

# Настройки сессии
app.config['SECRET_KEY'] = 'your-secret-key-12345'
app.config['SESSION_PROTECTION'] = 'strong'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)

# папки для загрузок
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'homeworks'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'videos'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'answers'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'chat_files'), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ========== МОДЕЛИ ==========
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    
    def has_access_to(self, subject):
        if self.role == 'teacher':
            return True
        purchase = Purchase.query.filter_by(student_id=self.id, subject=subject, is_active=True).first()
        if purchase:
            return True
        both_purchase = Purchase.query.filter_by(student_id=self.id, subject='both', is_active=True).first()
        if both_purchase:
            return True
        return False
    
    def has_any_access(self):
        purchases = Purchase.query.filter_by(student_id=self.id, is_active=True).all()
        return len(purchases) > 0

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
    expires_at = db.Column(db.DateTime, nullable=True)
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

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    file_name = db.Column(db.String(200), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(20), nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    student = db.relationship('User', backref=db.backref('purchases', lazy=True))

# ========== ТЕСТЫ ==========
class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    subject = db.Column(db.String(20), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time_limit = db.Column(db.Integer, default=0)
    passing_score = db.Column(db.Integer, default=50)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    teacher = db.relationship('User', backref=db.backref('tests', lazy=True))
    questions = db.relationship('TestQuestion', backref='test', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('TestResult', backref='test', lazy=True, cascade='all, delete-orphan')

class TestQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='single')
    points = db.Column(db.Integer, default=1)
    order_num = db.Column(db.Integer, default=0)
    
    answers = db.relationship('TestAnswer', backref='question', lazy=True, cascade='all, delete-orphan')

class TestAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('test_question.id'), nullable=False)
    answer_text = db.Column(db.String(500), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    max_score = db.Column(db.Integer, default=0)
    percentage = db.Column(db.Integer, default=0)
    grade = db.Column(db.String(5), nullable=True)
    answers_data = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    student = db.relationship('User', backref=db.backref('test_results', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_HOMEWORK_EXTENSIONS']

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_VIDEO_EXTENSIONS']

def allowed_chat_file(filename):
    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'txt', 'zip', 'rar'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

# ========== СОЗДАНИЕ ТАБЛИЦ ==========
with app.app_context():
    db.create_all()
    
    if not User.query.filter_by(role='teacher').first():
        hashed = bcrypt.generate_password_hash('teacher123').decode('utf-8')
        teacher = User(username='teacher', email='teacher@school.ru', password=hashed, role='teacher')
        db.session.add(teacher)
        db.session.commit()
        print("✅ Учитель создан: teacher / teacher123")
    
    if not User.query.filter_by(role='student').first():
        hashed = bcrypt.generate_password_hash('student123').decode('utf-8')
        student = User(username='student', email='student@school.ru', password=hashed, role='student')
        db.session.add(student)
        db.session.commit()
        print("✅ Ученик создан: student / student123")

# ========== ОСНОВНЫЕ МАРШРУТЫ ==========
@app.route('/')
def index():
    students_list = []
    teacher_data = None
    if current_user.is_authenticated:
        if current_user.role == 'teacher':
            students_list = User.query.filter_by(role='student').all()
        else:
            teacher_data = User.query.filter_by(role='teacher').first()
    
    return render_template('index.html', 
                         videos=Video.query.count(),
                         homeworks=Homework.query.count(),
                         students=User.query.filter_by(role='student').count(),
                         students_list=students_list,
                         teacher_data=teacher_data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']
        role = request.form.get('role', 'student')
        
        if password != confirm:
            flash('Пароли не совпадают!', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Имя занято!', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email занят!', 'error')
            return redirect(url_for('register'))
        
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed, role=role)
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            session.clear()
            login_user(user, remember=True, force=True)
            if user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('videos'))
        else:
            flash('Неверный логин или пароль!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('index'))

@app.route('/teacher')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))
    
    students_list = User.query.filter_by(role='student').all()
    
    videos_count = Video.query.filter_by(teacher_id=current_user.id).count()
    homeworks_count = Homework.query.filter_by(teacher_id=current_user.id).count()
    students_count = len(students_list)
    submitted_works = HomeworkResult.query.join(Homework).filter(Homework.teacher_id == current_user.id).count()
    
    recent_activities = HomeworkResult.query.join(Homework).filter(
        Homework.teacher_id == current_user.id
    ).order_by(HomeworkResult.date_submitted.desc()).limit(5).all()
    
    return render_template('teacher_dashboard.html',
                         videos_count=videos_count,
                         homeworks_count=homeworks_count,
                         students_count=students_count,
                         submitted_works=submitted_works,
                         recent_activities=recent_activities,
                         students_list=students_list,
                         teacher_data=None)

@app.route('/videos')
@login_required
def videos():
    students_list = []
    teacher_data = None
    if current_user.role == 'teacher':
        students_list = User.query.filter_by(role='student').all()
    else:
        teacher_data = User.query.filter_by(role='teacher').first()
    
    return render_template('videos.html',
                         videos=Video.query.order_by(Video.date_added.desc()).all(),
                         students_list=students_list,
                         teacher_data=teacher_data)

@app.route('/homeworks')
@login_required
def homeworks():
    students_list = []
    teacher_data = None
    submitted_ids = []
    
    if current_user.role == 'teacher':
        homeworks_list = Homework.query.order_by(Homework.date_added.desc()).all()
        students_list = User.query.filter_by(role='student').all()
    else:
        all_homeworks = Homework.query.order_by(Homework.date_added.desc()).all()
        homeworks_list = []
        for homework in all_homeworks:
            if current_user.has_access_to(homework.subject):
                homeworks_list.append(homework)
        teacher_data = User.query.filter_by(role='teacher').first()
        
        submitted_results = HomeworkResult.query.filter_by(student_id=current_user.id).all()
        submitted_ids = [r.homework_id for r in submitted_results]
    
    return render_template('homeworks.html',
                         homeworks=homeworks_list,
                         now=datetime.utcnow(),
                         submitted_ids=submitted_ids,
                         students_list=students_list,
                         teacher_data=teacher_data)

@app.route('/teacher/add_homework', methods=['GET', 'POST'])
@login_required
def add_homework():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
    
    students_list = User.query.filter_by(role='student').all()
    teacher_data = None
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        subject = request.form['subject']
        deadline = request.form.get('deadline')
        max_points = request.form.get('max_points', 100)
        auto_delete = request.form.get('auto_delete')
        
        expires_at = None
        if auto_delete:
            expires_at = datetime.utcnow() + timedelta(days=int(auto_delete))
        
        file_path = None
        file_name = None
        
        if 'homework_file' in request.files:
            file = request.files['homework_file']
            if file and file.filename:
                filename = secure_filename(file.filename)
                unique = f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                file_path = os.path.join('homeworks', unique)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_path))
                file_name = filename
        
        hw = Homework(title=title, description=description, subject=subject, teacher_id=current_user.id,
                     deadline=datetime.strptime(deadline, '%Y-%m-%d') if deadline else None,
                     expires_at=expires_at,
                     max_points=int(max_points), file_path=file_path, file_name=file_name)
        db.session.add(hw)
        db.session.commit()
        flash('Задание добавлено!', 'success')
        return redirect(url_for('homeworks'))
    
    return render_template('add_homework.html', students_list=students_list, teacher_data=teacher_data)

@app.route('/submit_homework/<int:homework_id>', methods=['POST'])
@login_required
def submit_homework(homework_id):
    if current_user.role != 'student':
        flash('Только ученики могут сдавать задания!', 'error')
        return redirect(url_for('homeworks'))
    
    homework = Homework.query.get_or_404(homework_id)
    if not current_user.has_access_to(homework.subject):
        flash('У вас нет доступа к этому заданию!', 'error')
        return redirect(url_for('homeworks'))
    
    existing = HomeworkResult.query.filter_by(student_id=current_user.id, homework_id=homework_id).first()
    if existing:
        flash('Вы уже сдали это задание! Изменить ответ нельзя.', 'error')
        return redirect(url_for('homeworks'))
    
    answer = request.form.get('answer', '')
    file_path = None
    file_name = None
    
    if 'answer_file' in request.files:
        file = request.files['answer_file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            unique = f"{current_user.id}_{homework_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
            file_path = os.path.join('answers', unique)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file_path))
            file_name = filename
    
    result = HomeworkResult(
        student_id=current_user.id, 
        homework_id=homework_id, 
        answer=answer, 
        file_path=file_path, 
        file_name=file_name
    )
    db.session.add(result)
    db.session.commit()
    
    flash('Задание успешно сдано! Изменить ответ будет нельзя.', 'success')
    return redirect(url_for('homeworks'))

@app.route('/teacher/results')
@login_required
def results():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
    
    students_list = User.query.filter_by(role='student').all()
    teacher_data = None
    results = HomeworkResult.query.order_by(HomeworkResult.date_submitted.desc()).all()
    
    return render_template('results.html', 
                         results=results,
                         students_list=students_list,
                         teacher_data=teacher_data)

@app.route('/teacher/grade_result/<int:result_id>', methods=['POST'])
@login_required
def grade_result(result_id):
    result = HomeworkResult.query.get_or_404(result_id)
    grade = request.form.get('grade')
    comment = request.form.get('comment', '')
    
    if grade:
        result.grade = int(grade)
        result.teacher_comment = comment
        db.session.commit()
        flash('Оценка сохранена!', 'success')
    
    return redirect(url_for('results'))

@app.route('/download/<path:filename>')
@login_required
def download_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            flash('Файл не найден', 'error')
            return redirect(request.referrer or url_for('homeworks'))
        
        return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), as_attachment=True)
    except Exception as e:
        print(f"Ошибка скачивания: {e}")
        flash('Ошибка при скачивании файла', 'error')
        return redirect(request.referrer or url_for('homeworks'))

@app.route('/teacher/delete_homework/<int:homework_id>', methods=['POST'])
@login_required
def delete_homework_route(homework_id):
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
    
    homework = Homework.query.get_or_404(homework_id)
    HomeworkResult.query.filter_by(homework_id=homework_id).delete()
    db.session.delete(homework)
    db.session.commit()
    flash('Задание удалено!', 'success')
    return redirect(url_for('homeworks'))

# ========== ВИДЕО МАРШРУТЫ ==========
@app.route('/teacher/add_video', methods=['GET', 'POST'])
@login_required
def add_video():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
    
    students_list = User.query.filter_by(role='student').all()
    teacher_data = None
    
    if request.method == 'POST':
        title = request.form['title']
        subject = request.form['subject']
        description = request.form['description']
        
        if request.form.get('input_method') == 'upload':
            file = request.files['video_file']
            if file and allowed_video_file(file.filename):
                filename = secure_filename(file.filename)
                unique = f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
                path = os.path.join('videos', unique)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], path))
                
                video = Video(title=title, video_url=path, video_type='uploaded', subject=subject, 
                            description=description, teacher_id=current_user.id, video_filename=filename, video_file_path=path)
                db.session.add(video)
                db.session.commit()
                flash('Видео добавлено!', 'success')
                return redirect(url_for('videos'))
        else:
            url = request.form['video_url']
            if 'youtube.com/watch?v=' in url:
                vid = url.split('v=')[1].split('&')[0]
                embed = f'https://www.youtube.com/embed/{vid}'
            elif 'youtu.be/' in url:
                vid = url.split('youtu.be/')[1].split('?')[0]
                embed = f'https://www.youtube.com/embed/{vid}'
            else:
                embed = url
            
            video = Video(title=title, video_url=embed, video_type='youtube', subject=subject, 
                        description=description, teacher_id=current_user.id)
            db.session.add(video)
            db.session.commit()
            flash('Видео добавлено!', 'success')
            return redirect(url_for('videos'))
    
    return render_template('add_video.html', students_list=students_list, teacher_data=teacher_data)

@app.route('/teacher/delete_video/<int:video_id>', methods=['POST'])
@login_required
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)
    if video.teacher_id == current_user.id:
        db.session.delete(video)
        db.session.commit()
        flash('Видео удалено!', 'success')
    return redirect(url_for('videos'))

# ========== ПОКУПКИ ==========
@app.route('/purchase')
@login_required
def purchase():
    if current_user.role != 'student':
        flash('Доступ только для учеников', 'error')
        return redirect(url_for('index'))
    
    purchases = Purchase.query.filter_by(student_id=current_user.id, is_active=True).all()
    students_list = []
    teacher_data = User.query.filter_by(role='teacher').first()
    
    return render_template('purchase.html', 
                         purchases=purchases,
                         students_list=students_list,
                         teacher_data=teacher_data)

@app.route('/purchase_subject', methods=['POST'])
@login_required
def purchase_subject():
    if current_user.role != 'student':
        flash('Доступ только для учеников', 'error')
        return redirect(url_for('index'))
    
    subject = request.form.get('subject')
    
    existing = Purchase.query.filter_by(student_id=current_user.id, subject=subject, is_active=True).first()
    if existing:
        flash('У вас уже есть доступ к этому предмету!', 'warning')
        return redirect(url_for('videos'))
    
    purchase = Purchase(student_id=current_user.id, subject=subject)
    db.session.add(purchase)
    db.session.commit()
    
    subject_name = "Химии" if subject == "chemistry" else "Биологии" if subject == "biology" else "полному пакету"
    flash(f'Доступ к {subject_name} успешно куплен!', 'success')
    return redirect(url_for('videos'))

# ========== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ==========
@app.route('/teacher/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))
    
    user_to_delete = User.query.get_or_404(user_id)
    
    if user_to_delete.role == 'teacher':
        flash('Нельзя удалить учителя!', 'error')
        return redirect(url_for('teacher_dashboard'))
    
    Message.query.filter((Message.sender_id == user_id) | (Message.receiver_id == user_id)).delete()
    Purchase.query.filter_by(student_id=user_id).delete()
    TestResult.query.filter_by(student_id=user_id).delete()
    HomeworkResult.query.filter_by(student_id=user_id).delete()
    
    db.session.delete(user_to_delete)
    db.session.commit()
    
    flash(f'Пользователь {user_to_delete.username} удален!', 'success')
    return redirect(url_for('teacher_dashboard'))

# ========== ЧАТ API ==========
@app.route('/api/upload_chat_file', methods=['POST'])
@login_required
def upload_chat_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Нет файла'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Нет файла'}), 400
    
    if file and allowed_chat_file(file.filename):
        filename = secure_filename(file.filename)
        unique = f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
        path = os.path.join('chat_files', unique)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], path))
        
        file_url = f"/static/uploads/{path}"
        return jsonify({'status': 'success', 'file_path': file_url, 'file_name': filename})
    
    return jsonify({'error': 'Неподдерживаемый формат'}), 400

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Нет данных'}), 400
        
        receiver_id = data.get('receiver_id')
        message = data.get('message', '').strip()
        file_path = data.get('file_path', '')
        file_name = data.get('file_name', '')
        
        if not message and not file_path:
            return jsonify({'error': 'Пустое сообщение'}), 400
        
        if not receiver_id:
            return jsonify({'error': 'Не указан получатель'}), 400
        
        msg = Message(
            sender_id=current_user.id,
            receiver_id=receiver_id,
            message=message if message else None,
            file_path=file_path if file_path else None,
            file_name=file_name if file_name else None
        )
        db.session.add(msg)
        db.session.commit()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        print("Ошибка send_message:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_messages/<int:user_id>')
@login_required
def get_messages(user_id):
    try:
        messages = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
            ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.created_at).all()
        
        result = []
        for m in messages:
            moscow_time = m.created_at + timedelta(hours=3)
            
            result.append({
                'id': m.id,
                'message': m.message or '',
                'file_path': m.file_path or '',
                'file_name': m.file_name or '',
                'created_at': moscow_time.strftime('%d.%m.%Y %H:%M'),
                'is_me': m.sender_id == current_user.id,
                'sender_id': m.sender_id,
                'sender_name': m.sender.username
            })
        
        return jsonify(result)
    except Exception as e:
        print("Ошибка get_messages:", e)
        return jsonify([]), 500

@app.route('/api/delete_message/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    try:
        message = Message.query.get_or_404(message_id)
        
        if current_user.role == 'teacher' or message.sender_id == current_user.id:
            db.session.delete(message)
            db.session.commit()
            return jsonify({'status': 'success'})
        
        return jsonify({'error': 'Нет прав для удаления'}), 403
    except Exception as e:
        print("Ошибка delete_message:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/api/edit_message/<int:message_id>', methods=['PUT'])
@login_required
def edit_message(message_id):
    try:
        message = Message.query.get_or_404(message_id)
        
        if message.sender_id != current_user.id:
            return jsonify({'error': 'Нет прав для редактирования'}), 403
        
        data = request.get_json()
        new_message = data.get('message', '').strip()
        
        if not new_message:
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400
        
        message.message = new_message
        db.session.commit()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/unread_count')
@login_required
def unread_count():
    try:
        count = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
        
        if current_user.role == 'teacher':
            unread_messages = Message.query.filter_by(receiver_id=current_user.id, is_read=False).all()
            senders = {}
            for msg in unread_messages:
                if msg.sender_id not in senders:
                    senders[msg.sender_id] = msg.sender.username
            result_senders = [{'id': k, 'name': v} for k, v in senders.items()]
            return jsonify({'count': count, 'senders': result_senders})
        
        return jsonify({'count': count})
    except Exception as e:
        return jsonify({'count': 0})

@app.route('/api/mark_as_read/<int:sender_id>', methods=['POST'])
@login_required
def mark_as_read(sender_id):
    try:
        Message.query.filter_by(sender_id=sender_id, receiver_id=current_user.id, is_read=False).update({'is_read': True})
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== ТЕСТЫ ==========
@app.route('/tests')
@login_required
def tests():
    students_list = []
    teacher_data = None
    
    if current_user.role == 'teacher':
        tests_list = Test.query.filter_by(teacher_id=current_user.id).order_by(Test.created_at.desc()).all()
        students_list = User.query.filter_by(role='student').all()
    else:
        all_tests = Test.query.filter_by(is_active=True).order_by(Test.created_at.desc()).all()
        tests_list = []
        for test in all_tests:
            if current_user.has_access_to(test.subject):
                tests_list.append(test)
        teacher_data = User.query.filter_by(role='teacher').first()
    
    return render_template('tests.html', 
                         tests=tests_list, 
                         students_list=students_list, 
                         teacher_data=teacher_data)

@app.route('/teacher/add_test', methods=['GET', 'POST'])
@login_required
def add_test():
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))
    
    students_list = User.query.filter_by(role='student').all()
    teacher_data = None
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        subject = request.form['subject']
        time_limit = int(request.form.get('time_limit', 0))
        passing_score = int(request.form.get('passing_score', 50))
        auto_delete = request.form.get('auto_delete')
        
        expires_at = None
        if auto_delete:
            expires_at = datetime.utcnow() + timedelta(days=int(auto_delete))
        
        test = Test(
            title=title,
            description=description,
            subject=subject,
            teacher_id=current_user.id,
            time_limit=time_limit,
            passing_score=passing_score,
            expires_at=expires_at
        )
        db.session.add(test)
        db.session.commit()
        
        for key, value in request.form.items():
            if key.endswith('_text'):
                q_num = key.split('_')[1]
                question_text = value
                points = int(request.form.get(f'question_{q_num}_points', 1))
                question_type = request.form.get(f'question_{q_num}_type', 'single')
                
                question = TestQuestion(
                    test_id=test.id,
                    question_text=question_text,
                    points=points,
                    question_type=question_type
                )
                db.session.add(question)
                db.session.commit()
                
                for ans_key, ans_value in request.form.items():
                    if ans_key.startswith(f'question_{q_num}_answer_') and not ans_key.endswith('correct'):
                        ans_num = ans_key.split('_')[-1]
                        is_correct = request.form.get(f'question_{q_num}_correct_{ans_num}') == 'on'
                        
                        answer = TestAnswer(
                            question_id=question.id,
                            answer_text=ans_value,
                            is_correct=is_correct
                        )
                        db.session.add(answer)
                db.session.commit()
        
        flash('Тест успешно создан!', 'success')
        return redirect(url_for('tests'))
    
    return render_template('add_test.html', 
                         students_list=students_list, 
                         teacher_data=teacher_data)

@app.route('/take_test/<int:test_id>', methods=['GET', 'POST'])
@login_required
def take_test(test_id):
    if current_user.role != 'student':
        flash('Доступ только для учеников', 'error')
        return redirect(url_for('index'))
    
    test = Test.query.get_or_404(test_id)
    existing_result = TestResult.query.filter_by(test_id=test_id, student_id=current_user.id, completed_at=None).first()
    
    students_list = []
    teacher_data = User.query.filter_by(role='teacher').first()
    
    if request.method == 'POST':
        if not existing_result:
            max_score = sum(q.points for q in test.questions)
            existing_result = TestResult(test_id=test_id, student_id=current_user.id, max_score=max_score)
            db.session.add(existing_result)
            db.session.commit()
        
        score = 0
        answers_data = {}
        
        for question in test.questions:
            if question.question_type == 'multiple':
                user_answers = request.form.getlist(f'q{question.id}')
                correct_answers = [a.id for a in question.answers if a.is_correct]
                
                user_set = set()
                for a in user_answers:
                    try:
                        user_set.add(int(a))
                    except ValueError:
                        pass
                
                correct_set = set(correct_answers)
                
                if len(correct_set) > 0:
                    if user_set and user_set == correct_set:
                        score += question.points
                    elif user_set:
                        correct_count = len(user_set.intersection(correct_set))
                        score += question.points * correct_count // len(correct_set)
                
                answers_data[str(question.id)] = ','.join(user_answers)
            else:
                user_answer = request.form.get(f'q{question.id}')
                if user_answer:
                    try:
                        answer = TestAnswer.query.get(int(user_answer))
                        if answer and answer.is_correct:
                            score += question.points
                    except:
                        pass
                    answers_data[str(question.id)] = user_answer
        
        percentage = 0
        if existing_result.max_score > 0:
            percentage = int((score / existing_result.max_score) * 100)
        
        if percentage >= 85:
            grade = '5'
        elif percentage >= 70:
            grade = '4'
        elif percentage >= 50:
            grade = '3'
        else:
            grade = '2'
        
        existing_result.score = score
        existing_result.percentage = percentage
        existing_result.grade = grade
        existing_result.answers_data = json.dumps(answers_data)
        existing_result.completed_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'Тест завершен! Результат: {score}/{existing_result.max_score} ({percentage}%) - Оценка: {grade}', 'success')
        return redirect(url_for('tests'))
    
    return render_template('take_test.html', 
                         test=test, 
                         students_list=students_list, 
                         teacher_data=teacher_data)

@app.route('/test_results/<int:test_id>')
@login_required
def test_results(test_id):
    if current_user.role != 'teacher':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('index'))
    
    test = Test.query.get_or_404(test_id)
    results = TestResult.query.filter_by(test_id=test_id).all()
    completed_results = [r for r in results if r.completed_at]
    avg_score = sum(r.percentage for r in completed_results) // len(completed_results) if completed_results else 0
    
    students_list = User.query.filter_by(role='student').all()
    teacher_data = None
    
    return render_template('test_results.html', 
                         test=test, 
                         results=completed_results, 
                         avg_score=avg_score,
                         students_list=students_list,
                         teacher_data=teacher_data)

@app.route('/teacher/delete_test/<int:test_id>', methods=['POST'])
@login_required
def delete_test(test_id):
    if current_user.role != 'teacher':
        return redirect(url_for('index'))
    
    test = Test.query.get_or_404(test_id)
    TestResult.query.filter_by(test_id=test_id).delete()
    db.session.delete(test)
    db.session.commit()
    
    flash('Тест и все результаты удалены', 'success')
    return redirect(url_for('tests'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)