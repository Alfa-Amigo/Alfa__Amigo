from flask import Flask, render_template, request, redirect, url_for, session, g, flash, json
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
from datetime import datetime
from pathlib import Path

# Configuración inicial
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super-secreto-alfaamigo-2025')

# Configuración de rutas
BASE_DIR = Path(__file__).parent
app.config['DATABASE'] = BASE_DIR / 'app.db'
app.config['LESSONS_FILE'] = BASE_DIR / 'lessons.json'

# ======================
# CARGAR LECCIÓNES
# ======================
def load_lessons():
    try:
        with open(app.config['LESSONS_FILE'], 'r', encoding='utf-8') as f:
            lessons = json.load(f)
        
        # Validación básica del JSON
        if not isinstance(lessons, list):
            raise ValueError("El formato de lessons.json no es válido")
        
        print(f"✅ Cargadas {len(lessons)} lecciones desde lessons.json")
        return lessons
    
    except Exception as e:
        print(f"❌ Error cargando lessons.json: {e}")
        return []

LESSONS = load_lessons()

# Categorías e íconos dinámicos
CATEGORIES = sorted({lesson['category'] for lesson in LESSONS})
CATEGORY_ICONS = {
    'Lectura': 'book',
    'Matemáticas': 'calculator',
    'Vocabulario': 'language',
    'Ciencias': 'flask'
}

# ======================
# BASE DE DATOS
# ======================
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        
        # Tabla de usuarios mejorada
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                streak INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                last_login TEXT,
                joined TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de progreso mejorada
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_lessons (
                user_id INTEGER,
                lesson_id INTEGER,
                completed BOOLEAN DEFAULT 0,
                completed_at TEXT,
                score INTEGER,
                attempts INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, lesson_id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        db.commit()

# ======================
# HELPERS
# ======================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('🔒 Debes iniciar sesión primero', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_user_progress(user_id):
    db = get_db()
    progress = db.execute('''
        SELECT lesson_id, MAX(score) as best_score, attempts
        FROM user_lessons 
        WHERE user_id = ? 
        GROUP BY lesson_id
    ''', (user_id,)).fetchall()
    return {row['lesson_id']: dict(row) for row in progress}

# ======================
# RUTAS PRINCIPALES
# ======================
@app.route('/')
@login_required
def index():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    progress = get_user_progress(session['user_id'])
    
    return render_template('index.html',
        user=dict(user),
        lessons=LESSONS,
        categories=CATEGORIES,
        category_icons=CATEGORY_ICONS,
        progress=progress
    )

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    lesson = next((l for l in LESSONS if l['id'] == lesson_id), None)
    if not lesson:
        flash('📕 Lección no encontrada', 'danger')
        return redirect(url_for('index'))
    
    db = get_db()
    progress = db.execute('''
        SELECT score, attempts FROM user_lessons 
        WHERE user_id = ? AND lesson_id = ?
        ORDER BY completed_at DESC LIMIT 1
    ''', (session['user_id'], lesson_id)).fetchone()
    
    return render_template('lesson_detail.html',
        lesson=lesson,
        progress=dict(progress) if progress else None,
        user=dict(db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone())
    )

@app.route('/quiz/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def quiz(lesson_id):
    db = get_db()
    lesson = next((l for l in LESSONS if l['id'] == lesson_id), None)
    
    if not lesson or 'quiz' not in lesson:
        flash('📝 Cuestionario no disponible', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Calcular puntaje
        score = sum(
            1 for q in lesson['quiz'] 
            if request.form.get(f'q{q["id"]}') == q['correct_answer']
        )
        
        # Registrar intento
        try:
            db.execute('''
                INSERT INTO user_lessons 
                (user_id, lesson_id, completed, completed_at, score, attempts)
                VALUES (?, ?, 1, datetime('now'), ?, 
                    COALESCE((SELECT attempts FROM user_lessons 
                     WHERE user_id = ? AND lesson_id = ? 
                     ORDER BY completed_at DESC LIMIT 1), 0) + 1)
            ''', (session['user_id'], lesson_id, score, session['user_id'], lesson_id))
            
            # Actualizar XP (10 puntos por respuesta correcta)
            db.execute(
                'UPDATE users SET xp = xp + ? WHERE id = ?',
                (score * 10, session['user_id'])
            )
            db.commit()
            
            flash(f'🏆 Resultado: {score}/{len(lesson["quiz"])}', 'success')
            return render_template('quiz_result.html',
                lesson=lesson,
                score=score,
                total=len(lesson['quiz']),
                user=dict(db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone())
            )
        except Exception as e:
            db.rollback()
            flash(f'❌ Error: {str(e)}', 'danger')
    
    return render_template('quiz.html',
        lesson=lesson,
        user=dict(db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone())
    )

@app.route('/profile')
@login_required
def profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Progreso detallado
    progress = db.execute('''
        SELECT ul.lesson_id, l.title, l.category, 
               MAX(ul.score) as best_score, 
               COUNT(ul.attempts) as attempts,
               MAX(ul.completed_at) as last_attempt
        FROM user_lessons ul
        JOIN (SELECT id, title, category FROM json_each(?)) l 
        ON ul.lesson_id = l.id
        WHERE ul.user_id = ?
        GROUP BY ul.lesson_id
        ORDER BY last_attempt DESC
    ''', (json.dumps(LESSONS), session['user_id'])).fetchall()
    
    return render_template('profile.html',
        user=dict(user),
        progress=list(progress),
        total_lessons=len(LESSONS),
        completed=len([p for p in progress if p['best_score'] > 0])
    )

# ======================
# AUTENTICACIÓN
# ======================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('⚠️ Usuario y contraseña requeridos', 'danger')
            return redirect(url_for('login'))
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', 
            (username,)
        ).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            
            # Actualizar última conexión y racha
            db.execute(
                'UPDATE users SET last_login = datetime("now") WHERE id = ?',
                (user['id'],)
            )
            db.commit()
            
            flash(f'👋 ¡Bienvenido {username}!', 'success')
            return redirect(url_for('index'))
        
        flash('❌ Credenciales incorrectas', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validaciones mejoradas
        errors = []
        if len(username) < 4:
            errors.append("El usuario debe tener al menos 4 caracteres")
        if len(password) < 6:
            errors.append("La contraseña debe tener al menos 6 caracteres")
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return redirect(url_for('register'))
        
        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password, method='pbkdf2:sha256'))
            )
            db.commit()
            flash('✅ ¡Registro exitoso! Inicia sesión', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('⛔ El usuario ya existe', 'danger')
        except Exception as e:
            flash(f'❌ Error: {str(e)}', 'danger')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 ¡Sesión cerrada! Vuelve pronto', 'info')
    return redirect(url_for('login'))

# ======================
# INICIALIZACIÓN
# ======================
with app.app_context():
    init_db()
    
    # Crear admin si no existe
    db = get_db()
    if not db.execute('SELECT 1 FROM users WHERE username = "admin"').fetchone():
        db.execute(
            "INSERT INTO users (username, password, streak, xp) VALUES (?, ?, ?, ?)",
            ("admin", generate_password_hash("admin123"), 7, 150)
        )
        db.commit()
        print("👨‍💻 Usuario admin creado: usuario=admin | contraseña=admin123")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
