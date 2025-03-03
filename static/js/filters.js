function applyFilter(filterType) {
    console.log('Filter selected:', filterType); // Debugging log

    // Update the filter label based on the selected filter
    const filterLabel = document.getElementById('filterLabel');
    switch (filterType) {
        case 'today':
            filterLabel.innerText = 'Today';
            break;
        case 'this_month':
            filterLabel.innerText = 'This Month';
            break;
        case 'past_month':
            filterLabel.innerText = 'Past Month';
            break;
        case 'past_year':
            filterLabel.innerText = 'Past Year';
            break;
        case 'current_year':
            filterLabel.innerText = 'Current Year';
            break;
        case 'custom':
            filterLabel.innerText = 'Custom Date Range';
            break;
        default:
            filterLabel.innerText = 'Current Period';
    }

    // Fetch dashboard data based on the selected filter
    fetch(`/api/dashboard-data?filter=${filterType}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Fetched data:', data); // Debugging log
            // Update the dashboard display with the fetched data
            document.getElementById('totalIncome').innerText = data.total_income; // Update income display
            document.getElementById('totalExpenses').innerText = data.total_expenses; // Update expenses display
            
            // Update budget summary
            const budgetSummaryElement = document.getElementById('budgetSummary');
            budgetSummaryElement.innerHTML = ''; // Clear previous budget summary
            for (const [budgetType, totalBudget] of Object.entries(data.budget_summary)) {
                const listItem = document.createElement('li');
                listItem.innerText = `${budgetType}: $${totalBudget.toFixed(2)}`;
                budgetSummaryElement.appendChild(listItem);
            }

            // Update occupancy level
            document.getElementById('occupiedCount').innerText = data.occupied; // Update occupied count
            document.getElementById('listedCount').innerText = data.listed; // Update listed count
            document.getElementById('occupancyRatio').innerText = (data.occupancy_ratio * 100).toFixed(2) + '%'; // Update occupancy ratio
        })
        .catch(error => console.error('Error fetching dashboard data:', error));
}