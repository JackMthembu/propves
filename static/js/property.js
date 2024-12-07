function openPhotoModal(src) {
    const modal = new bootstrap.Modal(document.getElementById('photoModal'));
    document.getElementById('modalImage').src = src;
    modal.show();
}

// Add keyboard navigation
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modal = bootstrap.Modal.getInstance(document.getElementById('photoModal'));
        if (modal) modal.hide();
    }
});

// Add zoom functionality
document.getElementById('modalImage').addEventListener('click', function() {
    this.classList.toggle('zoomed');
});

// Add touch support
let touchStart = null;
let currentScale = 1;
const modalImage = document.getElementById('modalImage');

modalImage.addEventListener('touchstart', function(e) {
    if (e.touches.length === 2) {
        touchStart = getDistance(e.touches[0], e.touches[1]);
    }
});

modalImage.addEventListener('touchmove', function(e) {
    if (touchStart && e.touches.length === 2) {
        e.preventDefault();
        const currentDistance = getDistance(e.touches[0], e.touches[1]);
        const scale = currentScale * (currentDistance / touchStart);
        modalImage.style.transform = `scale(${Math.min(Math.max(1, scale), 3)})`;
    }
});

modalImage.addEventListener('touchend', function() {
    touchStart = null;
    currentScale = parseFloat(modalImage.style.transform.replace('scale(', '')) || 1;
});

function getDistance(touch1, touch2) {
    return Math.hypot(touch2.pageX - touch1.pageX, touch2.pageY - touch1.pageY);
} 

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Property deletion function
function deleteProperty(propertyId) {
    console.log('Starting delete process for property:', propertyId);

    Swal.fire({
        title: 'Delete Property?',
        text: "This will permanently delete the property and all associated data (photos, listings, rental agreements). This action cannot be undone!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!',
        cancelButtonText: 'Cancel',
        reverseButtons: true
    }).then((result) => {
        if (result.isConfirmed) {
            console.log('Delete confirmed by user');
            
            // Create form data with CSRF token
            const formData = new FormData();
            formData.append('csrf_token', document.querySelector('meta[name="csrf-token"]').getAttribute('content'));
            
            // Make the delete request
            fetch(`/property/delete/${propertyId}`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: formData
            })
            .then(response => {
                console.log('Received response:', response);
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                console.log('Processed data:', data);
                
                if (data.success) {
                    Swal.fire({
                        title: 'Deleted!',
                        text: 'Property has been deleted successfully.',
                        icon: 'success',
                        confirmButtonColor: '#28a745'
                    }).then(() => {
                        window.location.href = '/property/list';
                    });
                } else {
                    throw new Error(data.error || 'Failed to delete property');
                }
            })
            .catch(error => {
                console.error('Error during deletion:', error);
                Swal.fire({
                    title: 'Error!',
                    text: error.message || 'An unexpected error occurred while deleting the property.',
                    icon: 'error',
                    confirmButtonColor: '#dc3545'
                });
            });
        }
    });
}

// Function to handle PDF upload and data extraction
function handlePDFUpload(event) {
    event.preventDefault();
    
    const formData = new FormData();
    const fileInput = document.querySelector('input[type="file"]');
    formData.append('document', fileInput.files[0]);

    // Show loading state
    const loadingElement = document.getElementById('loading-indicator');
    if (loadingElement) loadingElement.style.display = 'block';

    fetch(event.target.action, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Received data:', data); // Debug log
        
        if (data.success) {
            // Populate form fields with extracted values
            const totals = data.totals;
            
            // Map the extracted categories to form field IDs
            const fieldMapping = {
                'Maintenance': 'maintenance',
                'Security': 'staff_cost', // Assuming security maps to staff_cost
                'Property Management': 'management_fee',
                'Reserve Fund': 'reserve_fund',
                'Insurance': 'insurance'
                // Add more mappings as needed
            };

            // Update form fields
            Object.entries(fieldMapping).forEach(([category, fieldId]) => {
                const value = totals[category] || 0;
                const input = document.getElementById(fieldId);
                if (input) {
                    input.value = value.toFixed(2);
                }
            });

            // Show success message
            showAlert('Data extracted successfully!', 'success');
        } else {
            // Show error message
            showAlert(data.error || 'Failed to extract data from PDF', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('An error occurred while processing the PDF', 'error');
    })
    .finally(() => {
        // Hide loading state
        if (loadingElement) loadingElement.style.display = 'none';
    });
}

// Helper function to show alerts
function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Add event listener to the form
document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            if (e.target.querySelector('input[type="file"]').files.length > 0) {
                handlePDFUpload(e);
                e.preventDefault();
            }
        });
    }
});

// Add this function to handle the property save response
function handlePropertySave(data) {
    if (data.success) {
        Swal.fire({
            title: 'Success!',
            text: data.message,
            icon: 'success',
            confirmButtonText: 'OK',
            confirmButtonColor: '#28a745'
        }).then(() => {
            // Redirect to manage property page
            window.location.href = `/property/manage/${data.property_id}`;
        });
    } else {
        // Handle validation errors
        if (data.errors) {
            // Display validation errors next to form fields
            Object.keys(data.errors).forEach(field => {
                const input = document.querySelector(`[name="${field}"]`);
                if (input) {
                    input.classList.add('is-invalid');
                    const feedback = input.nextElementSibling;
                    if (feedback && feedback.classList.contains('invalid-feedback')) {
                        feedback.textContent = data.errors[field].join(', ');
                    }
                }
            });
        }
        
        Swal.fire({
            title: 'Error!',
            text: data.message || 'Please check the form for errors',
            icon: 'error',
            confirmButtonText: 'OK',
            confirmButtonColor: '#dc3545'
        });
    }
}

// Modify your existing save property function
function saveProperty(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire({
                title: 'Success!',
                text: data.message,
                icon: 'success',
                confirmButtonText: 'OK',
                confirmButtonColor: '#28a745'
            }).then(() => {
                // Use the redirect URL from the response
                if (data.redirect_url) {
                    window.location.href = data.redirect_url;
                } else {
                    window.location.href = `/property/manage/${data.property_id}`;
                }
            });
        } else {
            Swal.fire({
                title: 'Error!',
                text: data.message || 'An error occurred',
                icon: 'error',
                confirmButtonText: 'OK',
                confirmButtonColor: '#dc3545'
            });
        }
    })
    .catch(error => {
        console.error('Error:', error);
        Swal.fire({
            title: 'Error!',
            text: 'An unexpected error occurred',
            icon: 'error',
            confirmButtonText: 'OK',
            confirmButtonColor: '#dc3545'
        });
    });
}

// Photo error handling and modal functions
function handleImageError(imgElement) {
    console.log('Error loading image:', imgElement.src);
    imgElement.onerror = null; // Prevent infinite loop
    imgElement.src = '/static/uploads/property_photos/default.png';
    imgElement.classList.add('error-image');
}

function openPhotoModal(imageSrc) {
    Swal.fire({
        imageUrl: imageSrc,
        imageAlt: 'Property Photo',
        width: '80%',
        showCloseButton: true,
        showConfirmButton: false,
        customClass: {
            image: 'img-fluid',
            popup: 'photo-modal'
        },
        imageClass: 'img-fluid',
        errorHtml: `
            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle"></i>
                Failed to load image
            </div>
        `
    });
}
