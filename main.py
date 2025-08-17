from flask import Flask, render_template, request, redirect, url_for, session, g, flash, json
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
from datetime import datetime
from pathlib import Path

# Configuración inicial
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tu_super_clave_secreta_2025')  # Cambia esto en producción!

# Configuración de rutas
BASE_DIR = Path(__file__).parent
app.config['DATABASE'] = BASE_DIR / 'app.db'

# ==============================================
# LECCIÓNES DESDE EL ARCHIVO JSON (BASE DE DATOS)
# ==============================================
try:
    with open(BASE_DIR / 'lessons.json', 'r', encoding='utf-8') as f:
        LESSONS = json.load(f)
    print("✅ Lecciones cargadas desde lessons.json")
except Exception as e:
    print(f"❌ Error cargando lessons.json: {e}")
    LESSONS = []  # Lista vacía si hay error

# Categorías e íconos dinámicos
CATEGORIES = sorted({lesson['category'] for lesson in LESSONS})
CATEGORY_ICONS = {
    'Lectura': 'book',
    'Matemáticas': 'calculator',
    'Vocabulario': 'language',
    'Ciencias': 'flask'
}

# ==============================================
# CONFIGURACIÓN DE BASE DE DATOS
# ==============================================
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
                streak INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
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

# ==============================================
# DECORADORES Y FUNCIONES AUXILIARES
# ==============================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('🔒 Debes iniciar sesión para acceder', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# ==============================================
# RUTAS PRINCIPALES
# ==============================================
@app.route('/')
@login_required
def index():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Lecciones completadas por el usuario
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
    lesson = next((lesson for lesson in LESSONS if lesson['id'] == lesson_id), None)
    if not lesson:
        flash('📕 Lección no encontrada', 'danger')
        return redirect(url_for('index'))
    
    return render_template('lesson_detail.html', 
        lesson=lesson,
        user=dict(get_db().execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone())
    )

@app.route('/quiz/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def quiz(lesson_id):
    db = get_db()
    lesson = next((l for l in LESSONS if l['id'] == lesson_id), None)
    
    if not lesson:
        flash('📝 Cuestionario no encontrado', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Calcular puntaje
        score = sum(
            1 for q in lesson['quiz'] 
            if request.form.get(f'q{q["id"]}') == q['correct_answer']
        )
        
        # Guardar progreso
        try:
            db.execute('''
                INSERT OR REPLACE INTO user_lessons 
                (user_id, lesson_id, completed, completed_at, score)
                VALUES (?, ?, 1, datetime('now'), ?)
            ''', (session['user_id'], lesson_id, score))
            
            # Actualizar XP y racha
            db.execute(
                'UPDATE users SET xp = xp + ? WHERE id = ?',
                (score * 10, session['user_id'])
            )
            db.commit()
            flash(f'🏆 ¡Obtuviste {score} de {len(lesson["quiz"])} correctas!', 'success')
        except Exception as e:
            db.rollback()
            flash('❌ Error al guardar resultados', 'danger')
        
        return render_template('quiz_result.html', 
            lesson=lesson, 
            score=score,
            user=dict(db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone())
        )
    
    return render_template('quiz.html', lesson=lesson)

@app.route('/profile')
@login_required
def profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Progreso del usuario
    completed = db.execute('''
        SELECT ul.lesson_id, ul.score, l.title, l.category 
        FROM user_lessons ul
        JOIN (SELECT id, title, category FROM json_each(?)) l 
        ON ul.lesson_id = l.id
        WHERE ul.user_id = ? AND ul.completed = 1
    ''', (json.dumps(LESSONS), session['user_id'])).fetchall()
    
    return render_template('profile.html',
        user=dict(user),
        completed_lessons=list(completed),
        total_lessons=len(LESSONS)
    )

# ==============================================
# AUTENTICACIÓN
# ==============================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash('⚠️ Usuario y contraseña son requeridos', 'danger')
            return redirect(url_for('login'))
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?', 
            (username,)
        ).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            flash(f'👋 ¡Bienvenido {username}!', 'success')
            return redirect(url_for('index'))
        
        flash('❌ Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validaciones
        if not username or not password:
            flash('⚠️ Todos los campos son requeridos', 'danger')
            return redirect(url_for('register'))
            
        if len(password) < 6:
            flash('🔐 La contraseña debe tener al menos 6 caracteres', 'danger')
            return redirect(url_for('register'))
        
        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password, method='pbkdf2:sha256'))
            )
            db.commit()
            flash('✅ ¡Registro exitoso! Ahora inicia sesión', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('⛔ El usuario ya existe', 'danger')
        except Exception as e:
            flash(f'❌ Error en el registro: {str(e)}', 'danger')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 ¡Sesión cerrada correctamente!', 'info')
    return redirect(url_for('login'))

# ==============================================
# INICIALIZACIÓN
# ==============================================
with app.app_context():
    init_db()
    
    # Crear usuario admin si no existe
    db = get_db()
    if not db.execute('SELECT 1 FROM users WHERE username = "admin"').fetchone():
        db.execute(
            "INSERT INTO users (username, password, streak, xp) VALUES (?, ?, ?, ?)",
            ("admin", generate_password_hash("admin123"), 7, 150)
        )
        db.commit()
        print("👨‍💻 Usuario admin creado: admin / admin123")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
