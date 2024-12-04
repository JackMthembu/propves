document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const transactionFileInput = document.getElementById('transactionFile');
    const fileInfo = document.getElementById('fileInfo');
    const selectedFilesContainer = document.querySelector('.selected-files');
    const uploadButton = document.getElementById('uploadButton');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = document.querySelector('.progress-bar');
    const progressPercentage = document.querySelector('.progress-percentage');
    const statusText = document.querySelector('.status-text');

    // Handle file selection
    transactionFileInput?.addEventListener('change', function() {
        const files = Array.from(this.files);
        if (files.length > 0) {
            fileInfo.classList.remove('d-none');
            selectedFilesContainer.innerHTML = files.map(file => `
                <div class="file-item">
                    <i class="bi ${file.type === 'application/pdf' ? 'bi-file-pdf' : 'bi-file-spreadsheet'} me-2"></i>
                    <span class="file-name">${file.name}</span>
                </div>
            `).join('');
            uploadButton.disabled = false;
        } else {
            fileInfo.classList.add('d-none');
            uploadButton.disabled = true;
        }
    });

    // Handle form submission
    uploadForm?.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (!transactionFileInput.files.length) {
            alert('Please select a file');
            return;
        }

        const formData = new FormData();
        Array.from(transactionFileInput.files).forEach(file => {
            formData.append('files', file);
        });

        try {
            uploadProgress.classList.remove('d-none');
            uploadButton.disabled = true;
            progressBar.style.width = '0%';
            statusText.textContent = 'Uploading files...';

            const response = await fetch('/upload-transactions', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Upload failed');
            }
            
            // Show success state
            progressBar.style.width = '100%';
            progressPercentage.textContent = '100%';
            statusText.textContent = result.message || 'Files processed successfully';
            
            // Reset form after successful upload
            setTimeout(() => {
                resetUpload();
                if (result.redirect) {
                    window.location.href = result.redirect;
                }
            }, 1500);

        } catch (error) {
            console.error('Upload error:', error);
            statusText.textContent = error.message || 'Upload failed. Please try again.';
            uploadButton.disabled = false;
        }
    });

    // Reset upload form
    function resetUpload() {
        if (uploadForm) {
            uploadForm.reset();
            fileInfo.classList.add('d-none');
            selectedFilesContainer.innerHTML = '';
            uploadButton.disabled = true;
            uploadProgress.classList.add('d-none');
            progressBar.style.width = '0%';
            progressPercentage.textContent = '0%';
            statusText.textContent = 'Preparing files...';
        }
    }

    // Handle drag and drop
    const dropZone = document.getElementById('dropZone');

    if (dropZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        dropZone.addEventListener('drop', handleDrop, false);
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        dropZone?.classList.add('dragover');
    }

    function unhighlight(e) {
        dropZone?.classList.remove('dragover');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        transactionFileInput.files = files;
        transactionFileInput.dispatchEvent(new Event('change'));
    }

    // Optional: Add file size validation
    function validateFileSize(file) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            alert(`File ${file.name} is too large. Maximum size is 10MB.`);
            return false;
        }
        return true;
    }

    // Optional: Add file type validation
    function validateFileType(file) {
        const allowedTypes = [
            'application/pdf',
            'text/csv',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ];
        const allowedExtensions = ['.pdf', '.csv', '.xls', '.xlsx'];
        
        const extension = file.name.toLowerCase().split('.').pop();
        if (!allowedExtensions.includes(`.${extension}`)) {
            alert(`File ${file.name} is not supported. Please upload PDF or CSV files only.`);
            return false;
        }
        
        // Some browsers might not properly detect CSV mime type
        if (extension === 'csv' && file.type !== 'text/csv') {
            return true; // Allow CSV files even if mime type doesn't match
        }
        
        if (!allowedTypes.includes(file.type)) {
            alert(`File ${file.name} is not supported. Please upload PDF or CSV files only.`);
            return false;
        }
        
        return true;
    }
}); 