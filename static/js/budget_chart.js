document.addEventListener("DOMContentLoaded", async () => {
    const baseColor = '#60D0AC';
    
    // Fetch budget data from the server
    const response = await fetch('/api/budget/current-year');
    const budgetData = await response.json();
    
    // Group data by budget_type
    const groupedData = {};
    budgetData.forEach(item => {
        if (!groupedData[item.budget_type]) {
            groupedData[item.budget_type] = {
                budget_amount: 0,
                actual_amount: 0
            };
        }
        groupedData[item.budget_type].budget_amount += Number(item.budget_amount);
        groupedData[item.budget_type].actual_amount += Number(item.actual_amount);
    });
    
    // Extract categories and values from the grouped data
    const categories = Object.keys(groupedData);
    const budgetValues = categories.map(type => groupedData[type].budget_amount);
    const actualValues = categories.map(type => groupedData[type].actual_amount);
    
    const colors = generateLighterColors(baseColor, categories.length);

    new ApexCharts(document.querySelector("#budgetChart"), {
        series: [{
            name: 'Budget',
            data: budgetValues,
        },
        {
            name: 'Actual',
            data: actualValues,
        }],
        chart: {
            height: 400,
            type: 'radar',
            toolbar: {
                show: true
            }
        },
        colors: colors,
        xaxis: {
            categories: categories.map(type => type.charAt(0).toUpperCase() + type.slice(1))
        },
        tooltip: {
            y: {
                formatter: function(value) {
                    return value.toLocaleString('en-US', {
                        style: 'currency',
                        currency: 'USD'  // You might want to make this dynamic based on user's currency
                    });
                }
            }
        }
    }).render();

    // Call the function to generate the budget table
    generateBudgetTable(groupedData);
});

// Function to generate a table from the budget data
function generateBudgetTable(data) {
    const tableContainer = document.querySelector("#budgetTable");
    let tableHTML = "<table><tr><th>Budget Type</th><th>Budget Amount</th><th>Actual Amount</th></tr>";
    
    for (const [type, amounts] of Object.entries(data)) {
        tableHTML += `<tr><td>${type}</td><td>${amounts.budget_amount.toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td><td>${amounts.actual_amount.toLocaleString('en-US', {style: 'currency', currency: 'USD'})}</td></tr>`;
    }
    
    tableHTML += "</table>";
    tableContainer.innerHTML = tableHTML;
}

function generateLighterColors(baseColor, count) {
    const colors = [];
    let lightness = 40; // Initial lightness value
  
    for (let i = 0; i < count; i++) {
      const color = `hsl(${getHue(baseColor)}, ${getSaturation(baseColor)}%, ${lightness}%)`;
      colors.push(color);
      lightness += 10; // Increase lightness for the next color
    }
  
    return colors;
  }
  
  function getHue(hexColor) {
    const rgb = hexToRgb(hexColor);
    const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);
    return Math.round(hsl.h);
  }
  
  function getSaturation(hexColor) {
    const rgb = hexToRgb(hexColor);
    const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);
    return Math.round(hsl.s * 100);
  }
  
  function hexToRgb(hex) {
    const shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
    hex = hex.replace(shorthandRegex, function(m, r, g, b) {
      return r + r + g + g + b + b;
    });
  
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  }
  
  function rgbToHsl(r, g, b) {
    r /= 255, g /= 255, b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;
  
    if (max == min) {
      h = s = 0; // achromatic
    } else {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = (g - b) / d + (g < b ? 6 : 0); break;
        case g: h = (b - r) / d + 2; break;
        case b: h = (r - g) / d + 4; break;
      }
      h /= 6;
    }
  
    return { h: h * 360, s: s, l: l };
  }