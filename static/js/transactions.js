function removeTransaction(index) {
    log('Attempting to remove transaction:', index);
    
    // Validate index and transaction
    if (!Array.isArray(extractedTransactions) || index < 0 || index >= extractedTransactions.length) {
        log('Error: Invalid transaction index:', index);
        Swal.fire('Error', 'Invalid transaction index', 'error');
        return;
    }

    const transactionToRemove = extractedTransactions[index];
    log('Transaction to remove:', transactionToRemove);

    // Verify we have a transaction ID
    if (!transactionToRemove.id) {
        log('Error: Transaction has no ID');
        Swal.fire('Error', 'Cannot delete transaction - missing ID', 'error');
        return;
    }

    const csrfToken = document.querySelector('input[name="csrf_token"]').value;

    Swal.fire({
        title: 'Remove Transaction',
        text: 'Are you sure you want to remove this transaction?',
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Yes, remove it',
        cancelButtonText: 'Cancel',
        showLoaderOnConfirm: true,
        preConfirm: () => {
            return new Promise((resolve, reject) => {
                fetch(`/portfolio/transactions/${transactionToRemove.id}/delete`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    credentials: 'include'
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        extractedTransactions.splice(index, 1);
                        resolve(data);
                    } else {
                        reject(new Error(data.message || 'Failed to delete transaction'));
                    }
                })
                .catch(error => {
                    reject(new Error(error.message || 'Failed to delete transaction'));
                });
            });
        },
        allowOutsideClick: () => !Swal.isLoading()
    }).then((result) => {
        if (result.isConfirmed) {
            try {
                showTransactionPreview(extractedTransactions);
                log('Transaction removed successfully. Remaining:', extractedTransactions.length);
                
                Swal.fire({
                    title: 'Success',
                    text: 'Transaction removed successfully',
                    icon: 'success',
                    timer: 1500
                });
            } catch (error) {
                log('Error updating UI:', error);
                Swal.fire({
                    title: 'Warning',
                    text: 'Transaction deleted but display may be outdated. Please refresh.',
                    icon: 'warning'
                });
            }
        }
    }).catch((error) => {
        log('Error in removeTransaction:', error);
        Swal.fire({
            title: 'Error',
            text: error.message || 'Failed to delete transaction. Please try again.',
            icon: 'error'
        });
    });
}

