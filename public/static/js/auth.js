document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = this.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Verificando...';
            
            const formData = new FormData(this);
            const errorElement = document.getElementById('loginError');
            
            try {
                const response = await fetch(this.action, {
                    method: 'POST',
                    body: formData,
                    redirect: 'manual'  // Importante para manejar redirecciones
                });
                
                if (response.type === 'opaqueredirect') {
                    // Redirección manual para SPA
                    window.location.href = response.url;
                } else if (response.ok) {
                    const data = await response.json();
                    if (data.redirect) {
                        window.location.href = data.redirect;
                    }
                } else {
                    const error = await response.json();
                    throw new Error(error.message || 'Error en el login');
                }
            } catch (error) {
                errorElement.textContent = error.message;
                errorElement.classList.remove('d-none');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Ingresar';
            }
        });
    }
});
