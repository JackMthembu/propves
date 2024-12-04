function handleFileUpload(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const propertyId = document.getElementById('propertyId').value;
    
    fetch(`/accounting_routes/property/${propertyId}/monthly-expenses`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        console.log('Response data:', data); // Debug log
        
        // Check both success flag and totals existence
        if (data && data.totals) {  // Removed data.success check since it might not be needed
            // Map the extracted data to form fields
            const form = document.getElementById('expenseUploadForm');
            if (data.totals.Maintenance) form.levies.value = data.totals.Maintenance;
            if (data.totals.Security) form.security.value = data.totals.Security;
            if (data.totals['Property Management']) form.rates_taxes.value = data.totals['Property Management'];
            if (data.totals['Reserve Fund']) form.special_leveies.value = data.totals['Reserve Fund'];
            if (data.totals.Insurance) form.other.value = data.totals.Insurance;
            
            // Display the extracted data
            displayExpenses(data.totals);
            showSuccessMessage('Data extracted successfully');
        } else {
            // Error case
            const errorMsg = data.error || 'Failed to extract data';
            showErrorMessage(errorMsg);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showErrorMessage('Failed to process the file');
    });
}

function displayExpenses(totals) {
    const container = document.getElementById('expensesContainer');
    container.innerHTML = ''; // Clear previous content
    
    // Create a table to display the expenses
    const table = document.createElement('table');
    table.className = 'table table-striped';
    
    // Add header
    const header = `
        <thead>
            <tr>
                <th>Expense Type</th>
                <th class="text-end">Amount</th>
            </tr>
        </thead>
    `;
    
    // Add body
    let rows = '';
    for (const [category, amount] of Object.entries(totals)) {
        if (category !== 'Total') { // Skip total in the main list
            rows += `
                <tr>
                    <td>${category}</td>
                    <td class="text-end">$${amount.toFixed(2)}</td>
                </tr>
            `;
        }
    }
    
    // Add total row
    if (totals.Total) {
        rows += `
            <tr class="table-primary">
                <th>Total</th>
                <th class="text-end">$${totals.Total.toFixed(2)}</th>
            </tr>
        `;
    }
    
    table.innerHTML = header + `<tbody>${rows}</tbody>`;
    container.appendChild(table);
}

function showErrorMessage(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.getElementById('alertContainer');
    container.innerHTML = '';
    container.appendChild(alertDiv);
}

function showSuccessMessage(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.getElementById('alertContainer');
    container.innerHTML = '';
    container.appendChild(alertDiv);
}

// Add these functions to handle the exports
function exportToExcel() {
    // Show loading indicator
    const loadingToast = showToast('Generating Excel file...', 'info');
    
    fetch('/accounting_routes/export/excel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            property_expenses: getPropertyExpensesData(),
            total_expenses: getTotalExpensesData()
        })
    })
    .then(response => response.blob())
    .then(blob => {
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `expenses_report_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        
        // Hide loading indicator and show success message
        loadingToast.hide();
        showToast('Excel file downloaded successfully!', 'success');
    })
    .catch(error => {
        console.error('Export error:', error);
        loadingToast.hide();
        showToast('Failed to generate Excel file. Please try again.', 'error');
    });
}

function exportToPDF() {
    // Show loading indicator
    const loadingToast = showToast('Generating PDF file...', 'info');
    
    fetch('/accounting_routes/export/pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            property_expenses: getPropertyExpensesData(),
            total_expenses: getTotalExpensesData()
        })
    })
    .then(response => response.blob())
    .then(blob => {
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `expenses_report_${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
        
        // Hide loading indicator and show success message
        loadingToast.hide();
        showToast('PDF file downloaded successfully!', 'success');
    })
    .catch(error => {
        console.error('Export error:', error);
        loadingToast.hide();
        showToast('Failed to generate PDF file. Please try again.', 'error');
    });
}

// Helper function to show toast notifications
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    return bsToast;
}

// Helper function to create toast container
function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

// Helper functions to get data
function getPropertyExpensesData() {
    // Get data from the property expenses table
    const data = {};
    document.querySelectorAll('#property-expenses .card').forEach(card => {
        const propertyName = card.querySelector('.card-title').textContent.trim();
        const expenses = {};
        
        card.querySelectorAll('tbody tr').forEach(row => {
            const type = row.cells[0].textContent.trim();
            const amount = parseFloat(row.cells[1].textContent.replace(/[^0-9.-]+/g, ''));
            expenses[type] = amount;
        });
        
        data[propertyName] = expenses;
    });
    return data;
}

function getTotalExpensesData() {
    // Get data from the total summary table
    const data = {};
    document.querySelectorAll('#total-summary tbody tr').forEach(row => {
        const type = row.cells[0].textContent.trim();
        const amount = parseFloat(row.cells[1].textContent.replace(/[^0-9.-]+/g, ''));
        data[type] = amount;
    });
    return data;
} 