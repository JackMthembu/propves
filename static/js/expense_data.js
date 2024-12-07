function initializeExpenseData(totalExpenses, currencySymbol) {
    // Define expense labels mapping
    const expenseLabels = {
        'hoa_fees': 'Association Fees',
        'maintenance': 'Maintenance',
        'staff_cost': 'Staff Cost',
        'management_fee': 'Management Fees',
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
        'other_city_charges': 'Other City Charges'
    };

    // Transform data using the labels mapping
    const chartData = Object.entries(totalExpenses).map(([key, value]) => ({
        label: expenseLabels[key] || key,
        value: value
    })).filter(item => item.value > 0); // Only include non-zero values

    // Sort by value descending
    chartData.sort((a, b) => b.value - a.value);

    // Get the canvas element
    const ctx = document.getElementById('expensesDonutChart');
    
    if (ctx) {
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: chartData.map(item => item.label),
                datasets: [{
                    data: chartData.map(item => item.value),
                    backgroundColor: [
                        '#60D0AC', // Primary
                        '#4AB089', // 25% darker
                        '#359066', // 50% darker
                        '#207043', // 75% darker
                        '#8BDBC1', // 25% lighter
                        '#B5E6D6', // 50% lighter
                        '#DFF2EA', // 75% lighter
                        '#75D6B8'  // 10% darker
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed;
                                const percentage = ((value / chartData.reduce((sum, item) => sum + item.value, 0)) * 100).toFixed(1);
                                return `${context.label}: ${currencySymbol}${value.toFixed(2)} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
}

