from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave_por_defecto_segura')

# Configuración de la base de datos
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            os.path.join(os.path.dirname(__file__), 'app.db'),
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def init_db():
    try:
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.commit()
    except Exception as e:
        print(f"Error inicializando DB: {str(e)}")

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Rutas principales
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            db = get_db()
            user = db.execute(
                'SELECT * FROM users WHERE username = ?', (username,)
            ).fetchone()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                return redirect(url_for('index'))
            
            flash('Usuario o contraseña incorrectos')
        except Exception as e:
            print(f"Error en login: {str(e)}")
            flash('Error en el servidor')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            db = get_db()
            db.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            db.commit()
            flash('Registro exitoso! Por favor inicia sesión')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('El usuario ya existe')
        except Exception as e:
            print(f"Error en registro: {str(e)}")
            flash('Error en el servidor')
    
    return render_template('register.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)

# Inicialización
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
