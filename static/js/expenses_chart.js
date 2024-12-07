document.addEventListener('DOMContentLoaded', function() {
    const chartDom = document.getElementById('expensesChart');
    if (!chartDom) {
        console.error('Expenses chart container not found');
        return;
    }

    // Verify ECharts is loaded
    if (typeof echarts === 'undefined') {
        console.error('ECharts library not loaded');
        return;
    }

    console.log('Initializing expenses chart...');
    const myChart = echarts.init(chartDom);
    
    // Fetch expenses data from the API
    fetch('/api/expenses-data')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Received expenses data:', data);
            if (!Array.isArray(data) || data.length === 0) {
                console.warn('No expenses data received');
            }

            const option = {
                tooltip: {
                    trigger: 'item',
                    formatter: '{a} <br/>{b}: ${c} ({d}%)'
                },
                legend: {
                    orient: 'vertical',
                    left: 'left'
                },
                series: [
                    {
                        name: 'Expenses',
                        type: 'pie',
                        radius: '70%',
                        data: data.map(item => ({
                            value: item.total,
                            name: item.sub_category
                        })),
                        emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowOffsetX: 0,
                                shadowColor: 'rgba(0, 0, 0, 0.5)'
                            }
                        }
                    }
                ]
            };

            console.log('Setting chart options...');
            myChart.setOption(option);
        })
        .catch(error => {
            console.error('Error loading expenses chart:', error);
            chartDom.innerHTML = 'Error loading expenses data';
        });

    // Handle window resize
    window.addEventListener('resize', function() {
        myChart.resize();
    });
});