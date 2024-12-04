document.addEventListener('DOMContentLoaded', function() {
    let chart = null; // Keep track of chart instance

    // Add fetch logic here
    console.log('Starting to fetch expense data');
    fetch('/api/expenses-data')
        .then(response => {
            console.log('Received response:', response.status);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Received expense data:', data);
            window.expenseData = data;
            initChart();
        })
        .catch(error => {
            console.error('Error loading expenses data:', error);
        });

    const initChart = () => {
        const chartElement = document.querySelector("#expensesChart");
        if (!chartElement) {
            console.error('Chart element not found');
            return;
        }

        if (!window.expenseData || !window.expenseData.series || !window.expenseData.series.length) {
            console.error('No expense data available:', window.expenseData);
            return;
        }

        // Destroy existing chart if it exists
        if (chart) {
            chart.destroy();
        }

        console.log('Initializing chart with data:', window.expenseData);  // Debug line

        const baseColor = '#60D0AC';
        const backgroundColors = [
            baseColor,  // base color
            '#54bb9b',  // 10% darker
            '#48a689',  // 20% darker
            '#3c9178',  // 30% darker
            '#307c66',  // 40% darker
        ];

        // Transform the nested expense data structure
        const expenseCategories = [
            'Operating Expenses',
            'Common Area Expenses',
            'Occupancy Expenses',
            'Financial Expenses'
        ];

        // Ensure we're only using expense data from the correct categories
        const series = expenseCategories.map(category => 
            window.expenseData.series[window.expenseData.labels.indexOf(category)] || 0
        );

        const options = {
            series: series,
            chart: {
                type: 'donut',
                height: 380,
                events: {
                    dataPointSelection: function(event, chartContext, config) {
                        // Handle drill-down if implemented
                        const category = expenseCategories[config.dataPointIndex];
                        console.log('Selected category:', category);
                        // You could implement drill-down to show subcategories here
                    }
                }
            },
            labels: expenseCategories,
            colors: backgroundColors,
            dataLabels: {
                enabled: true,
                formatter: function(val, opts) {
                    const value = window.expenseData.series[opts.seriesIndex];
                    const percent = ((value / opts.w.globals.seriesTotals.reduce((a, b) => a + b, 0)) * 100).toFixed(1);
                    return `${opts.w.config.labels[opts.seriesIndex]}\n${percent}%\n${window.expenseData.currencySymbol}${value.toLocaleString()}`;
                }
            },
            tooltip: {
                y: {
                    formatter: function(value) {
                        return window.expenseData.currencySymbol + value.toLocaleString();
                    }
                }
            },
            legend: {
                position: 'right',
                horizontalAlign: 'center',
                formatter: function(seriesName, opts) {
                    const value = opts.w.globals.series[opts.seriesIndex];
                    const total = opts.w.globals.series.reduce((a, b) => a + b, 0);
                    const percent = ((value / total) * 100).toFixed(1);
                    return `${seriesName} (${percent}%)`;
                }
            },
            plotOptions: {
                pie: {
                    donut: {
                        size: '70%',
                        labels: {
                            show: true,
                            total: {
                                show: true,
                                label: 'Total Expenses',
                                formatter: function(w) {
                                    const total = w.globals.seriesTotals.reduce((a, b) => a + b, 0);
                                    return window.expenseData.currencySymbol + total.toLocaleString();
                                }
                            }
                        }
                    }
                }
            }
        };

        try {
            console.log('Creating chart with options:', options);  // Debug line
            chart = new ApexCharts(chartElement, options);
            chart.render();
            console.log('Expenses chart rendered successfully');
        } catch (error) {
            console.error('Error rendering expenses chart:', error);
        }
    };
});