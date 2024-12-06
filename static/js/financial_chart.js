document.addEventListener("DOMContentLoaded", () => {
  let chart; // Store chart instance
  
  // Function to load chart data
  const loadChartData = (period = 'year') => {
    fetch(`/api/monthly-financials?period=${period}`)
      .then(response => response.json())
      .then(data => {
        if (chart) {
          // Update existing chart
          chart.updateOptions({
            xaxis: {
              categories: data.months
            },
            series: [{
              name: 'Income',
              data: data.monthly_income
            }, {
              name: 'Expenses',
              data: data.monthly_expenses
            }, {
              name: 'Earnings',
              data: data.monthly_cashflow
            }]
          });
        } else {
          // Create new chart
          chart = new ApexCharts(document.querySelector("#financialreportchart"), {
            series: [{
              name: 'Income',
              data: data.monthly_income
            }, {
              name: 'Expenses',
              data: data.monthly_expenses
            }, {
              name: 'Earnings',
              data: data.monthly_cashflow
            }],
            chart: {
              height: 350,
              type: 'area',
              toolbar: {
                show: false
              },
              zoom: {
                enabled: false
              }
            },
            markers: {
              size: 4
            },
            colors: ['#60D0AC', '#FF6B6B', '#14832e'],  // More distinct colors
            fill: {
              type: "gradient",
              gradient: {
                shadeIntensity: 1,
                opacityFrom: 0.4,
                opacityTo: 0.1,
                stops: [0, 90, 100]
              }
            },
            dataLabels: {
              enabled: false
            },
            stroke: {
              curve: 'smooth',
              width: 2
            },
            xaxis: {
              categories: data.months,
              labels: {
                format: 'MMM'
              }
            },
            yaxis: {
              labels: {
                formatter: function(value) {
                  return '$' + value.toLocaleString();
                }
              }
            },
            tooltip: {
              y: {
                formatter: function(value) {
                  return '$' + value.toLocaleString();
                }
              }
            },
            legend: {
              position: 'top',
              horizontalAlign: 'right'
            }
          });
          chart.render();
        }
      })
      .catch(error => {
        console.error('Error loading financial data:', error);
        document.querySelector("#financialreportchart").innerHTML = 
          '<div class="alert alert-danger">Failed to load financial data</div>';
      });
  };

  // Add click handlers for filter items
  document.querySelectorAll('.financial-filter .dropdown-item').forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const period = e.target.dataset.period;
      loadChartData(period);
      
      // Update the title span
      const titleSpan = e.target.closest('.card').querySelector('.card-title span');
      titleSpan.textContent = `/${e.target.textContent}`;
    });
  });

  // Initial load
  loadChartData('year');
});
