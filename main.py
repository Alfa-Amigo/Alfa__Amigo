from flask import Flask, render_template, request, redirect, url_for, session, g, flash, json
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
from datetime import datetime
from pathlib import Path

# Configuración inicial
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_123')  # Cambia en producción!

# Configuración de rutas
BASE_DIR = Path(__file__).parent
app.config['DATABASE'] = BASE_DIR / 'app.db'

# Lecciones integradas (backup si no encuentra el JSON)
DEFAULT_LESSONS = [
    {
        "id": 1,
        "title": "El Abecedario",
        "description": "Aprende las letras del alfabeto español",
        "icon": "font",
        "category": "Lectura",
        "content": [
            {"type": "text", "content": "<p>El alfabeto español tiene 27 letras...</p>"},
            {"type": "image", "url": "/static/images/alfabeto.jpg", "alt": "Abecedario"}
        ],
        "quiz": [
            {
                "id": 1,
                "question": "¿Cuál es la primera letra?",
                "options": ["A", "B", "Z"],
                "correct_answer": "A"
            }
        ]
    }
]

# Cargar lecciones desde JSON o usar las por defecto
try:
    with open(BASE_DIR / 'lessons.json', 'r', encoding='utf-8') as f:
        LESSONS = json.load(f)
except FileNotFoundError:
    LESSONS = DEFAULT_LESSONS
    print("⚠️ Usando lecciones por defecto (no se encontró lessons.json)")

CATEGORIES = sorted({lesson['category'] for lesson in LESSONS})
CATEGORY_ICONS = {
    'Lectura': 'book',
    'Matemáticas': 'calculator',
    'Vocabulario': 'language'
}

# Configuración de la base de datos
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                streak INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                joined TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_lessons (
                user_id INTEGER,
                lesson_id INTEGER,
                completed BOOLEAN DEFAULT 0,
                completed_at TEXT,
                score INTEGER,
                PRIMARY KEY (user_id, lesson_id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        db.commit()

# Decorador para rutas protegidas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicia sesión', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Rutas principales
@app.route('/')
@login_required
def index():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    completed = db.execute(
        'SELECT lesson_id FROM user_lessons WHERE user_id = ? AND completed = 1',
        (session['user_id'],)
    ).fetchall()
    
    return render_template('index.html',
        user=dict(user),
        lessons=LESSONS,
        categories=CATEGORIES,
        category_icons=CATEGORY_ICONS,
        user_completed_lessons=[row['lesson_id'] for row in completed]
    )

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    lesson = next((l for l in LESSONS if l['id'] == lesson_id), None)
    if not lesson:
        flash('Lección no encontrada', 'danger')
        return redirect(url_for('index'))
    return render_template('lesson_detail.html', lesson=lesson)

@app.route('/quiz/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def quiz(lesson_id):
    lesson = next((l for l in LESSONS if l['id'] == lesson_id), None)
    if not lesson:
        flash('Lección no encontrada', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        score = sum(
            1 for q in lesson['quiz'] 
            if request.form.get(f'q{q["id"]}') == q['correct_answer']
        )
        
        db = get_db()
        try:
            db.execute('''
                INSERT OR REPLACE INTO user_lessons 
                (user_id, lesson_id, completed, completed_at, score)
                VALUES (?, ?, 1, datetime('now'), ?)
            ''', (session['user_id'], lesson_id, score))
            
            db.execute(
                'UPDATE users SET xp = xp + ? WHERE id = ?',
                (score * 10, session['user_id'])
            )
            db.commit()
        except Exception as e:
            db.rollback()
            flash('Error al guardar progreso', 'danger')
        
        return render_template('quiz_result.html', lesson=lesson, score=score)
    
    return render_template('quiz.html', lesson=lesson)

@app.route('/profile')
@login_required
def profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    completed = db.execute(
        'SELECT lesson_id FROM user_lessons WHERE user_id = ? AND completed = 1',
        (session['user_id'],)
    ).fetchall()
    
    return render_template('profile.html',
        user={**dict(user), 'completed_lessons': [row['lesson_id'] for row in completed]},
        lessons=LESSONS
    )

# Autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        
        flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            db.commit()
            flash('Registro exitoso! Por favor inicia sesión', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El usuario ya existe', 'danger')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Inicialización
with app.app_context():
    init_db()
    # Crear usuario admin si no existe
    db = get_db()
    if not db.execute('SELECT 1 FROM users WHERE username = "admin"').fetchone():
        db.execute(
            "INSERT INTO users (username, password, streak, xp) VALUES (?, ?, ?, ?)",
            ("admin", generate_password_hash("admin123"), 5, 100)
        )
        db.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
