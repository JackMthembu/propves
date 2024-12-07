document.addEventListener('DOMContentLoaded', function() {
    // Handle country selection change
    const countrySelect = document.getElementById('country');
    if (countrySelect) {
        console.log('Country select found'); // Debug log
        
        // Initial load if country is already selected
        if (countrySelect.value) {
            console.log('Initial country value:', countrySelect.value);
            updateCurrency(countrySelect.value);
        }
        
        // Add change event listener
        countrySelect.addEventListener('change', function() {
            console.log('Country changed to:', this.value);
            updateCurrency(this.value);
        });
    } else {
        console.error('Country select not found');
    }

    // Handle form submissions
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Clear previous errors
            form.querySelectorAll('.is-invalid').forEach(field => {
                field.classList.remove('is-invalid');
            });
            form.querySelectorAll('.invalid-feedback').forEach(feedback => {
                feedback.remove();
            });

            const formData = new FormData(this);
            
            // Format date if present
            const birthdayField = form.querySelector('input[type="date"]');
            if (birthdayField && birthdayField.value) {
                formData.set('birthday', birthdayField.value);
            }
            
            // Log form data for debugging
            for (let pair of formData.entries()) {
                console.log(pair[0] + ': ' + pair[1]);
            }

            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Profile updated successfully', 'success');
                } else {
                    handleFormErrors(data.error, form);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred', 'error');
            });
        });
    });

    // Handle profile picture upload
    const profilePicForm = document.getElementById('profile-pic-form');
    if (profilePicForm) {
        profilePicForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Profile picture updated successfully', 'success');
                    // Reload the page after a short delay to show the new picture
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showNotification(data.error, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred while uploading the profile picture', 'error');
            });
        });
    }

    // Handle main profile form (existing code)
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        profileForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Clear previous errors
            profileForm.querySelectorAll('.is-invalid').forEach(field => {
                field.classList.remove('is-invalid');
            });
            profileForm.querySelectorAll('.invalid-feedback').forEach(feedback => {
                feedback.remove();
            });

            const formData = new FormData(this);
            
            // Format date if present
            const birthdayField = profileForm.querySelector('input[type="date"]');
            if (birthdayField && birthdayField.value) {
                formData.set('birthday', birthdayField.value);
            }
            
            // Log form data for debugging
            for (let pair of formData.entries()) {
                console.log(pair[0] + ': ' + pair[1]);
            }

            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Profile updated successfully', 'success');
                } else {
                    handleFormErrors(data.error, profileForm);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred', 'error');
            });
        });
    }

    // Add this to validate select fields on change
    const selects = document.querySelectorAll('select[required]');
    selects.forEach(select => {
        select.addEventListener('change', function() {
            if (this.value) {
                this.classList.remove('is-invalid');
                const feedback = this.parentNode.querySelector('.invalid-feedback');
                if (feedback) {
                    feedback.remove();
                }
            }
        });
    });
});

// Function to update currency based on country selection
function updateCurrency(countryId) {
    if (!countryId) return;
    
    console.log('Fetching currency for country:', countryId); // Debug log
    
    fetch(`/api/get_currency/${countryId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Currency data received:', data); // Debug log
            
            if (data.success) {
                const currencyField = document.getElementById('currency_id');
                if (currencyField) {
                    currencyField.value = data.currency_id;
                    console.log('Currency updated to:', data.currency_id);
                }
            } else {
                console.error('Error:', data.error);
                showNotification(data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error fetching currency:', error);
            showNotification('Error updating currency', 'error');
        });
}

// Function to preview profile picture
function previewProfilePicture(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        const preview = document.getElementById('profile-picture-preview');
        
        reader.onload = function(e) {
            if (preview) {
                preview.src = e.target.result;
                preview.style.display = 'block';
            }
        }
        
        reader.readAsDataURL(file);
    }
}

// Function to show notifications
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'success' ? 'success' : 'danger'} position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '1050';
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}