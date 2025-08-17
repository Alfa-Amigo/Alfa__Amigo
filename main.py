from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g
from datetime import datetime
import json
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_por_defecto_para_desarrollo')

# Configuración para Render
app.config.update(
    DATABASE=os.path.join(os.path.dirname(__file__), 'app.db'),
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600  # 1 hora en segundos
)

# Conexión a la base de datos
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

# Decorador para rutas protegidas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Inicialización de la base de datos
def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                xp INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                last_login DATE
            )
        ''')
        
        # Tabla de lecciones completadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS completed_lessons (
                user_id INTEGER,
                lesson_id INTEGER,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                score INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                PRIMARY KEY (user_id, lesson_id)
            )
        ''')
        db.commit()

# Cargar lecciones
def load_lessons():
    with open('data/lessons.json', 'r', encoding='utf-8') as f:
        return json.load(f)

lessons = load_lessons()

@app.context_processor
def inject_global_data():
    user_data = None
    if 'user_id' in session:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT username, xp, streak FROM users WHERE id = ?', (session['user_id'],))
        user_data = cursor.fetchone()
    
    return {
        'user': dict(user_data) if user_data else None,
        'categories': ['Lectura', 'Matemáticas', 'Escritura', 'Vocabulario'],
        'category_icons': {
            'Lectura': 'book-open',
            'Matemáticas': 'calculator',
            'Escritura': 'pen',
            'Vocabulario': 'language'
        },
        'lessons': lessons
    }

# Manejo de errores
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

# Cerrar conexión a la BD al terminar
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Rutas principales
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        
        db = get_db()
        try:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            db.commit()
        except sqlite3.IntegrityError:
            return "El nombre de usuario ya existe"
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            
            # Actualizar última conexión y racha
            today = datetime.now().strftime('%Y-%m-%d')
            if user['last_login'] != today:
                new_streak = user['streak'] + 1 if user['last_login'] == (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d') else 1
                cursor.execute('UPDATE users SET last_login = ?, streak = ? WHERE id = ?', 
                             (today, new_streak, user['id']))
                db.commit()
            
            return redirect(url_for('index'))
        
        return render_template('login.html', error="Credenciales inválidas")
    
    return render_template('login.html')

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    lesson = next((l for l in lessons if l['id'] == lesson_id), None)
    if not lesson:
        return redirect(url_for('index'))
    
    return render_template('lesson_detail.html', lesson=lesson)

@app.route('/quiz/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def quiz(lesson_id):
    lesson = next((l for l in lessons if l['id'] == lesson_id), None)
    if not lesson:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        score = sum(1 for q in lesson['quiz'] 
                   if request.form.get(f'q{q["id"]}') == q['correct_answer'])
        
        db = get_db()
        cursor = db.cursor()
        
        # Registrar lección completada
        cursor.execute('''
            INSERT OR REPLACE INTO completed_lessons (user_id, lesson_id, score)
            VALUES (?, ?, ?)
        ''', (session['user_id'], lesson_id, score))
        
        # Actualizar XP del usuario
        cursor.execute('''
            UPDATE users 
            SET xp = xp + ?
            WHERE id = ?
        ''', (score * 10, session['user_id']))
        
        db.commit()
        
        return render_template('quiz_result.html', 
                             lesson=lesson,
                             score=score,
                             total=len(lesson['quiz']))
    
    return render_template('quiz.html', lesson=lesson)

@app.route('/profile')
@login_required
def profile():
    db = get_db()
    cursor = db.cursor()
    
    # Datos del usuario
    cursor.execute('SELECT username, xp, streak, created_at FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    
    # Lecciones completadas
    cursor.execute('''
        SELECT lesson_id, score, completed_at 
        FROM completed_lessons 
        WHERE user_id = ?
        ORDER BY completed_at DESC
    ''', (session['user_id'],))
    completed = cursor.fetchall()
    
    # Mapear lecciones completadas con datos de lecciones
    completed_lessons = []
    for row in completed:
        lesson = next((l for l in lessons if l['id'] == row['lesson_id']), None)
        if lesson:
            completed_lessons.append({
                'title': lesson['title'],
                'category': lesson['category'],
                'score': row['score'],
                'completed_at': row['completed_at'],
                'max_score': len(lesson['quiz'])
            })
    
    return render_template('profile.html', 
                         user=user,
                         completed_lessons=completed_lessons)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Inicializar la base de datos al iniciar
init_db()

# Configuración para producción
if __name__ == '__main__':
    from datetime import timedelta  # Importación adicional necesaria
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_DEBUG', 'False') == 'True'
    )
