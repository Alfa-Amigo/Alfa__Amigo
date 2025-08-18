// auth.js - Versión modificada para Flask
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            // Mostrar estado de carga
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Verificando...';
            
            // Ocultar mensajes de error previos
            const errorElement = document.getElementById('loginError');
            if (errorElement) {
                errorElement.classList.add('d-none');
            }
            
            // Enviar el formulario de forma tradicional
            // Flask manejará la redirección después del login
            // No necesitamos preventDefault() porque queremos el comportamiento normal
            
            // Solo como fallback, si después de 5 segundos no hubo redirección
            setTimeout(() => {
                if (submitBtn.disabled) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnText;
                    if (errorElement) {
                        errorElement.textContent = "El servidor está tardando demasiado. Intenta nuevamente.";
                        errorElement.classList.remove('d-none');
                    }
                }
            }, 5000);
        });
    }
});