// Add these event listeners in your document.ready function
$(document).ready(function() {
    // ... existing code ...

    // Save transaction button
    $(document).on('click', '.save-transaction', function() {
        const row = $(this).closest('tr');
        const transactionId = row.data('id');
        const transactionData = {
            date: row.find('[data-field="date"] input').val(),
            property: row.find('[data-field="property"] select').val(),
            category: row.find('[data-field="category"] select').val(),
            description: row.find('[data-field="description"] input').val(),
            debit: parseFloat(row.find('[data-field="debit"] input').val()) || 0,
            credit: parseFloat(row.find('[data-field="credit"] input').val()) || 0,
            is_reconciled: row.find('[data-field="is_reconciled"]').prop('checked')
        };

        $.ajax({
            url: `/api/transactions/${transactionId || ''}`,
            method: transactionId ? 'PUT' : 'POST',
            data: JSON.stringify(transactionData),
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
            },
            success: function(response) {
                Swal.fire({
                    icon: 'success',
                    title: 'Success',
                    text: 'Transaction saved successfully',
                    timer: 1500
                });
                if (!transactionId) {
                    row.attr('data-id', response.id);
                }
            },
            error: function(xhr) {
                Swal.fire({
                    icon: 'error',
                    title: 'Error',
                    text: 'Failed to save transaction'
                });
            }
        });
    });

    // Delete transaction button
    $(document).on('click', '.delete-transaction', function() {
        const row = $(this).closest('tr');
        const transactionId = row.data('id');

        if (!transactionId) {
            row.remove();
            return;
        }

        Swal.fire({
            title: 'Are you sure?',
            text: "You won't be able to revert this!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Yes, delete it!'
        }).then((result) => {
            if (result.isConfirmed) {
                $.ajax({
                    url: `/api/transactions/${transactionId}`,
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
                    },
                    success: function() {
                        row.remove();
                        Swal.fire(
                            'Deleted!',
                            'Transaction has been deleted.',
                            'success'
                        );
                    },
                    error: function() {
                        Swal.fire(
                            'Error!',
                            'Failed to delete transaction.',
                            'error'
                        );
                    }
                });
            }
        });
    });

    // Add row button
    $(document).on('click', '.add-row', function() {
        const newRow = $('tbody tr:first').clone();
        newRow.removeAttr('data-id');
        newRow.find('input[type="text"], input[type="number"]').val('');
        newRow.find('input[type="date"]').val(new Date().toISOString().split('T')[0]);
        newRow.find('input[type="checkbox"]').prop('checked', false);
        newRow.find('select').each(function() {
            $(this).val($(this).find('option:first').val());
        });
        $(this).closest('tr').after(newRow);
    });

    // Handle form submissions
    $('.transaction-form').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        
        $.ajax({
            url: form.attr('action'),
            method: 'POST',
            data: form.serialize(),
            success: function(response) {
                if (response.success) {
                    Swal.fire({
                        title: 'Success!',
                        text: 'Transaction saved successfully',
                        icon: 'success',
                        timer: 2000
                    });
                    // Optionally refresh the page or update the row
                    location.reload();
                } else {
                    Swal.fire({
                        title: 'Error!',
                        text: response.message || 'Failed to save transaction',
                        icon: 'error'
                    });
                }
            },
            error: function() {
                Swal.fire({
                    title: 'Error!',
                    text: 'Failed to save transaction',
                    icon: 'error'
                });
            }
        });
    });

    // Handle transaction deletion
    $('.delete-transaction').on('click', function() {
        const transactionId = $(this).data('transaction-id');
        
        Swal.fire({
            title: 'Are you sure?',
            text: "This transaction will be permanently deleted!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Yes, delete it!'
        }).then((result) => {
            if (result.isConfirmed) {
                $.ajax({
                    url: `/transactions/delete/${transactionId}`,
                    method: 'POST',
                    data: {
                        csrf_token: $('input[name=csrf_token]').val()
                    },
                    success: function(response) {
                        if (response.success) {
                            Swal.fire(
                                'Deleted!',
                                'Transaction has been deleted.',
                                'success'
                            );
                            // Remove the row from the table
                            $(`tr[data-id="${transactionId}"]`).remove();
                        } else {
                            Swal.fire(
                                'Error!',
                                response.message || 'Failed to delete transaction',
                                'error'
                            );
                        }
                    },
                    error: function() {
                        Swal.fire(
                            'Error!',
                            'Failed to delete transaction',
                            'error'
                        );
                    }
                });
            }
        });
    });
});

function addPreviewRow(transaction) {
    const row = `
        <tr>
            <td data-field="date">${transaction.transaction_date}</td>
            <td data-field="description">${transaction.description}</td>
            <td data-field="account">${transaction.account}</td>
            <td data-field="main_category">${transaction.main_category}</td>
            <td data-field="sub_category">${transaction.sub_category}</td>
            <td data-field="debit">${transaction.debit_amount}</td>
            <td data-field="credit">${transaction.credit_amount}</td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="removePreviewRow(this)">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `;
    $('#previewTransactionsBody').append(row);
}

function removePreviewRow(button) {
    $(button).closest('tr').remove();
}

