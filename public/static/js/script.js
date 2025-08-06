document.addEventListener('DOMContentLoaded', function() {
    // Función para manejar el slider
    function setupSlider(section) {
        const row = section.querySelector('.lesson-row');
        const prevBtn = section.querySelector('.prev-slide');
        const nextBtn = section.querySelector('.next-slide');

        // Solo configurar controles en desktop
        if (window.innerWidth >= 992) {
            let scrollPosition = 0;
            const scrollAmount = 400;

            nextBtn.addEventListener('click', () => {
                scrollPosition += scrollAmount;
                if (scrollPosition > row.scrollWidth - row.clientWidth) {
                    scrollPosition = row.scrollWidth - row.clientWidth;
                }
                row.scrollTo({
                    left: scrollPosition,
                    behavior: 'smooth'
                });
            });

            prevBtn.addEventListener('click', () => {
                scrollPosition -= scrollAmount;
                if (scrollPosition < 0) {
                    scrollPosition = 0;
                }
                row.scrollTo({
                    left: scrollPosition,
                    behavior: 'smooth'
                });
            });
        }

        // Efectos hover para todas las pantallas
        section.querySelectorAll('.lesson-card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                if (window.innerWidth >= 768) { // Solo en tablets y desktop
                    card.style.transform = 'translateY(-5px)';
                    card.style.boxShadow = '0 8px 20px rgba(0,0,0,0.12)';
                }
            });

            card.addEventListener('mouseleave', () => {
                if (window.innerWidth >= 768) {
                    card.style.transform = '';
                    card.style.boxShadow = '0 3px 10px rgba(0,0,0,0.08)';
                }
            });
        });
    }

    // Configurar todos los sliders
    document.querySelectorAll('.category-section').forEach(setupSlider);

    // Reconfigurar al cambiar tamaño de pantalla
    window.addEventListener('resize', function() {
        document.querySelectorAll('.category-section').forEach(setupSlider);
    });

    // Carga diferida de imágenes
    const lazyLoad = function() {
        const images = document.querySelectorAll('.card-img-container img[loading="lazy"]');

        images.forEach(img => {
            if (img.getAttribute('data-src') && img.getBoundingClientRect().top < window.innerHeight + 200) {
                img.setAttribute('src', img.getAttribute('data-src'));
                img.removeAttribute('data-src');
            }
        });
    };

    // Carga inicial y al hacer scroll
    lazyLoad();
    window.addEventListener('scroll', lazyLoad);
    window.addEventListener('resize', lazyLoad);
});
