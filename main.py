from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import sqlite3
import os
import json
from dotenv import load_dotenv

# Configuración inicial
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'app.db')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Base de datos - Versión optimizada para Render
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES,
            timeout=20,
            check_same_thread=False  # Necesario para Render
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA busy_timeout=30000")
    return g.db

def init_db():
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.executescript('''
            BEGIN;
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS completed_lessons (
                user_id INTEGER,
                lesson_id INTEGER,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                score INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, lesson_id)
            );
            COMMIT;
        ''')
        db.commit()
    except Exception as e:
        print(f"Error inicializando DB: {str(e)}")
        if 'db' in g:
            g.db.rollback()

# Decorador para rutas protegidas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor inicia sesión para acceder a esta página', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Cerrar conexión
@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Cargar lecciones
def load_lessons():
    try:
        with open('data/lessons.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error cargando lecciones: {str(e)}")
        return []

lessons = load_lessons()

# Context processor
@app.context_processor
def inject_user():
    user_data = {}
    if 'user_id' in session:
        try:
            db = get_db()
            user = db.execute('''
                SELECT u.username, up.xp, up.streak 
                FROM users u
                LEFT JOIN user_progress up ON u.id = up.user_id
                WHERE u.id = ?
            ''', (session['user_id'],)).fetchone()
            if user:
                user_data = dict(user)
        except Exception as e:
            print(f"Error obteniendo datos de usuario: {str(e)}")
    return {'current_user': user_data}

# Manejo de errores
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

# Rutas de autenticación
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if len(username) < 4 or len(password) < 6:
            flash('Usuario debe tener al menos 4 caracteres y contraseña 6', 'danger')
            return redirect(url_for('register'))
        
        try:
            db = get_db()
            hashed_pw = generate_password_hash(password)
            
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_pw)
            )
            user_id = cursor.lastrowid
            
            cursor.execute(
                "INSERT INTO user_progress (user_id) VALUES (?)",
                (user_id,)
            )
            db.commit()
            
            flash('¡Registro exitoso! Por favor inicia sesión', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El nombre de usuario ya existe', 'danger')
        except Exception as e:
            print(f"Error en registro: {str(e)}")
            flash('Ocurrió un error en el servidor', 'danger')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        try:
            db = get_db()
            user = db.execute(
                'SELECT * FROM users WHERE username = ?', (username,)
            ).fetchone()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session.permanent = True
                
                # Actualizar último login
                today = datetime.now()
                db.execute(
                    'UPDATE users SET last_login = ? WHERE id = ?',
                    (today, user['id'])
                )
                
                # Actualizar racha
                cursor = db.cursor()
                cursor.execute('''
                    UPDATE user_progress 
                    SET streak = CASE 
                        WHEN last_login IS NOT NULL AND DATE(last_login) = DATE(?, '-1 day') 
                        THEN streak + 1 
                        ELSE 1 
                    END
                    WHERE user_id = ?
                ''', (today, user['id']))
                db.commit()
                
                next_page = request.args.get('next', url_for('index'))
                return redirect(next_page)
            
            flash('Usuario o contraseña incorrectos', 'danger')
        except Exception as e:
            print(f"Error en login: {str(e)}")
            flash('Ocurrió un error en el servidor', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('login'))

# Rutas principales
@app.route('/')
@login_required
def index():
    try:
        return render_template('index.html', lessons=lessons)
    except Exception as e:
        print(f"Error cargando índice: {str(e)}")
        flash('Error al cargar las lecciones', 'danger')
        return render_template('index.html', lessons=[])

@app.route('/profile')
@login_required
def profile():
    try:
        db = get_db()
        user = db.execute('''
            SELECT u.username, u.created_at, up.xp, up.streak
            FROM users u
            JOIN user_progress up ON u.id = up.user_id
            WHERE u.id = ?
        ''', (session['user_id'],)).fetchone()
        
        completed = db.execute('''
            SELECT lesson_id, score, completed_at
            FROM completed_lessons
            WHERE user_id = ?
            ORDER BY completed_at DESC
            LIMIT 10
        ''', (session['user_id'],)).fetchall()
        
        completed_lessons = []
        for row in completed:
            lesson = next((l for l in lessons if l['id'] == row['lesson_id']), None)
            if lesson:
                completed_lessons.append({
                    'title': lesson['title'],
                    'category': lesson['category'],
                    'score': row['score'],
                    'completed_at': row['completed_at'],
                    'max_score': len(lesson.get('quiz', []))
                })
        
        return render_template('profile.html', 
                            user=dict(user),
                            completed_lessons=completed_lessons)
    except Exception as e:
        print(f"Error cargando perfil: {str(e)}")
        flash('Error al cargar tu perfil', 'danger')
        return redirect(url_for('index'))

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    lesson = next((l for l in lessons if l['id'] == lesson_id), None)
    if not lesson:
        flash('Lección no encontrada', 'danger')
        return redirect(url_for('index'))
    return render_template('lesson_detail.html', lesson=lesson)

@app.route('/quiz/<int:lesson_id>', methods=['GET', 'POST'])
@login_required
def quiz(lesson_id):
    lesson = next((l for l in lessons if l['id'] == lesson_id), None)
    if not lesson or 'quiz' not in lesson:
        flash('Lección no encontrada', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        score = 0
        for q in lesson['quiz']:
            if request.form.get(f'q{q["id"]}') == q['correct_answer']:
                score += 1
        
        try:
            db = get_db()
            db.execute('''
                INSERT OR REPLACE INTO completed_lessons 
                (user_id, lesson_id, score) VALUES (?, ?, ?)
            ''', (session['user_id'], lesson_id, score))
            
            db.execute('''
                UPDATE user_progress SET xp = xp + ? 
                WHERE user_id = ?
            ''', (score * 10, session['user_id']))
            
            db.commit()
            flash(f'¡Quiz completado! Puntaje: {score}/{len(lesson["quiz"])}', 'success')
            return render_template('quiz_result.html', 
                                lesson=lesson,
                                score=score,
                                total=len(lesson['quiz']))
        except Exception as e:
            print(f"Error guardando quiz: {str(e)}")
            flash('Error al guardar tus resultados', 'danger')
    
    return render_template('quiz.html', lesson=lesson)

# Inicialización segura para Render
@app.before_first_request
def initialize():
    with app.app_context():
        init_db()
        # Crear usuario admin si no existe
        try:
            db = get_db()
            if not db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                db.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    ("admin", generate_password_hash("admin123"))
                )
                db.commit()
                print("Usuario admin creado: admin/admin123")
        except Exception as e:
            print(f"Error inicializando usuario admin: {str(e)}")

if __name__ == '__main__':
    # Solo para desarrollo local
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
