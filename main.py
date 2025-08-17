from flask import Flask, render_template, request, redirect, url_for, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import sqlite3
import os
from dotenv import load_dotenv

# Configuración inicial
load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tu_clave_secreta_super_segura_aqui')
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'app.db')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Tabla de progreso
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        db.commit()

# Decorador para rutas protegidas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Cerrar conexión a la BD
@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Rutas de autenticación
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        if not username or not password:
            return render_template('register.html', error="Todos los campos son requeridos")
        
        try:
            db = get_db()
            cursor = db.cursor()
            hashed_pw = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_pw)
            )
            cursor.execute(
                "INSERT INTO user_progress (user_id) VALUES (?)",
                (cursor.lastrowid,)
            )
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="El usuario ya existe")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session.permanent = True
            
            # Actualizar último login y racha
            today = datetime.now()
            cursor.execute('''
                UPDATE users SET last_login = ? WHERE id = ?
            ''', (today, user['id']))
            
            cursor.execute('''
                UPDATE user_progress 
                SET streak = streak + 1 
                WHERE user_id = ? AND DATE(last_login) = DATE(?, '-1 day')
            ''', (user['id'], today))
            db.commit()
            
            next_page = request.args.get('next') or url_for('index')
            return redirect(next_page)
        
        return render_template('login.html', error="Usuario o contraseña incorrectos")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Rutas principales
@app.route('/')
@login_required
def index():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT u.username, up.xp, up.streak 
        FROM users u
        JOIN user_progress up ON u.id = up.user_id
        WHERE u.id = ?
    ''', (session['user_id'],))
    user = cursor.fetchone()
    
    return render_template('index.html', user=dict(user))

# Inicialización
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
