document.addEventListener('DOMContentLoaded', function() {
    // PDF Export
    document.getElementById('exportPDF').addEventListener('click', function() {
        // Create the content container
        const content = document.createElement('div');
        content.id = 'printContent';
        
        // Add report header
        content.innerHTML = `
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #333;">Expense Report</h1>
                <p>${document.querySelector('.alert-info').textContent}</p>
            </div>
        `;
        
        // Add Properties Overview
        content.innerHTML += `
            <div style="margin-bottom: 30px;">
                <h2 style="color: #444;">Properties Overview</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #f8f9fa;">
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Property</th>
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Location</th>
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: right;">Total Expenses</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${Array.from(document.querySelectorAll('#properties tbody tr')).map(row => `
                            <tr>
                                <td style="padding: 12px; border: 1px solid #dee2e6;">${row.cells[0].textContent}</td>
                                <td style="padding: 12px; border: 1px solid #dee2e6;">${row.cells[1].textContent}</td>
                                <td style="padding: 12px; border: 1px solid #dee2e6; text-align: right;">${row.cells[2].textContent}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                    <tfoot>
                        <tr style="background-color: #f8f9fa; font-weight: bold;">
                            <td colspan="2" style="padding: 12px; border: 1px solid #dee2e6;">Total</td>
                            <td style="padding: 12px; border: 1px solid #dee2e6; text-align: right;">
                                ${document.querySelector('#properties tfoot tr td:last-child').textContent}
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        `;
        
        // Add Expense Categories
        content.innerHTML += `
            <div style="margin-bottom: 30px;">
                <h2 style="color: #444;">Expense Categories</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #f8f9fa;">
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">Category</th>
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: right;">Amount</th>
                            <th style="padding: 12px; border: 1px solid #dee2e6; text-align: right;">Percentage</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${Array.from(document.querySelectorAll('#categories tbody tr')).map(row => `
                            <tr>
                                <td style="padding: 12px; border: 1px solid #dee2e6;">${row.cells[0].textContent}</td>
                                <td style="padding: 12px; border: 1px solid #dee2e6; text-align: right;">${row.cells[1].textContent}</td>
                                <td style="padding: 12px; border: 1px solid #dee2e6; text-align: right;">${row.cells[2].textContent}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        // Add footer
        content.innerHTML += `
            <div style="margin-top: 30px; text-align: center; color: #666;">
                <p>Report generated on ${new Date().toLocaleString()}</p>
            </div>
        `;
        
        // Add to document
        document.body.appendChild(content);
        
        // Print
        window.print();
        
        // Cleanup
        document.body.removeChild(content);
    });

    // Excel Export
    document.getElementById('exportExcel').addEventListener('click', function() {
        // Get the data
        const data = [];
        
        // Add header
        data.push(['Expense Report']);
        data.push([document.querySelector('.alert-info').textContent]);
        data.push([]);
        
        // Add properties data
        data.push(['Properties Overview']);
        data.push(['Property', 'Location', 'Total Expenses']);
        document.querySelectorAll('#properties tbody tr').forEach(row => {
            data.push([
                row.cells[0].textContent,
                row.cells[1].textContent,
                row.cells[2].textContent
            ]);
        });
        data.push([]);
        
        // Add categories data
        data.push(['Expense Categories']);
        data.push(['Category', 'Amount', 'Percentage']);
        document.querySelectorAll('#categories tbody tr').forEach(row => {
            data.push([
                row.cells[0].textContent,
                row.cells[1].textContent,
                row.cells[2].textContent
            ]);
        });
        
        // Convert to CSV
        const csvContent = data.map(row => row.join(',')).join('\n');
        
        // Download file
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        const date = new Date().toISOString().split('T')[0];
        
        link.setAttribute('href', url);
        link.setAttribute('download', `expense_report_${date}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
}); 