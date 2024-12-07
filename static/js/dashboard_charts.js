document.addEventListener("DOMContentLoaded", async () => {
    // ... existing code ...

    // Fetch income sources data from the server
    const incomeResponse = await fetch('/api/income/sources');
    const incomeData = await incomeResponse.json();

    // Extract income categories and values
    const incomeCategories = incomeData.map(item => item.source);
    const incomeValues = incomeData.map(item => item.amount);

    // Create the Income Sources Breakdown donut chart
    new ApexCharts(document.querySelector("#incomeSourcesChart"), {
        series: incomeValues,
        chart: {
            type: 'donut',
            height: 400
        },
        labels: incomeCategories,
        colors: ['#FF4560', '#00E396', '#008FFB'], // Customize colors as needed
        tooltip: {
            y: {
                formatter: function(value) {
                    return value.toLocaleString('en-US', {
                        style: 'currency',
                        currency: 'USD'
                    });
                }
            }
        }
    }).render();
    
    // ... existing code ...
});