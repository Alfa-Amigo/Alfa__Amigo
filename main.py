from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import json
from pathlib import Path
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_temporal'  # Cambia esto en producción

# Configuración de rutas
BASE_DIR = Path(__file__).parent
LESSONS_FILE = BASE_DIR / 'static' / 'data' / 'lessons.json'

# Datos en memoria (simulan la base de datos)
users = {
    'admin': {
        'password': generate_password_hash('admin123'),
        'name': 'Administrador',
        'xp': 100,
        'streak': 5,
        'completed_lessons': [1, 2, 3]
    }
}

# Cargar lecciones
def load_lessons():
    try:
        with open(LESSONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

LESSONS = load_lessons()
CATEGORIES = sorted({lesson['category'] for lesson in LESSONS})
CATEGORY_ICONS = {
    'Lectura': 'book',
    'Matemáticas': 'calculator',
    'Vocabulario': 'language'
}

# Decorador para rutas protegidas
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('🔒 Por favor inicia sesión para acceder', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Rutas principales
@app.route('/')
@login_required
def index():
    user = users.get(session['username'])
    return render_template('index.html',
        user=user,
        lessons=LESSONS,
        categories=CATEGORIES,
        category_icons=CATEGORY_ICONS,
        completed_lessons=user.get('completed_lessons', [])
    )

@app.route('/profile')
@login_required
def profile():
    user = users.get(session['username'])
    return render_template('profile.html',
        user=user,
        lessons=LESSONS,
        completed_lessons=user.get('completed_lessons', [])
    )

# Autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = users.get(username)
        
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash(f'👋 ¡Bienvenido {username}!', 'success')
            return redirect(url_for('index'))
        
        flash('❌ Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if len(username) < 4:
            flash('El usuario debe tener al menos 4 caracteres', 'danger')
        elif len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres', 'danger')
        elif password != confirm_password:
            flash('Las contraseñas no coinciden', 'danger')
        elif username in users:
            flash('El usuario ya existe', 'danger')
        else:
            users[username] = {
                'password': generate_password_hash(password),
                'name': username,
                'xp': 0,
                'streak': 0,
                'completed_lessons': []
            }
            flash('✅ ¡Registro exitoso! Por favor inicia sesión', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

# Sistema de lecciones
@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    lesson = next((l for l in LESSONS if l['id'] == lesson_id), None)
    if not lesson:
        flash('Lección no encontrada', 'danger')
        return redirect(url_for('index'))
    return render_template('lesson_detail.html', lesson=lesson)

@app.route('/lesson/<int:lesson_id>/quiz', methods=['GET', 'POST'])
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
        
        # Actualizar datos del usuario
        user = users[session['username']]
        user['xp'] += score * 10
        if lesson_id not in user['completed_lessons']:
            user['completed_lessons'].append(lesson_id)
        
        return redirect(url_for('quiz_result', lesson_id=lesson_id, score=score))
    
    return render_template('quiz.html', lesson=lesson)

@app.route('/lesson/<int:lesson_id>/result')
@login_required
def quiz_result(lesson_id):
    lesson = next((l for l in LESSONS if l['id'] == lesson_id), None)
    score = request.args.get('score', 0)
    return render_template('quiz_result.html', lesson=lesson, score=int(score))

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('👋 ¡Sesión cerrada correctamente!', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
