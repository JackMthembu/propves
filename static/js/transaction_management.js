function handlePropertySelection(select) {
    const selectedValue = select.value;
    const row = select.closest('tr');
    const transactionAmount = row.querySelector('[data-field="amount"] input').value;

    if (selectedValue === 'all') {
        const propertyCount = select.options.length - 1; // Subtract 1 for the "All Properties" option
        const distributedAmount = (parseFloat(transactionAmount) / propertyCount).toFixed(2);

        // Create new transaction rows for each property
        Array.from(select.options).forEach((option, index) => {
            if (index === 0) return; // Skip "All Properties" option
            
            const newRow = row.cloneNode(true);
            const propertySelect = newRow.querySelector('.property-selector');
            propertySelect.value = option.value;
            
            // Update transaction amount with distributed value
            const amountInput = newRow.querySelector('[data-field="amount"] input');
            amountInput.value = distributedAmount;
            
            row.parentNode.insertBefore(newRow, row.nextSibling);
        });

        // Remove the original row
        row.remove();
    }
}

// Add event listener to property selectors
document.querySelectorAll('.property-selector').forEach(select => {
    select.addEventListener('change', () => handlePropertySelection(select));
});

async function saveTransaction(button) {
    const row = button.closest('tr');
    const transactionId = row.querySelector('.property-selector').dataset.transactionId;
    const data = {
        property_id: row.querySelector('.property-selector').value,
        transaction_date: row.querySelector('[data-field="transaction_date"] input').value,
        description: row.querySelector('[data-field="description"] input').value,
        amount: parseFloat(row.querySelector('[data-field="amount"] input').value),
        is_reconciled: row.querySelector('[data-field="is_reconciled"] input').checked
    };

    try {
        const url = transactionId ? `/api/transaction/${transactionId}` : '/api/transaction';
        const method = transactionId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) throw new Error('Failed to save transaction');

        const result = await response.json();
        
        // Update the row with new data
        if (!transactionId) {
            row.querySelector('.property-selector').dataset.transactionId = result.id;
        }

        Swal.fire({
            icon: 'success',
            title: 'Success!',
            text: 'Transaction saved successfully',
            timer: 2000
        });
    } catch (error) {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to save transaction'
        });
    }
}

async function deleteTransaction(button) {
    const row = button.closest('tr');
    const transactionId = row.querySelector('.property-selector').dataset.transactionId;

    // If there's no transactionId, it's a new unsaved row
    if (!transactionId) {
        row.remove();
        return;
    }

    try {
        const result = await Swal.fire({
            title: 'Are you sure?',
            text: "You won't be able to revert this!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Yes, delete it!'
        });

        if (result.isConfirmed) {
            const response = await fetch(`/api/transaction/${transactionId}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Failed to delete transaction');

            row.remove();
            
            Swal.fire({
                icon: 'success',
                title: 'Deleted!',
                text: 'Transaction has been deleted.',
                timer: 2000
            });
        }
    } catch (error) {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to delete transaction'
        });
    }
}
