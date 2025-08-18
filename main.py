from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import json
import os
from pathlib import Path

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'clave_secreta_temporal_123'

# Configuración de rutas - AJUSTADA PARA PUBLIC/STATIC/DATA
BASE_DIR = Path(__file__).parent
app.config['LESSONS_FILE'] = BASE_DIR / 'public' / 'static' / 'data' / 'lessons.json'

# Crear directorios necesarios
os.makedirs(BASE_DIR / 'public' / 'static' / 'data', exist_ok=True)

# Datos en memoria
users = {
    'admin': {
        'password': generate_password_hash('admin123'),
        'name': 'Admin',
        'xp': 100,
        'streak': 5,
        'completed_lessons': []
    }
}

def load_lessons():
    try:
        if not os.path.exists(app.config['LESSONS_FILE']):
            raise FileNotFoundError(f"Archivo no encontrado en: {app.config['LESSONS_FILE']}")
            
        with open(app.config['LESSONS_FILE'], 'r', encoding='utf-8') as f:
            lessons = json.load(f)
            print(f"✅ Lecciones cargadas desde: {app.config['LESSONS_FILE']}")
            return lessons
    except Exception as e:
        print(f"❌ Error cargando lecciones: {str(e)}")
        # Datos de ejemplo
        return [
            {
                "id": 1,
                "title": "Lección de Ejemplo",
                "description": "Contenido de ejemplo porque no se encontró el archivo",
                "category": "General",
                "content": [{"type": "text", "content": "Ejemplo de contenido"}],
                "quiz": [{
                    "id": 1,
                    "question": "Pregunta ejemplo",
                    "options": ["Opción 1", "Opción 2"],
                    "correct_answer": "Opción 1"
                }]
            }
        ]

LESSONS = load_lessons()
CATEGORIES = sorted({lesson.get('category', 'General') for lesson in LESSONS})
CATEGORY_ICONS = {
    'General': 'question-circle',
    'Lectura': 'book',
    'Matemáticas': 'calculator',
    'Vocabulario': 'language'
}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Por favor inicia sesión', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user = users.get(session['username'], {})
    return render_template('index.html',
        user=user,
        lessons=LESSONS,
        categories=CATEGORIES,
        category_icons=CATEGORY_ICONS,
        completed_lessons=user.get('completed_lessons', [])
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        user = users.get(username)
        
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash(f'¡Bienvenido {username}!', 'success')
            return redirect(url_for('index'))
        
        flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()

        if len(username) < 4:
            flash('Usuario muy corto (mínimo 4 caracteres)', 'danger')
        elif len(password) < 6:
            flash('Contraseña muy corta (mínimo 6 caracteres)', 'danger')
        elif password != confirm:
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
            flash('¡Registro exitoso! Por favor inicia sesión', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/profile')
@login_required
def profile():
    user = users.get(session['username'], {})
    return render_template('profile.html',
        user=user,
        lessons=LESSONS,
        completed_lessons=user.get('completed_lessons', [])
    )

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    lesson = next((l for l in LESSONS if l.get('id') == lesson_id), None)
    if not lesson:
        flash('Lección no encontrada', 'danger')
        return redirect(url_for('index'))
    return render_template('lesson_detail.html', lesson=lesson)

@app.route('/lesson/<int:lesson_id>/quiz', methods=['GET', 'POST'])
@login_required
def quiz(lesson_id):
    lesson = next((l for l in LESSONS if l.get('id') == lesson_id), None)
    if not lesson:
        flash('Lección no encontrada', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        score = sum(
            1 for q in lesson.get('quiz', []) 
            if request.form.get(f'q{q.get("id")}') == q.get('correct_answer')
        )
        
        user = users.get(session['username'], {})
        user['xp'] = user.get('xp', 0) + score * 10
        if lesson_id not in user.get('completed_lessons', []):
            user.setdefault('completed_lessons', []).append(lesson_id)
        
        return redirect(url_for('quiz_result', lesson_id=lesson_id, score=score))
    
    return render_template('quiz.html', lesson=lesson)

@app.route('/lesson/<int:lesson_id>/result')
@login_required
def quiz_result(lesson_id):
    lesson = next((l for l in LESSONS if l.get('id') == lesson_id), None)
    score = request.args.get('score', 0)
    return render_template('quiz_result.html', 
                         lesson=lesson, 
                         score=int(score))

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
