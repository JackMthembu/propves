export const showAlert = (type, message, container) => {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.innerHTML = '';
    container.appendChild(alertDiv);
};

export const formatCurrency = (amount, symbol = '$') => {
    return `${symbol}${parseFloat(amount || 0).toFixed(2)}`;
};

// ... other shared utilities 