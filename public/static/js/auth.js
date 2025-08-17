// Guardar progreso del usuario
async function saveProgress(score, level) {
    try {
        const response = await fetch('/api/save_progress', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ score, level })
        });
        
        if (!response.ok) {
            throw new Error('Error al guardar progreso');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        return null;
    }
}

// Cargar progreso del usuario
async function loadProgress() {
    try {
        const response = await fetch('/api/load_progress');
        
        if (!response.ok) {
            throw new Error('Error al cargar progreso');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Error:', error);
        return { score: 0, level: 1 }; // Valores por defecto
    }
}

// Ejemplo de uso:
// Cuando el usuario complete un nivel:
// await saveProgress(nuevoPuntaje, nuevoNivel);

// Al cargar la página:
// const progress = await loadProgress();
// console.log('Progreso actual:', progress);
