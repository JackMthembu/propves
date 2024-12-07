document.addEventListener('DOMContentLoaded', function() {
    const overlay = document.getElementById('loadingOverlay');
    const img = new Image();
    img.src = '/static/img/background/auth-bg.jpg';
    
    img.onload = function() {
        document.body.classList.add('bg-loaded');
        overlay.classList.add('hidden');
        setTimeout(() => overlay.style.display = 'none', 300);
    };
}); 