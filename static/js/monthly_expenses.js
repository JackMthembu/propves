document.addEventListener('DOMContentLoaded', function() {
    // Get required elements
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('document');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const uploadButton = document.getElementById('uploadButton');
    const removeFileBtn = document.getElementById('removeFile');
    const uploadForm = document.getElementById('uploadForm');

    let isSubmitting = false;

    // Add necessary styles
    const style = document.createElement('style');
    style.textContent = `
        .drop-zone {
            min-height: 200px;
            border: 2px dashed #ccc;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background-color: #f8f9fa;
            margin-bottom: 1rem;
        }

        .drop-zone--over {
            border-color: #0d6efd;
            background-color: rgba(13, 110, 253, 0.05);
        }

        .drop-zone--accepted {
            border-color: #198754;
            background-color: rgba(25, 135, 84, 0.05);
        }

        .drop-zone__prompt {
            text-align: center;
            padding: 2rem;
        }

        .drop-zone__prompt i {
            font-size: 2.5rem;
            color: #6c757d;
            margin-bottom: 1rem;
        }

        .drop-zone__prompt p {
            margin-bottom: 0.5rem;
            color: #495057;
        }
    `;
    document.head.appendChild(style);

    // Initialize drag and drop
    if (dropZone) {
        // Make dropzone clickable
        dropZone.addEventListener('click', () => fileInput.click());

        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults);
            document.body.addEventListener(eventName, preventDefaults);
        });

        // Handle drag and drop events
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight);
        });

        // Handle file selection
        fileInput.addEventListener('change', handleFiles);
        dropZone.addEventListener('drop', handleDrop);
        removeFileBtn.addEventListener('click', removeFile);
    }

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        preventDefaults(e);
        dropZone.classList.add('drop-zone--over');
    }

    function unhighlight(e) {
        preventDefaults(e);
        dropZone.classList.remove('drop-zone--over');
    }

    function handleDrop(e) {
        preventDefaults(e);
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles({ target: { files: files } });
    }

    function handleFiles(e) {
        const file = e.target.files[0];
        if (file && file.type === 'application/pdf') {
            fileName.textContent = file.name;
            fileInfo.classList.remove('d-none');
            uploadButton.disabled = false;
            dropZone.classList.add('drop-zone--accepted');
        } else {
            showAlert('danger', 'Please select a PDF file');
            removeFile();
        }
    }

    function removeFile() {
        fileInput.value = '';
        fileInfo.classList.add('d-none');
        uploadButton.disabled = true;
        dropZone.classList.remove('drop-zone--accepted');
        dropZone.classList.remove('drop-zone--over');
    }

    // Define the field mappings
    const FIELD_MAPPINGS = {
        'hoa_fees': 'Association Fees',
        'maintenance': 'Maintenance',
        'staff_cost': 'Staff Cost',
        'management_fee': 'Management Fee',
        'reserve_fund': 'Reserve Fund',
        'special_assessments': 'Special Assessments',
        'amenities': 'Amenities',
        'other_expenses': 'Other Expenses',
        'insurance': 'Insurance',
        'property_taxes': 'Property Taxes',
        'electricity': 'Electricity',
        'gas': 'Gas',
        'water_sewer': 'Water & Sewer',
        'miscellaneous_cost': 'Miscellaneous',
        'other_city_charges': 'City Charges'
    };

    async function handleFormSubmit(e) {
        e.preventDefault();
        
        if (isSubmitting || !fileInput.files[0]) return;

        try {
            isSubmitting = true;
            uploadButton.disabled = true;
            uploadButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Processing...';
            
            const formData = new FormData(uploadForm);
            
            const response = await fetch(window.location.href, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            console.log('Server response:', result); // Debug log
            
            if (result.success && (result.extracted_data || result.totals)) {
                const data = result.extracted_data || result.totals;
                fillFormWithData(data);
                displayExpenses(data);
                showAlert('success', 'Data has been successfully extracted and filled in the form!');
                removeFile();
            } else {
                throw new Error(result.error || 'Failed to extract data');
            }
        } catch (error) {
            console.error('Error:', error);
            showAlert('danger', error.message);
        } finally {
            isSubmitting = false;
            uploadButton.disabled = false;
            uploadButton.innerHTML = '<i class="bi bi-upload"></i> Upload & Extract';
        }
    }

    function fillFormWithData(data) {
        console.log('Filling form with data:', data); // Debug log
        
        // Loop through each form field and try to find matching data
        Object.entries(FIELD_MAPPINGS).forEach(([fieldName, displayName]) => {
            const input = document.querySelector(`input[name="${fieldName}"]`);
            if (!input) {
                console.log(`No input found for field: ${fieldName}`);
                return;
            }

            // Try different possible keys for the data
            const value = data[displayName] || data[fieldName] || data[displayName.toLowerCase()];
            if (value !== undefined) {
                input.value = parseFloat(value).toFixed(2);
                console.log(`Set ${fieldName} to ${value}`);
            }
        });

        // Update total after filling form
        updateTotalExpenses();
    }

    function displayExpenses(data) {
        const container = document.getElementById('expensesContainer');
        if (!container) {
            console.log('Expenses container not found');
            return;
        }
        
        container.innerHTML = ''; // Clear previous content
        
        const table = document.createElement('table');
        table.className = 'table table-striped mt-3';
        
        let html = `
            <thead>
                <tr>
                    <th>Expense Type</th>
                    <th class="text-end">Amount</th>
                </tr>
            </thead>
            <tbody>
        `;
        
        Object.entries(data).forEach(([category, amount]) => {
            if (category.toLowerCase() !== 'total') {
                html += `
                    <tr>
                        <td>${category}</td>
                        <td class="text-end">${formatCurrency(amount)}</td>
                    </tr>
                `;
            }
        });
        
        // Add total row if exists
        const total = Object.values(data).reduce((sum, val) => sum + (parseFloat(val) || 0), 0);
        if (total > 0) {
            html += `
                <tr class="table-primary">
                    <th>Total</th>
                    <th class="text-end">${formatCurrency(total)}</th>
                </tr>
            `;
        }
        
        html += '</tbody>';
        table.innerHTML = html;
        container.appendChild(table);
    }

    function formatCurrency(value) {
        const currencySymbol = document.querySelector('meta[name="currency-symbol"]')?.content || '$';
        return `${currencySymbol}${parseFloat(value).toFixed(2)}`;
    }

    function updateTotalExpenses() {
        const inputs = document.querySelectorAll('.expense-input');
        const total = Array.from(inputs)
            .reduce((sum, input) => sum + (parseFloat(input.value) || 0), 0);
        
        const totalElement = document.getElementById('totalExpenses');
        if (totalElement) {
            const currencySymbol = totalElement.textContent.charAt(0) || '$';
            totalElement.textContent = `${currencySymbol}${total.toFixed(2)}`;
        }
    }

    function showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.getElementById('alertContainer');
        if (container) {
            container.innerHTML = '';
            container.appendChild(alertDiv);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }
    }

    // Handle form submission
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFormSubmit);
    }

    // Keep your existing fillFormWithData and other functions...
}); 