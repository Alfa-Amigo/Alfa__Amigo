// ======================
// MANEJADOR DE SESIÓN
// ======================
class AuthManager {
    static async login(username, password) {
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    username: username,
                    password: password
                })
            });

            if (response.redirected) {
                window.location.href = response.url;
                return true;
            } else {
                const data = await response.json();
                throw new Error(data.error || 'Error en el login');
            }
        } catch (error) {
            console.error('Login error:', error);
            showAlert('❌ ' + error.message, 'danger');
            return false;
        }
    }

    static async register(username, password) {
        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    username: username,
                    password: password
                })
            });

            if (response.redirected) {
                window.location.href = response.url;
                return true;
            } else {
                const data = await response.json();
                throw new Error(data.error || 'Error en el registro');
            }
        } catch (error) {
            console.error('Register error:', error);
            showAlert('❌ ' + error.message, 'danger');
            return false;
        }
    }
}

// ======================
// MANEJADOR DE PROGRESO
// ======================
class ProgressManager {
    static async saveLessonProgress(lessonId, score) {
        try {
            const response = await fetch(`/api/lessons/${lessonId}/progress`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    score: score,
                    timestamp: new Date().toISOString()
                })
            });

            if (!response.ok) {
                throw new Error('Error al guardar progreso');
            }

            return await response.json();
        } catch (error) {
            console.error('Progress save error:', error);
            return null;
        }
    }

    static async getUserProgress() {
        try {
            const response = await fetch('/api/user/progress');
            
            if (!response.ok) {
                throw new Error('Error al cargar progreso');
            }

            return await response.json();
        } catch (error) {
            console.error('Progress load error:', error);
            return { xp: 0, streak: 0, completedLessons: [] };
        }
    }
}

// ======================
// HELPERS
// ======================
function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} fixed-top mx-auto mt-3`;
    alertDiv.style.maxWidth = '500px';
    alertDiv.style.zIndex = '2000';
    alertDiv.textContent = message;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.classList.add('fade-out');
        setTimeout(() => alertDiv.remove(), 500);
    }, 3000);
}

// ======================
// INICIALIZACIÓN
// ======================
document.addEventListener('DOMContentLoaded', () => {
    // Manejadores de formularios
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = loginForm.username.value.trim();
            const password = loginForm.password.value.trim();
            await AuthManager.login(username, password);
        });
    }

    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = registerForm.username.value.trim();
            const password = registerForm.password.value.trim();
            await AuthManager.register(username, password);
        });
    }

    // Cargar progreso al iniciar
    if (document.querySelector('.profile-progress')) {
        ProgressManager.getUserProgress().then(progress => {
            updateProgressUI(progress);
        });
    }
});

function updateProgressUI(progress) {
    // Actualizar barra de progreso
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        const percentage = (progress.xp / 1000) * 100; // Asumiendo 1000 XP máximo
        progressBar.style.width = `${Math.min(percentage, 100)}%`;
        progressBar.textContent = `${progress.xp} XP`;
    }

    // Actualizar lecciones completadas
    const completedLessons = document.querySelectorAll('.lesson-completed');
    completedLessons.forEach(el => {
        if (progress.completedLessons.includes(parseInt(el.dataset.lessonId))) {
            el.classList.add('text-success');
            el.innerHTML = '<i class="fas fa-check-circle"></i> Completada';
        }
    });
}
