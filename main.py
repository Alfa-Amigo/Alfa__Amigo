from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_por_defecto')


with open('data/lessons.json', 'r', encoding='utf-8') as f:
    lessons = json.load(f)

@app.context_processor
def inject_global_data():
    return {
        'user': session.get('user'),
        'categories': ['Lectura', 'Matemáticas', 'Escritura', 'vocabulario'],
        'category_icons': {
            'Lectura': 'book-open',
            'Matemáticas': 'calculator',
            'Escritura': 'pen'
            
        },
        'lessons': lessons
    }

# Rutas
@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', 'Usuario').strip()
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
        score = sum(1 for q in lesson['quiz'] if request.form.get(f'q{q["id"]}') == q['correct_answer'])

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
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080) 