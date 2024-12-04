document.addEventListener('DOMContentLoaded', function() {
    const thumbnailDrop = document.getElementById('thumbnailDrop');
    const photosDrop = document.getElementById('photosDrop');
    const thumbnailInput = document.getElementById('thumbnail');
    const photosInput = document.getElementById('photos');
    const thumbnailPreview = document.getElementById('thumbnail-preview');
    const photosPreview = document.getElementById('photos-preview');

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        thumbnailDrop.addEventListener(eventName, preventDefaults, false);
        photosDrop.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight drop zone when dragging over it
    ['dragenter', 'dragover'].forEach(eventName => {
        thumbnailDrop.addEventListener(eventName, highlight, false);
        photosDrop.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        thumbnailDrop.addEventListener(eventName, unhighlight, false);
        photosDrop.addEventListener(eventName, unhighlight, false);
    });

    function highlight(e) {
        e.target.closest('.upload-area').classList.add('dragover');
    }

    function unhighlight(e) {
        e.target.closest('.upload-area').classList.remove('dragover');
    }

    // Handle dropped files
    thumbnailDrop.addEventListener('drop', handleThumbnailDrop, false);
    photosDrop.addEventListener('drop', handlePhotosDrop, false);

    function handleThumbnailDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        thumbnailInput.files = files;
        handleFiles(thumbnailInput);
    }

    function handlePhotosDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        photosInput.files = files;
        handleFiles(photosInput);
    }

    // Handle selected files
    thumbnailInput.addEventListener('change', function() {
        handleFiles(this);
    });

    photosInput.addEventListener('change', function() {
        handleFiles(this);
    });

    function handleFiles(input) {
        const files = input.files;
        const previewContainer = input.id === 'thumbnail' ? thumbnailPreview : photosPreview;
        
        if (input.id === 'thumbnail') {
            previewContainer.innerHTML = ''; // Clear previous thumbnail
        }

        Array.from(files).forEach(file => {
            if (!file.type.startsWith('image/')) {
                alert('Please upload only image files.');
                return;
            }

            const reader = new FileReader();
            const previewItem = document.createElement('div');
            previewItem.className = 'preview-item';

            reader.onload = (e) => {
                previewItem.innerHTML = `
                    <img src="${e.target.result}" alt="Preview">
                    <button type="button" class="delete-btn" onclick="removePreview(this)">
                        <i class="bi bi-trash"></i>
                    </button>
                `;
                previewContainer.appendChild(previewItem);
            };

            reader.readAsDataURL(file);
        });
    }
});

// These functions need to be global since they're called from HTML
window.removePreview = function(button) {
    const previewItem = button.parentElement;
    const container = previewItem.parentElement;
    const input = container.id === 'thumbnail-preview' ? 
        document.getElementById('thumbnail') : 
        document.getElementById('photos');

    previewItem.remove();

    // Clear the file input if it's a thumbnail
    if (container.id === 'thumbnail-preview') {
        input.value = '';
    }
}

window.submitPhotos = function(event) {
    const thumbnailPreview = document.getElementById('thumbnail-preview');
    const photosPreview = document.getElementById('photos-preview');

    if (thumbnailPreview.children.length === 0) {
        alert('Please upload a thumbnail image');
        return false;
    }

    if (photosPreview.children.length === 0) {
        alert('Please upload at least one property photo');
        return false;
    }

    return true;
} 