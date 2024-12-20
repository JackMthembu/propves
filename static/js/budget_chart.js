// Function to render the radar chart
function renderRadarChart(budgetData) {
  const ctx = document.getElementById('budgetRadarChart').getContext('2d');

  const labels = budgetData.map(item => item.budget_type); // Extract budget types
  const dataValues = budgetData.map(item => item.budget_amount); // Extract budget amounts

  // Clear any existing chart before rendering a new one
  if (window.radarChart) {
      window.radarChart.destroy();
  }

  // Create a new radar chart
  window.radarChart = new Chart(ctx, {
      type: 'radar',
      data: {
          labels: labels,
          datasets: [{
              label: 'Budget Amount',
              data: dataValues,
              backgroundColor: 'rgba(255, 99, 132, 0.2)',
              borderColor: 'rgba(255, 99, 132, 1)',
              borderWidth: 1
          }]
      },
      options: {
          scale: {
              ticks: {
                  beginAtZero: true
              }
          }
      }
  });
}

// Example function to fetch budget data and render the chart
async function fetchAndRenderBudgetData() {
  try {
      const response = await fetch('/api/budget/current-year'); // Adjust the endpoint as necessary
      if (!response.ok) {
          throw new Error('Network response was not ok');
      }
      const budgetData = await response.json();

      // Check if budgetData is an array and has data
      if (Array.isArray(budgetData) && budgetData.length > 0) {
          // Call the function to render the radar chart
          renderRadarChart(budgetData);
      } else {
          console.warn('No budget data available to display.');
          // Optionally, you can handle the case where there's no data
      }
  } catch (error) {
      console.error('Error fetching budget data:', error);
      // Optionally, display an error message to the user
  }
}

// Call the function to fetch data and render the chart when the page loads
document.addEventListener('DOMContentLoaded', fetchAndRenderBudgetData);
