from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_por_defecto_para_desarrollo')

# Configuración para Render
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=3600  # 1 hora en segundos
)

# Cargar lecciones
def load_lessons():
    with open('data/lessons.json', 'r', encoding='utf-8') as f:
        return json.load(f)

lessons = load_lessons()

@app.context_processor
def inject_global_data():
    return {
        'user': session.get('user'),
        'categories': ['Lectura', 'Matemáticas', 'Escritura', 'Vocabulario'],  # Corregido mayúscula
        'category_icons': {
            'Lectura': 'book-open',
            'Matemáticas': 'calculator',
            'Escritura': 'pen',
            'Vocabulario': 'language'  # Icono añadido
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

# Rutas principales
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if not username:
            return redirect(url_for('login'))
            
        session['user'] = {
            'name': username,
            'joined': datetime.now().strftime('%d/%m/%Y'),
            'xp': 0,
            'streak': 1,
            'completed_lessons': []
        }
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/lesson/<int:lesson_id>')
def lesson_detail(lesson_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    lesson = next((l for l in lessons if l['id'] == lesson_id), None)
    if not lesson:
        return redirect(url_for('index'))

    return render_template('lesson_detail.html', lesson=lesson)

@app.route('/quiz/<int:lesson_id>', methods=['GET', 'POST'])
def quiz(lesson_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    lesson = next((l for l in lessons if l['id'] == lesson_id), None)
    if not lesson:
        return redirect(url_for('index'))

    if request.method == 'POST':
        score = sum(1 for q in lesson['quiz'] 
                if request.form.get(f'q{q["id"]}') == q['correct_answer'])

        if lesson_id not in session['user']['completed_lessons']:
            session['user']['completed_lessons'].append(lesson_id)
            session['user']['xp'] += score * 10
            session.modified = True

        return render_template('quiz_result.html', 
                           lesson=lesson,
                           score=score,
                           total=len(lesson['quiz']))

    return render_template('quiz.html', lesson=lesson)

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('profile.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Configuración para producción
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_DEBUG', 'False') == 'True'
    )
