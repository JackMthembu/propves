(function() {
    'use strict';

    // Global variables
    let properties = JSON.parse(document.getElementById('propertiesData').textContent);
    let accountClassifications = JSON.parse(document.getElementById('accountClassifications').textContent);
    let extractedTransactions = [];

    // Utility functions
    function log(...args) {
        console.log(...args);
    }

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

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Remove transaction function
    function removeTransaction(index) {
        console.log('Attempting to remove transaction:', index);

        // Validate index and transaction
        if (!Array.isArray(extractedTransactions) || index < 0 || index >= extractedTransactions.length) {
            console.error('Error: Invalid transaction index:', index);
            Swal.fire('Error', 'Invalid transaction index', 'error');
            return;
        }

        const transactionToRemove = extractedTransactions[index];
        console.log('Transaction to remove:', transactionToRemove);

        // Verify we have a transaction ID
        if (transactionToRemove.id == null) {
            console.error('Error: Transaction has no ID');
            Swal.fire('Error', 'Cannot delete transaction - missing ID', 'error');
            return;
        }

        const csrfTokenInput = document.querySelector('input[name="csrf_token"]');
        const csrfToken = csrfTokenInput ? csrfTokenInput.value : null;
        if (!csrfToken) {
            console.error('Error: CSRF token not found');
            Swal.fire('Error', 'CSRF token not found', 'error');
            return;
        }

        Swal.fire({
            title: 'Remove Transaction',
            text: 'Are you sure you want to remove this transaction?',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes, remove it',
            cancelButtonText: 'Cancel',
            showLoaderOnConfirm: true,
            preConfirm: () => {
                return fetch(`/portfolio/transactions/${transactionToRemove.id}/delete`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    credentials: 'include'
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Network response was not ok: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        extractedTransactions.splice(index, 1);
                        return data;
                    } else {
                        throw new Error(data.message || 'Failed to delete transaction');
                    }
                })
                .catch(error => {
                    throw new Error(error.message || 'Failed to delete transaction');
                });
            },
            allowOutsideClick: () => !Swal.isLoading()
        }).then((result) => {
            if (result.isConfirmed) {
                try {
                    showTransactionPreview(extractedTransactions);
                    console.log('Transaction removed successfully. Remaining:', extractedTransactions.length);

                    Swal.fire({
                        title: 'Success',
                        text: 'Transaction removed successfully',
                        icon: 'success',
                        timer: 1500
                    });
                } catch (error) {
                    console.error('Error updating UI:', error);
                    Swal.fire({
                        title: 'Warning',
                        text: 'Transaction deleted but display may be outdated. Please refresh.',
                        icon: 'warning'
                    });
                }
            }
        }).catch((error) => {
            console.error('Error in removeTransaction:', error);
            Swal.fire({
                title: 'Error',
                text: error.message || 'Failed to delete transaction. Please try again.',
                icon: 'error'
            });
        });
    }

    // Event listeners
    $(document).ready(function() {
        // Save transaction button
        $(document).on('click', '.save-transaction', function() {
            const $row = $(this).closest('tr');
            const transactionId = $row.data('id');
            const transactionData = {
                transaction_date: $row.find('[data-field="date"] input').val(),
                property_id: $row.find('[data-field="property"] select').val(),
                account: $row.find('[data-field="account"] select').val(),
                description: $row.find('[data-field="description"] input').val(),
                debit_amount: parseFloat($row.find('[data-field="debit"] input').val()) || 0,
                credit_amount: parseFloat($row.find('[data-field="credit"] input').val()) || 0,
                is_reconciled: $row.find('[data-field="is_reconciled"] input').prop('checked')
            };

            const csrfToken = $('meta[name="csrf-token"]').attr('content');
            if (!csrfToken) {
                console.error('CSRF token not found');
                showErrorToast('CSRF token not found');
                return;
            }

            $.ajax({
                url: transactionId ? `/transactions/${transactionId}` : '/transactions/save',
                method: transactionId ? 'PUT' : 'POST',
                data: JSON.stringify(transactionData),
                contentType: 'application/json',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                success: function(response) {
                    if (response.success) {
                        showSuccessToast('Transaction saved successfully');
                        if (!transactionId && response.id) {
                            $row.attr('data-id', response.id);
                        }
                    } else {
                        showErrorToast(response.message || 'Failed to save transaction');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Save error details:', {
                        status: status,
                        error: error,
                        response: xhr.responseText
                    });
                    let responseMessage = 'Failed to save transaction';
                    try {
                        const response = JSON.parse(xhr.responseText);
                        responseMessage = response.message || responseMessage;
                    } catch (e) {
                        // Ignore parsing error
                    }
                    showErrorToast(responseMessage);
                }
            });
        });

        // Delete transaction button
        $(document).on('click', '.delete-transaction', function() {
            const $row = $(this).closest('tr');
            const transactionId = $row.data('id');

            if (!transactionId) {
                $row.remove();
                return;
            }

            const csrfToken = $('meta[name="csrf-token"]').attr('content');
            if (!csrfToken) {
                console.error('CSRF token not found');
                showErrorToast('CSRF token not found');
                return;
            }

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
                        headers: {
                            'X-CSRFToken': csrfToken
                        },
                        success: function(response) {
                            if (response.success) {
                                $row.remove();
                                Swal.fire(
                                    'Deleted!',
                                    'Transaction has been deleted.',
                                    'success'
                                );
                            } else {
                                Swal.fire(
                                    'Error!',
                                    response.message || 'Failed to delete transaction',
                                    'error'
                                );
                            }
                        },
                        error: function(xhr, status, error) {
                            console.error('Delete error details:', {
                                status: status,
                                error: error,
                                response: xhr.responseText
                            });
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

        // Add row button
        $(document).on('click', '.add-row', function() {
            const $newRow = $('tbody tr:first').clone();
            $newRow.removeAttr('data-id');
            $newRow.find('input[type="text"], input[type="number"]').val('');
            $newRow.find('input[type="date"]').val(new Date().toISOString().split('T')[0]);
            $newRow.find('input[type="checkbox"]').prop('checked', false);
            $newRow.find('select').each(function() {
                $(this).val($(this).find('option:first').val());
            });
            $(this).closest('tr').after($newRow);
        });

        // Handle form submissions
        $('.transaction-form').on('submit', function(e) {
            e.preventDefault();
            const $form = $(this);

            const csrfToken = $('meta[name="csrf-token"]').attr('content');
            if (!csrfToken) {
                console.error('CSRF token not found');
                showErrorToast('CSRF token not found');
                return;
            }

            $.ajax({
                url: $form.attr('action'),
                method: 'POST',
                data: $form.serialize(),
                headers: {
                    'X-CSRFToken': csrfToken
                },
                success: function(response) {
                    if (response.success) {
                        Swal.fire({
                            title: 'Success!',
                            text: 'Transaction saved successfully',
                            icon: 'success',
                            timer: 2000
                        }).then(() => {
                            location.reload();
                        });
                    } else {
                        Swal.fire({
                            title: 'Error!',
                            text: response.message || 'Failed to save transaction',
                            icon: 'error'
                        });
                    }
                },
                error: function(xhr, status, error) {
                    console.error('Form submission error:', {
                        status: status,
                        error: error,
                        response: xhr.responseText
                    });
                    Swal.fire({
                        title: 'Error!',
                        text: 'Failed to save transaction',
                        icon: 'error'
                    });
                }
            });
        });

        // Show reconciled transactions toggle
        $('#showReconciledSwitch').on('change', function() {
            const showReconciled = $(this).is(':checked');
            $('tr.reconciled-row').toggleClass('d-none', !showReconciled);
        });

        // Update transaction fields
        $(document).on('change', '.editable-row input, .editable-row select', function() {
            updateTransaction(this);
        });
    });

    // Update transaction function
    function updateTransaction(element) {
        const $row = $(element).closest('tr');
        const transactionId = $row.data('id');
        const field = $(element).closest('td').data('field');
        const value = $(element).is(':checkbox') ? $(element).prop('checked') : $(element).val();

        const csrfToken = $('meta[name="csrf-token"]').attr('content');
        if (!csrfToken) {
            console.error('CSRF token not found');
            showErrorToast('CSRF token not found');
            return;
        }

        fetch(`/transactions/api/transactions/${transactionId}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            body: JSON.stringify({
                field: field,
                value: value
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server error: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showSuccessToast('Transaction updated successfully');
            } else {
                showErrorToast(data.message || 'Failed to update transaction');
            }
        })
        .catch(error => {
            console.error('Error updating transaction:', error);
            showErrorToast('Error updating transaction');
        });
    }

    // File Upload Handling
    document.addEventListener('DOMContentLoaded', function() {
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('transactionFile');
        const uploadButton = document.getElementById('uploadButton');
        const uploadProgress = document.getElementById('uploadProgress');
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

                if (response.status === 'success') {
                    extractedTransactions = response.transactions;
                    showTransactionPreview(extractedTransactions);
                } else {
                    Swal.fire('Error', response.message, 'error');
                }
            } catch (error) {
                console.error('Error uploading files:', error);
                Swal.fire('Error', 'Failed to upload files', 'error');
            } finally {
                uploadProgress.classList.add('d-none');
            }
        });
    });

    function updateFileInfo(files) {
        const fileInfo = document.querySelector('.selected-files');
        fileInfo.innerHTML = '';

        const allowedExtensions = ['pdf', 'csv', 'xlsx', 'xls'];
        const maxFileSize = 5 * 1024 * 1024; // 5MB limit

        let filesValid = true;

        Array.from(files).forEach(file => {
            const fileElement = document.createElement('div');
            fileElement.className = 'selected-file';

            const fileExtension = file.name.split('.').pop().toLowerCase();
            if (!allowedExtensions.includes(fileExtension)) {
                filesValid = false;
                fileElement.innerHTML = `
                    <i class="bi bi-file-earmark-excel"></i>
                    <span>${file.name}</span>
                    <small class="text-danger">(Invalid file type)</small>
                `;
            } else if (file.size > maxFileSize) {
                filesValid = false;
                fileElement.innerHTML = `
                    <i class="bi bi-file-earmark-excel"></i>
                    <span>${file.name}</span>
                    <small class="text-danger">(File too large)</small>
                `;
            } else {
                fileElement.innerHTML = `
                    <i class="bi bi-file-earmark"></i>
                    <span>${file.name}</span>
                    <small>(${formatFileSize(file.size)})</small>
                `;
            }
            fileInfo.appendChild(fileElement);
        });

        document.getElementById('uploadButton').disabled = !filesValid || files.length === 0;
    }

    async function uploadFiles(formData) {
        const response = await fetch('/api/transactions/upload', {
            method: 'POST',
            body: formData
        });
        if (!response.ok) {
            throw new Error(`Server error: ${response.statusText}`);
        }
        return await response.json();
    }

    // Transaction Preview
    function showTransactionPreview(transactions) {
        const $tbody = $('#previewTransactionsBody');
        $tbody.empty();

        transactions.forEach((transaction, index) => {
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
                        <button class="btn btn-sm btn-danger" onclick="removePreviewRow(this, ${index})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
            $tbody.append(row);
        });
    }

    function removePreviewRow(button, index) {
        $(button).closest('tr').remove();
        extractedTransactions.splice(index, 1);
    }

    // Save transactions from preview
    function saveTransactions() {
        const csrfToken = $('meta[name="csrf-token"]').attr('content');
        if (!csrfToken) {
            console.error('CSRF token not found');
            showErrorToast('CSRF token not found');
            return;
        }

        fetch('/transactions/commit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ transactions: extractedTransactions })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server error: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
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
            console.error('Error saving transactions:', error);
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'An error occurred while saving transactions'
            });
        });
    }

    // Expose saveTransactions to global scope for button onclick
    window.saveTransactions = saveTransactions;

    document.addEventListener('DOMContentLoaded', function() {
        const saveButton = document.getElementById('saveNewTransaction');
        if (saveButton) {
            saveButton.addEventListener('click', function() {
                // Your code to handle the button click
                console.log('Save Transaction button clicked');
                // Example: Submit the form
                document.getElementById('newTransactionForm').submit();
            });
        }
    });

})();
