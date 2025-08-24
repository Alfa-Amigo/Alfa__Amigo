document.addEventListener('DOMContentLoaded', function() {
    // ======================
    // MANEJADOR DE SLIDERS
    // ======================
    function initSliders() {
        document.querySelectorAll('.category-section').forEach(section => {
            const slider = section.querySelector('.lesson-row');
            const prevBtn = section.querySelector('.prev-slide');
            const nextBtn = section.querySelector('.next-slide');

            if (!slider || !prevBtn || !nextBtn) return;

            let isDragging = false;
            let startPos = 0;
            let currentTranslate = 0;
            let prevTranslate = 0;

            // Touch/Desktop events
            slider.addEventListener('mousedown', dragStart);
            slider.addEventListener('touchstart', dragStart);
            slider.addEventListener('mouseup', dragEnd);
            slider.addEventListener('mouseleave', dragEnd);
            slider.addEventListener('touchend', dragEnd);
            slider.addEventListener('mousemove', drag);
            slider.addEventListener('touchmove', drag);

            // Botones de navegación
            prevBtn.addEventListener('click', () => {
                slider.scrollBy({ left: -300, behavior: 'smooth' });
            });

            nextBtn.addEventListener('click', () => {
                slider.scrollBy({ left: 300, behavior: 'smooth' });
            });

            function dragStart(e) {
                if (e.type === 'touchstart') {
                    startPos = e.touches[0].clientX;
                } else {
                    startPos = e.clientX;
                    e.preventDefault();
                }
                
                isDragging = true;
                slider.style.cursor = 'grabbing';
                slider.style.scrollBehavior = 'auto';
            }

            function drag(e) {
                if (!isDragging) return;
                const currentPosition = e.type === 'touchmove' ? e.touches[0].clientX : e.clientX;
                const diff = currentPosition - startPos;
                slider.scrollLeft = slider.scrollLeft - diff;
                startPos = currentPosition;
            }

            function dragEnd() {
                isDragging = false;
                slider.style.cursor = 'grab';
                slider.style.scrollBehavior = 'smooth';
            }
        });
    }

    // ======================
    // EFECTOS HOVER
    // ======================
    function setupHoverEffects() {
        document.querySelectorAll('.lesson-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                if (window.innerWidth >= 768) {
                    card.style.transform = 'translateY(-5px)';
                    card.style.boxShadow = '0 8px 20px rgba(0,0,0,0.12)';
                }
            });

            card.addEventListener('mouseleave', () => {
                if (window.innerWidth >= 768) {
                    card.style.transform = '';
                    card.style.boxShadow = '';
                }
            });
        });
    }

    // ======================
    // CARGA DIFERIDA DE IMÁGENES
    // ======================
    function lazyLoadImages() {
        const lazyImages = document.querySelectorAll('img[loading="lazy"]');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                    }
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '200px'
        });

        lazyImages.forEach(img => {
            if (img.dataset.src) {
                observer.observe(img);
            }
        });
    }

    // ======================
    // MANEJADOR DE QUIZ
    // ======================
    function setupQuizHandlers() {
        const quizForms = document.querySelectorAll('form[method="POST"]');
        
        quizForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                const unanswered = this.querySelectorAll('input[type="radio"]:not(:checked)').length;
                const totalQuestions = this.querySelectorAll('.quiz-question').length;
                
                if (unanswered === totalQuestions) {
                    e.preventDefault();
                    alert('⚠️ Por favor responde al menos una pregunta');
                } else if (unanswered > 0) {
                    if (!confirm(`Tienes ${unanswered} preguntas sin responder. ¿Quieres enviar igual?`)) {
                        e.preventDefault();
                    }
                }
            });
        });
    }

    // ======================
    // ANIMACIONES PARA NIÑOS
    // ======================
    function setupKidsAnimations() {
        if (document.body.classList.contains('version-kids')) {
            // Animación de rebote en las tarjetas
            document.querySelectorAll('.lesson-card').forEach(card => {
                card.addEventListener('click', function() {
                    this.style.transform = 'scale(0.95)';
                    setTimeout(() => {
                        this.style.transform = '';
                    }, 300);
                });
            });
            
            // Efectos de confeti al completar lección (simulado)
            document.querySelectorAll('.btn-primary').forEach(btn => {
                btn.addEventListener('click', function() {
                    this.style.transform = 'scale(1.05)';
                    setTimeout(() => {
                        this.style.transform = '';
                    }, 300);
                });
            });

            // Agregar animaciones a los badges
            document.querySelectorAll('.badge').forEach(badge => {
                badge.addEventListener('mouseover', function() {
                    this.style.transform = 'scale(1.1)';
                });
                badge.addEventListener('mouseout', function() {
                    this.style.transform = '';
                });
            });
        }
    }

    // ======================
    // INICIALIZACIÓN
    // ======================
    initSliders();
    setupHoverEffects();
    lazyLoadImages();
    setupQuizHandlers();
    setupKidsAnimations();

    // Re-iniciar sliders al redimensionar
    window.addEventListener('resize', initSliders);
});
