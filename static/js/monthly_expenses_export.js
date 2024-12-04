// Add this new file for handling exports
function exportToPDF(propertyTitle, expenses) {
    // Create a hidden div for PDF content
    const printContent = document.createElement('div');
    printContent.id = 'printContent';
    printContent.style.padding = '20px';

    // Add header
    const header = document.createElement('div');
    header.innerHTML = `
        <h2 style="color: #333; margin-bottom: 20px;">Monthly Expenses - ${propertyTitle}</h2>
        <p style="color: #666; margin-bottom: 30px;">
            Report generated on ${new Date().toLocaleDateString()}
        </p>
    `;
    printContent.appendChild(header);

    // Create expense details table
    const table = document.createElement('table');
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';
    table.style.marginBottom = '30px';

    // Add table headers
    const headers = ['Month', 'Bill Type', 'Association Fees', 'City Expenses', 'Total'];
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    headers.forEach(headerText => {
        const th = document.createElement('th');
        th.textContent = headerText;
        th.style.backgroundColor = '#f4f4f4';
        th.style.padding = '10px';
        th.style.border = '1px solid #ddd';
        th.style.textAlign = 'left';
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Add expense data
    const tbody = document.createElement('tbody');
    expenses.forEach(expense => {
        const row = document.createElement('tr');
        
        // Format the data
        const hoaFees = (
            parseFloat(expense.hoa_fees || 0) +
            parseFloat(expense.maintenance || 0) +
            parseFloat(expense.staff_cost || 0) +
            parseFloat(expense.management_fee || 0) +
            parseFloat(expense.reserve_fund || 0) +
            parseFloat(expense.special_assessments || 0) +
            parseFloat(expense.amenities || 0) +
            parseFloat(expense.other_expenses || 0) +
            parseFloat(expense.insurance || 0)
        ).toFixed(2);

        const cityExpenses = (
            parseFloat(expense.property_taxes || 0) +
            parseFloat(expense.electricity || 0) +
            parseFloat(expense.gas || 0) +
            parseFloat(expense.water_sewer || 0) +
            parseFloat(expense.miscellaneous_cost || 0) +
            parseFloat(expense.other_city_charges || 0)
        ).toFixed(2);

        const total = (parseFloat(hoaFees) + parseFloat(cityExpenses)).toFixed(2);

        // Add cells
        [
            new Date(expense.month).toLocaleDateString('default', { month: 'long', year: 'numeric' }),
            expense.bill_type,
            `${window.currencySymbol}${hoaFees}`,
            `${window.currencySymbol}${cityExpenses}`,
            `${window.currencySymbol}${total}`
        ].forEach(text => {
            const td = document.createElement('td');
            td.textContent = text;
            td.style.padding = '10px';
            td.style.border = '1px solid #ddd';
            row.appendChild(td);
        });

        tbody.appendChild(row);
    });
    table.appendChild(tbody);
    printContent.appendChild(table);

    // Add to document, print, and remove
    document.body.appendChild(printContent);
    window.print();
    document.body.removeChild(printContent);
}