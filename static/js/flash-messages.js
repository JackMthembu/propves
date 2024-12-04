// Flash message configuration and utilities
const FlashMessages = {
    // Initialize flash messages
    init: function() {
        document.addEventListener('DOMContentLoaded', () => {
            const messages = this.getFlashMessages();
            this.displayMessages(messages);
        });
    },

    // Get flash messages from the page
    getFlashMessages: function() {
        return window.flashMessages || [];
    },

    // Display messages using SweetAlert2
    displayMessages: function(messages) {
        messages.forEach(msg => {
            this.showMessage(msg.category, msg.message);
        });
    },

    // Show individual message
    showMessage: function(category, message) {
        const messageConfig = {
            title: category.charAt(0).toUpperCase() + category.slice(1),
            text: message,
            confirmButtonText: 'OK',
            customClass: {
                confirmButton: `btn btn-${category === 'success' ? 'success' : 'danger'}`
            }
        };

        // Set icon and button color based on category
        switch(category) {
            case 'success':
                messageConfig.icon = 'success';
                messageConfig.confirmButtonColor = '#28a745';
                break;
            case 'error':
            case 'danger':
                messageConfig.icon = 'error';
                messageConfig.confirmButtonColor = '#dc3545';
                break;
            case 'warning':
                messageConfig.icon = 'warning';
                messageConfig.confirmButtonColor = '#ffc107';
                break;
            case 'info':
                messageConfig.icon = 'info';
                messageConfig.confirmButtonColor = '#17a2b8';
                break;
            default:
                messageConfig.icon = 'info';
                messageConfig.confirmButtonColor = '#6c757d';
        }

        Swal.fire(messageConfig);
    }
};

// Initialize flash messages
FlashMessages.init();

// Export for use in other files
window.FlashMessages = FlashMessages; 