function saveTransactions() {
    const transactions = [];
    
    // Collect all transaction data from the preview table
    $('#previewTransactionsBody tr').each(function() {
        const row = $(this);
        transactions.push({
            transaction_date: row.find('[data-field="date"]').text(),
            description: row.find('[data-field="description"]').text(),
            account: row.find('[data-field="account"]').text(),
            main_category: row.find('[data-field="main_category"]').text(),
            sub_category: row.find('[data-field="sub_category"]').text(),
            debit_amount: parseFloat(row.find('[data-field="debit"]').text()) || 0,
            credit_amount: parseFloat(row.find('[data-field="credit"]').text()) || 0,
            is_reconciled: false
        });
    });

    // Send the data to the server
    fetch('/transactions/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({ transactions: transactions })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire({
                icon: 'success',
                title: 'Success',
                text: 'Transactions saved successfully',
                timer: 1500
            }).then(() => {
                location.reload();
            });
        } else {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: data.message || 'Failed to save transactions'
            });
        }
    })
    .catch(error => {
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'An error occurred while saving transactions'
        });
    });
}

document.getElementById('showReconciledSwitch').addEventListener('change', function() {
    const reconciledRows = document.querySelectorAll('tr[data-reconciled="true"]');
    reconciledRows.forEach(row => {
        if (this.checked) {
            row.classList.remove('d-none');
        } else {
            row.classList.add('d-none');
        }
    });
});

// Global variables
let properties = JSON.parse(document.getElementById('propertiesData').textContent);
let accountClassifications = JSON.parse(document.getElementById('accountClassifications').textContent);

// File Upload Handling
document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('transactionFile');
    const uploadButton = document.getElementById('uploadButton');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressBar = document.getElementById('uploadProgressBar');
    const uploadStatus = document.getElementById('uploadStatus');
    const fileInfo = document.querySelector('.selected-files');

    // Drag and drop handlers
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drop-zone--over');
    });

    ['dragleave', 'dragend'].forEach(type => {
        dropZone.addEventListener(type, (e) => {
            dropZone.classList.remove('drop-zone--over');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drop-zone--over');
        
        const files = e.dataTransfer.files;
        fileInput.files = files;
        updateFileInfo(files);
    });

    fileInput.addEventListener('change', (e) => {
        updateFileInfo(e.target.files);
    });

    // File upload handling
    document.getElementById('uploadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        
        try {
            uploadProgress.classList.remove('d-none');
            const response = await uploadFiles(formData);
            
            if (response.success) {
                showPreview(response.transactions);
            } else {
                Swal.fire('Error', response.message, 'error');
            }
        } catch (error) {
            Swal.fire('Error', 'Failed to upload files', 'error');
        } finally {
            uploadProgress.classList.add('d-none');
        }
    });
});

// Transaction Management
function updateTransaction(element) {
    const row = element.closest('tr');
    const transactionId = row.dataset.id;
    const field = element.closest('td').dataset.field;
    const value = element.value;

    fetch('/api/transactions/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify({
            id: transactionId,
            field: field,
            value: value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessToast('Transaction updated successfully');
        } else {
            showErrorToast('Failed to update transaction');
        }
    })
    .catch(error => {
        showErrorToast('Error updating transaction');
    });
}

// Helper Functions
function showSuccessToast(message) {
    Swal.fire({
        toast: true,
        position: 'top-end',
        icon: 'success',
        title: message,
        showConfirmButton: false,
        timer: 3000
    });
}

function showErrorToast(message) {
    Swal.fire({
        toast: true,
        position: 'top-end',
        icon: 'error',
        title: message,
        showConfirmButton: false,
        timer: 3000
    });
}

async function uploadFiles(formData) {
    const response = await fetch('/api/transactions/upload', {
        method: 'POST',
        body: formData
    });
    return await response.json();
}

function updateFileInfo(files) {
    const fileInfo = document.querySelector('.selected-files');
    fileInfo.innerHTML = '';
    
    Array.from(files).forEach(file => {
        const fileElement = document.createElement('div');
        fileElement.className = 'selected-file';
        fileElement.innerHTML = `
            <i class="bi bi-file-earmark"></i>
            <span>${file.name}</span>
            <small>(${formatFileSize(file.size)})</small>
        `;
        fileInfo.appendChild(fileElement);
    });
    
    document.getElementById('uploadButton').disabled = files.length === 0;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
