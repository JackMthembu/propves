// Get the offer validity date from the span (make sure the format matches YYYY-MM-DDTHH:MM:SS)
const offerValidityString = document.getElementById('offerValidity').textContent;
const offerValidityDate = new Date(offerValidityString).getTime(); // This should parse correctly

// Function to start the countdown
function startCountdown() {
    const countdownElement = document.getElementById('countdown');
    const statusElement = document.getElementById('agreementStatus');

    const interval = setInterval(() => {
        const now = new Date().getTime();
        const distance = offerValidityDate - now;

        // Time calculations for days, hours, minutes, and seconds
        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);

        // Display the result in the countdown element
        countdownElement.innerHTML = `Time remaining: ${days}d ${hours}h ${minutes}m ${seconds}s`;

        // If the countdown is over, update the status and stop the timer
        if (distance < 0) {
            clearInterval(interval);
            countdownElement.innerHTML = "Offer has expired.";
            statusElement.innerHTML = "Status: Rejected";

            // Send API request to update the agreement status in the database
            fetch('/api/update-agreement-status', { // Replace with your actual API endpoint
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    agreementId: {{ agreement.id }}, // Assuming you have access to the agreement ID
                    status: 'rejected' 
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    console.log('Agreement status updated successfully.');
                    showNotification('Agreement status updated successfully.', 'success');
                } else {
                    console.error('Failed to update agreement status:', data.error);
                    showNotification('Failed to update agreement status.', 'error');
                }
            })
            .catch(error => {
                console.error('Error updating agreement status:', error);
                showNotification('Error updating agreement status: ' + error.message, 'error');
            });
        }
    }, 1000);
}

// Function to show notifications
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerText = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000); // Remove after 3 seconds
}

// Start the countdown
startCountdown();