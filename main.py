
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path

# Configuración inicial
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tu_super_clave_secreta_2025!')
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 1 día en segundos

# Configuración de rutas
BASE_DIR = Path(__file__).parent
app.config['DATABASE'] = BASE_DIR / 'app.db'
app.config['LESSONS_FILE'] = BASE_DIR / 'lessons.json'

# Cargar lecciones desde JSON
def load_lessons():
    try:
        with open(app.config['LESSONS_FILE'], 'r', encoding='utf-8') as f:
            lessons = json.load(f)
            print(f"✅ Lecciones cargadas: {len(lessons)} encontradas")
            return lessons
    except Exception as e:
        print(f"❌ Error cargando lessons.json: {e}")
        return []

LESSONS = load_lessons()
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
        
        # Tabla de usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT,
                streak INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                last_login TEXT,
                joined TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de progreso
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
            flash('🔒 Por favor inicia sesión para acceder', 'warning')
            return redirect(url_for('login', next=request.url))
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
    
    # Obtener lecciones completadas por el usuario
    completed_lessons = db.execute(
        'SELECT lesson_id FROM user_lessons WHERE user_id = ? AND completed = 1',
        (session['user_id'],)
    ).fetchall()
    
    completed_lesson_ids = [row['lesson_id'] for row in completed_lessons]
    
    # Crear objeto user con todos los datos necesarios
    user_data = {
        'id': user['id'],
        'username': user['username'],
        'name': user.get('name', user['username']),  # Usamos el nombre si existe, sino el username
        'streak': user['streak'],
        'xp': user['xp'],
        'joined': user['joined'],
        'completed_lessons': completed_lesson_ids
    }
    
    return render_template('index.html',
        user=user_data,
        lessons=LESSONS,
        categories=CATEGORIES,
        category_icons=CATEGORY_ICONS
    )

@app.route('/profile')
@login_required
def profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Obtener lecciones completadas con detalles
    completed_lessons = db.execute('''
        SELECT lesson_id FROM user_lessons 
        WHERE user_id = ? AND completed = 1
        ORDER BY completed_at DESC
    ''', (session['user_id'],)).fetchall()
    
    completed_lesson_ids = [row['lesson_id'] for row in completed_lessons]
    
    # Filtrar lecciones completadas
    completed_with_details = []
    for lesson in LESSONS:
        if lesson['id'] in completed_lesson_ids:
            completed_with_details.append(lesson)
    
    # Crear objeto user con todos los datos necesarios
    user_data = {
        'id': user['id'],
        'username': user['username'],
        'name': user.get('name', user['username']),
        'streak': user['streak'],
        'xp': user['xp'],
        'joined': user['joined'],
        'completed_lessons': completed_lesson_ids
    }
    
    return render_template('profile.html',
        user=user_data,
        lessons=LESSONS,
        completed_lessons=completed_with_details
    )

# Sistema de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('⚠️ Usuario y contraseña son requeridos', 'danger')
            return render_template('login.html', username=username)
            
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', 
            (username,)
        ).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            session.permanent = True
            
            # Actualizar último login y posiblemente la racha
            db.execute(
                'UPDATE users SET last_login = datetime("now") WHERE id = ?',
                (user['id'],)
            )
            db.commit()
            
            next_page = request.args.get('next')
            flash(f'👋 ¡Bienvenido {username}!', 'success')
            return redirect(next_page or url_for('index'))
        
        flash('❌ Usuario o contraseña incorrectos', 'danger')
        return render_template('login.html', username=username)
    
    return render_template('login.html', next=request.args.get('next'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        # Validaciones
        errors = []
        if len(username) < 4:
            errors.append("El usuario debe tener al menos 4 caracteres")
        if len(password) < 6:
            errors.append("La contraseña debe tener al menos 6 caracteres")
        if password != confirm_password:
            errors.append("Las contraseñas no coinciden")

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html', username=username)

        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (username, password, name) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), username)
            )
            db.commit()
            flash('✅ ¡Registro exitoso! Por favor inicia sesión', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('⛔ El usuario ya existe', 'danger')
        except Exception as e:
            flash(f'❌ Error al crear la cuenta: {str(e)}', 'danger')

    return render_template('register.html')

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
        # Calcular puntaje
        score = 0
        for question in lesson['quiz']:
            user_answer = request.form.get(f'q{question["id"]}')
            if user_answer == question['correct_answer']:
                score += 1
        
        # Guardar resultados en la base de datos
        db = get_db()
        try:
            db.execute(
                '''INSERT OR REPLACE INTO user_lessons 
                (user_id, lesson_id, completed, completed_at, score)
                VALUES (?, ?, 1, datetime("now"), ?)''',
                (session['user_id'], lesson_id, score)
            )
            
            # Actualizar XP del usuario (10 puntos por respuesta correcta)
            xp_gained = score * 10
            db.execute(
                'UPDATE users SET xp = xp + ? WHERE id = ?',
                (xp_gained, session['user_id'])
            )
            
            db.commit()
            
            return redirect(url_for('quiz_result', lesson_id=lesson_id, score=score))
        except Exception as e:
            flash('Error al guardar los resultados', 'danger')
            print(f"Error: {e}")
    
    return render_template('quiz.html', lesson=lesson)

@app.route('/quiz/<int:lesson_id>/result')
@login_required
def quiz_result(lesson_id):
    lesson = next((l for l in LESSONS if l['id'] == lesson_id), None)
    score = request.args.get('score', 0, type=int)
    
    if not lesson:
        flash('Lección no encontrada', 'danger')
        return redirect(url_for('index'))
    
    return render_template('quiz_result.html', lesson=lesson, score=score)

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 ¡Sesión cerrada correctamente!', 'info')
    return redirect(url_for('login'))

# Inicialización
with app.app_context():
    init_db()
    
    # Crear usuario admin si no existe
    db = get_db()
    if not db.execute('SELECT 1 FROM users WHERE username = "admin"').fetchone():
        db.execute(
            "INSERT INTO users (username, password, name, streak, xp) VALUES (?, ?, ?, ?, ?)",
            ("admin", generate_password_hash("admin123"), "Administrador", 5, 100)
        )
        db.commit()
        print("👨‍💻 Usuario admin creado: admin / admin123")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
