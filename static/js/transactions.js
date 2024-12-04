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
        saveTransaction(row);
    });

    // Delete transaction button
    $(document).on('click', '.delete-transaction', function() {
        const row = $(this).closest('tr');
        deleteTransaction(row);
    });

    // Add row button
    $(document).on('click', '.add-row', function() {
        const row = $(this).closest('tr');
        addRowBelow(row);
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
