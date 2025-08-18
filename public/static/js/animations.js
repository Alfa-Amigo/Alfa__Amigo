// ======================
// EFECTOS DE INTERFAZ
// ======================
class UIEffects {
    static init() {
        this.setupCardHover();
        this.setupPageTransitions();
        this.setupProgressAnimations();
    }

    static setupCardHover() {
        document.querySelectorAll('.lesson-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                if (window.innerWidth > 768) {
                    card.style.transform = 'translateY(-10px) scale(1.02)';
                    card.style.boxShadow = '0 15px 30px rgba(0,0,0,0.1)';
                }
            });

            card.addEventListener('mouseleave', () => {
                if (window.innerWidth > 768) {
                    card.style.transform = '';
                    card.style.boxShadow = '';
                }
            });
        });
    }

    static setupPageTransitions() {
        const links = document.querySelectorAll('a:not([target="_blank"])');
        
        links.forEach(link => {
            link.addEventListener('click', (e) => {
                if (link.href && !link.href.includes('#')) {
                    e.preventDefault();
                    document.body.classList.add('page-exit');
                    
                    setTimeout(() => {
                        window.location.href = link.href;
                    }, 300);
                }
            });
        });
    }

    static setupProgressAnimations() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const progressBar = entry.target.querySelector('.progress-bar');
                    if (progressBar) {
                        const width = progressBar.style.width;
                        progressBar.style.width = '0';
                        setTimeout(() => {
                            progressBar.style.width = width;
                            progressBar.classList.add('animate-progress');
                        }, 100);
                    }
                }
            });
        }, { threshold: 0.1 });

        document.querySelectorAll('.progress-container').forEach(el => {
            observer.observe(el);
        });
    }
}

// Inicializar al cargar
document.addEventListener('DOMContentLoaded', () => UIEffects.init());
