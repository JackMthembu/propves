document.addEventListener("DOMContentLoaded", () => {
    const ctx = document.querySelector('#expensesDonutChart');
    if (!ctx) {
        console.error('Chart canvas not found');
        return;
    }

    // Check if expense data exists
    if (!window.expenseData) {
        console.error('Expense data not found');
        return;
    }

    // Create the chart
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: window.expenseData.labels,
            datasets: [{
                data: window.expenseData.values,
                backgroundColor: [
                    '#60D0AC', // Primary
                    '#4AB089', // 25% darker
                    '#359066', // 50% darker
                    '#207043', // 75% darker
                    '#8BDBC1', // 25% lighter
                    '#B5E6D6', // 50% lighter
                    '#DFF2EA', // 75% lighter
                    '#75D6B8'  // 10% darker
                ],
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${context.label}: ${window.expenseData.currencySymbol}${value.toLocaleString()} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
});