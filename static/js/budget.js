function handlePropertySelection(select) {
    const selectedValue = select.value;
    const row = select.closest('tr');
    const budgetAmount = row.querySelector('[data-field="budget_amount"] input').value;

    if (selectedValue === 'all') {
        const propertyCount = select.options.length - 1; // Subtract 1 for the "All Properties" option
        const distributedAmount = (parseFloat(budgetAmount) / propertyCount).toFixed(2);

        // Create new budget rows for each property
        Array.from(select.options).forEach((option, index) => {
            if (index === 0) return; // Skip "All Properties" option
            
            const newRow = row.cloneNode(true);
            const propertySelect = newRow.querySelector('.property-selector');
            propertySelect.value = option.value;
            
            // Update budget amount with distributed value
            const budgetInput = newRow.querySelector('[data-field="budget_amount"] input');
            budgetInput.value = distributedAmount;
            
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

async function saveBudget(button) {
    const row = button.closest('tr');
    const budgetId = row.querySelector('.property-selector').dataset.budgetId;
    const data = {
        property_id: row.querySelector('.property-selector').value,
        budget_type: row.querySelector('[data-field="budget_type"] select').value,
        budget_description: row.querySelector('[data-field="budget_description"] input').value,
        budget_amount: parseFloat(row.querySelector('[data-field="budget_amount"] input').value),
        actual_amount: parseFloat(row.querySelector('[data-field="actual_amount"] input').value)
    };

    try {
        const url = budgetId ? `/api/budget/${budgetId}` : '/api/budget';
        const method = budgetId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) throw new Error('Failed to save budget');

        const result = await response.json();
        
        // Update the row with new data
        if (!budgetId) {
            row.querySelector('.property-selector').dataset.budgetId = result.id;
        }

        Swal.fire({
            icon: 'success',
            title: 'Success!',
            text: 'Budget saved successfully',
            timer: 2000
        });
    } catch (error) {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to save budget'
        });
    }
}

async function deleteBudget(button) {
    const row = button.closest('tr');
    const budgetId = row.querySelector('.property-selector').dataset.budgetId;

    // If there's no budgetId, it's a new unsaved row
    if (!budgetId) {
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
            const response = await fetch(`/api/budget/${budgetId}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Failed to delete budget');

            row.remove();
            
            Swal.fire({
                icon: 'success',
                title: 'Deleted!',
                text: 'Budget has been deleted.',
                timer: 2000
            });
        }
    } catch (error) {
        console.error('Error:', error);
        Swal.fire({
            icon: 'error',
            title: 'Error',
            text: 'Failed to delete budget'
        });
    }
} 