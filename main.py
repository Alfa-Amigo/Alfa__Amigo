from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from pathlib import Path

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this for production!

# Configure absolute paths
BASE_DIR = Path(__file__).parent.absolute()
JSON_PATH = BASE_DIR / 'public' / 'static' / 'data' / 'lessons.json'

# Create directories if they don't exist
os.makedirs(BASE_DIR / 'public' / 'static' / 'data', exist_ok=True)

# In-memory user database
users = {
    'admin': {
        'password': generate_password_hash('admin123'),
        'name': 'Administrator',
        'xp': 100,
        'streak': 5,
        'completed_lessons': []
    }
}

def load_lessons():
    try:
        if not JSON_PATH.exists():
            raise FileNotFoundError(f"JSON file not found at {JSON_PATH}")
            
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            lessons = json.load(f)
            print(f"Successfully loaded {len(lessons)} lessons")
            return lessons
    except Exception as e:
        print(f"Error loading lessons: {str(e)}")
        # Fallback data
        return [
            {
                "id": 1,
                "title": "Sample Lesson",
                "description": "This is a sample lesson",
                "category": "General",
                "content": [{"type": "text", "content": "Sample content"}],
                "quiz": [
                    {
                        "id": 1,
                        "question": "Sample question",
                        "options": ["Option 1", "Option 2"],
                        "correct_answer": "Option 1"
                    }
                ]
            }
        ]

LESSONS = load_lessons()

# Authentication decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page', 'warning')
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
            flash('Login successful!', 'success')
            next_page = request.args.get('next', url_for('index'))
            return redirect(next_page)
        
        flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if len(username) < 4:
            flash('Username must be at least 4 characters', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match', 'danger')
        elif username in users:
            flash('Username already exists', 'danger')
        else:
            users[username] = {
                'password': generate_password_hash(password),
                'name': username,
                'xp': 0,
                'streak': 0,
                'completed_lessons': []
            }
            flash('Registration successful! Please login', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/profile')
@login_required
def profile():
    user = users.get(session['username'], {})
    return render_template('profile.html',
        user=user,
        completed_lessons=user.get('completed_lessons', [])
    )

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson_detail(lesson_id):
    lesson = next((l for l in LESSONS if l.get('id') == lesson_id), None)
    if not lesson:
        flash('Lesson not found', 'danger')
        return redirect(url_for('index'))
    return render_template('lesson_detail.html', lesson=lesson)

@app.route('/lesson/<int:lesson_id>/quiz', methods=['GET', 'POST'])
@login_required
def quiz(lesson_id):
    lesson = next((l for l in LESSONS if l.get('id') == lesson_id), None)
    if not lesson:
        flash('Lesson not found', 'danger')
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
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
