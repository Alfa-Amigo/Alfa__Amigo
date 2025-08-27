from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import json
import os
from pathlib import Path
from flask import send_from_directory

# Inicialización de la aplicación
app = Flask(__name__)
app.secret_key = 'clave_segura_cambiar_en_produccion'  # ¡Cambiar en producción!

# Configuración de rutas
BASE_DIR = Path(__file__).parent.absolute()
LESSONS_FILE = BASE_DIR / 'public' / 'static' / 'data' / 'lessons.json'

# Crear directorios necesarios
os.makedirs(BASE_DIR / 'public' / 'static' / 'data', exist_ok=True)

# Carga de lecciones con manejo robusto de errores
def load_lessons():
    try:
        with open(LESSONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print("✅ Lecciones cargadas correctamente")
            return data
    except FileNotFoundError:
        print(f"⚠️ Archivo no encontrado: {LESSONS_FILE}")
    except json.JSONDecodeError:
        print("⚠️ Error en el formato del archivo JSON")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
    
    # Datos de ejemplo si hay error
    return [
        {
            "id": 1,
            "title": "Ejemplo",
            "description": "Lección de ejemplo",
            "category": "General",
            "content": [{"type": "text", "content": "Contenido de ejemplo"}],
            "quiz": [
                {
                    "id": 1,
                    "question": "Pregunta ejemplo",
                    "options": ["Opción 1", "Opción 2"],
                    "correct_answer": "Opción 1"
                }
            ]
        }
    ]

lessons = load_lessons()

# Datos globales para plantillas
@app.context_processor
def inject_global_data():
    return {
        'user': session.get('user'),
        'version': session.get('version', 'adults'),  # Default a adultos
        'categories': sorted({l.get('category', 'General') for l in lessons}),
        'category_icons': {
            'Lectura': 'book-open',
            'Matemáticas': 'calculator',
            'Escritura': 'pen',
            'General': 'question-circle'
        },
        'lessons': lessons
    }

# Rutas principales

@app.route('/descargar-app')
def descargar_app():
    return send_from_directory(
        directory=os.path.join(app.root_path, 'public/static/downloads'),
        path='Alfa Amigo.apk',  # Cambia por el nombre real de tu APK
        as_attachment=True,
        mimetype='application/vnd.android.package-archive'
    )

@app.route('/set_version/<version>')
def set_version(version):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if version in ['kids', 'adults']:
        session['version'] = version
        session.modified = True
        return redirect(request.referrer or url_for('index'))
    
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

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
            return render_template('login.html', error="Ingresa un nombre de usuario")
        
        session['user'] = {
            'name': username,
            'joined': datetime.now().strftime('%d/%m/%Y'),
            'xp': 0,
            'streak': 1,
            'completed_lessons': []
        }
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if len(username) < 3:
            return render_template('register.html', error="Mínimo 3 caracteres")
        
        session['user'] = {
            'name': username,
            'joined': datetime.now().strftime('%d/%m/%Y'),
            'xp': 0,
            'streak': 1,
            'completed_lessons': []
        }
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/lesson/<int:lesson_id>')
def lesson_detail(lesson_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    lesson = next((l for l in lessons if l.get('id') == lesson_id), None)
    if not lesson:
        return redirect(url_for('index'))
    
    return render_template('lesson_detail.html', lesson=lesson)

@app.route('/quiz/<int:lesson_id>', methods=['GET', 'POST'])
def quiz(lesson_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    lesson = next((l for l in lessons if l.get('id') == lesson_id), None)
    if not lesson:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        score = sum(
            1 for q in lesson.get('quiz', [])
            if request.form.get(f'q{q.get("id")}') == q.get('correct_answer')
        )
        
        if lesson_id not in session['user']['completed_lessons']:
            session['user']['completed_lessons'].append(lesson_id)
            session['user']['xp'] += score * 10
            session.modified = True
        
        return render_template('quiz_result.html',
                            lesson=lesson,
                            score=score,
                            total=len(lesson.get('quiz', [])))
    
    return render_template('quiz.html', lesson=lesson)

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('profile.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('version', None)
    return redirect(url_for('login'))


@app.route('/writing_practice')
def writing_practice():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('writing_practice.html')

# Configuración para producción
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
