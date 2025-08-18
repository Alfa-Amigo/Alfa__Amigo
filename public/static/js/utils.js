// ======================
// MANEJO DE FECHAS
// ======================
class DateUtils {
    static formatDate(date, format = 'es-MX') {
        const options = {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        };
        return new Date(date).toLocaleDateString(format, options);
    }

    static calculateStreak(lastLogin) {
        const today = new Date();
        const lastDate = new Date(lastLogin);
        const diffTime = today - lastDate;
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
        
        return diffDays === 1 ? 1 : 0; // Devuelve 1 si inició sesión ayer, 0 si no
    }
}

// ======================
# MANEJO DEL DOM
# ======================
class DOMHelpers {
    static showLoading(container = document.body) {
        const loader = document.createElement('div');
        loader.className = 'loading-overlay';
        loader.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Cargando...</span>
            </div>
        `;
        container.appendChild(loader);
        return loader;
    }

    static hideLoading(loader) {
        if (loader) {
            loader.classList.add('fade-out');
            setTimeout(() => loader.remove(), 300);
        }
    }

    static toggleElement(elementId, show = true) {
        const el = document.getElementById(elementId);
        if (el) {
            el.style.display = show ? 'block' : 'none';
        }
    }
}

# ======================
# MANEJO DE API
# ======================
class API {
    static async fetchJSON(endpoint, options = {}) {
        try {
            const response = await fetch(endpoint, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Error en ${endpoint}:`, error);
            throw error;
        }
    }

    static async postFormData(endpoint, formData) {
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error enviando formulario:', error);
            throw error;
        }
    }
}

# ======================
# MANEJO DE NOTIFICACIONES
# ======================
class Notify {
    static show(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas ${this.getIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;

        document.body.appendChild(notification);
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, duration);

        return notification;
    }

    static getIcon(type) {
        const icons = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-circle',
            'warning': 'fa-exclamation-triangle',
            'info': 'fa-info-circle'
        };
        return icons[type] || 'fa-info-circle';
    }
}

# ======================
# MANEJO DE FORMULARIOS
# ======================
class FormUtils {
    static serializeForm(formElement) {
        const formData = new FormData(formElement);
        return Object.fromEntries(formData.entries());
    }

    static validateForm(formElement, rules) {
        let isValid = true;
        const errors = {};
        const formData = this.serializeForm(formElement);

        for (const [field, validation] of Object.entries(rules)) {
            const value = formData[field];
            
            if (validation.required && !value) {
                errors[field] = validation.messages?.required || 'Este campo es requerido';
                isValid = false;
            }

            if (validation.minLength && value && value.length < validation.minLength) {
                errors[field] = validation.messages?.minLength || `Mínimo ${validation.minLength} caracteres`;
                isValid = false;
            }

            if (validation.pattern && value && !validation.pattern.test(value)) {
                errors[field] = validation.messages?.pattern || 'Formato inválido';
                isValid = false;
            }
        }

        return { isValid, errors };
    }

    static clearForm(formElement) {
        formElement.reset();
        formElement.querySelectorAll('.is-invalid').forEach(el => {
            el.classList.remove('is-invalid');
        });
    }
}

# ======================
# MANEJO DE SESIÓN
# ======================
class Session {
    static getToken() {
        return localStorage.getItem('authToken');
    }

    static setToken(token) {
        localStorage.setItem('authToken', token);
    }

    static clear() {
        localStorage.removeItem('authToken');
    }

    static isAuthenticated() {
        return !!this.getToken();
    }
}

# ======================
# EXPORTACIÓN (si usas módulos)
# ======================
export {
    DateUtils,
    DOMHelpers,
    API,
    Notify,
    FormUtils,
    Session
};

# ======================
# INICIALIZACIÓN GLOBAL (para uso sin módulos)
# ======================
window.AppUtils = {
    DateUtils,
    DOMHelpers,
    API,
    Notify,
    FormUtils,
    Session
};
