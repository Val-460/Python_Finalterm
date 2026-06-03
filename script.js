document.addEventListener("DOMContentLoaded", () => {
    const appContainer = document.getElementById("timeline-app");

    // Display a loading indicator while fetching the serverless API
    appContainer.innerHTML = '<div class="loading">Fetching military assets and market analytics...</div>';

    fetch('/api/Pycode')
        .then(response => {
            if (!response.ok) throw new Error("Network response was not OK");
            return response.json();
        })
        .then(data => {
            // Clear the loading indicator
            appContainer.innerHTML = "";

            if (data.status === "success") {
                data.timeline_data.forEach((event, index) => {
                    // 1. Create a unique ID for the canvas graph elements
                    const tsmcCanvasId = `chart-tsmc-${index}`;
                    const taiexCanvasId = `chart-taiex-${index}`;

                    // 2. Build out the HTML structure for each card
                    let hardwareHtml = "";
                    for (const [name, specs] of Object.entries(event.hardware_and_tech_breakdown)) {
                        hardwareHtml += `
                            <div class="hardware-spec">
                                <h4>${name} (${specs.category})</h4>
                                <p><strong>Deep-Tech Components:</strong> ${specs.components.join(", ")}</p>
                                <p><strong>Avionics & Sensors:</strong> <span class="highlight-tech">${specs.chips_sensors.join(", ")}</span></p>
                                <p><strong>Advanced Materials:</strong> ${specs.materials.join(", ")}</p>
                            </div>
                        `;
                    }

                    const cardHtml = `
                        <div class="timeline-card">
                            <div class="timeline-header">
                                <h2>${event.exercise}</h2>
                                <span class="badge-date">${event.date}</span>
                            </div>
                            <p class="summary-text">${event.context}</p>
                            
                            <div class="tech-breakdown-section">
                                <h3>Frontline Hardware & Semiconductor Vector Breakdown</h3>
                                ${hardwareHtml}
                            </div>

                            <div class="market-box">
                                <h3>Market Volatility & Resilience Tracking</h3>
                                <p>${event.market_analytics.summary}</p>
                                
                                <div style="margin-top: 20px; background: #1f242c; padding: 15px; border-radius: 6px;">
                                    <canvas id="${tsmcCanvasId}"></canvas>
                                </div>
                                <div style="margin-top: 20px; background: #1f242c; padding: 15px; border-radius: 6px;">
                                    <canvas id="${taiexCanvasId}"></canvas>
                                </div>
                            </div>
                        </div>
                    `;

                    // Append the built card to our main app container
                    appContainer.innerHTML += cardHtml;

                    // 3. We must wait a millisecond for the browser to render the canvas tags into the DOM, 
                    // then initialize the Chart.js objects using the arrays from Python
                    setTimeout(() => {
                        renderLineChart(
                            tsmcCanvasId, 
                            "TSMC (TPE:2330) 14-Day Post-Exercise Trend", 
                            event.market_analytics.graphs.TSMC_14_Day_Trend, 
                            "#58a6ff"
                        );
                        renderLineChart(
                            taiexCanvasId, 
                            "TAIEX Index 14-Day Post-Exercise Trend", 
                            event.market_analytics.graphs.TAIEX_14_Day_Trend, 
                            "#3fb950"
                        );
                    }, 50);
                });
            } else {
                appContainer.innerHTML = '<div class="loading">Failed to load analytics payload.</div>';
            }
        })
        .catch(error => {
            console.error("Error loading application:", error);
            appContainer.innerHTML = '<div class="loading" style="color: #ff7b72;">Failed to dynamically render analytics. Check local server terminal configurations.</div>';
        });
});

// Helper function that configures Chart.js options
function renderLineChart(canvasId, label, trendData, themeColor) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Split the data array into independent labels (X-axis) and prices (Y-axis)
    const labels = trendData.map(item => item.day);
    const dataPoints = trendData.map(item => item.price);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: dataPoints,
                borderColor: themeColor,
                backgroundColor: themeColor + '1A', // Adds slight transparency for line fill area
                borderWidth: 2,
                tension: 0.3, // Adds smooth curve smoothing to graph lines
                pointRadius: 3,
                pointBackgroundColor: themeColor
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#c9d1d9' } }
            },
            scales: {
                x: { grid: { color: '#30363d' }, ticks: { color: '#8b949e' } },
                y: { grid: { color: '#30363d' }, ticks: { color: '#8b949e' } }
            }
        }
    });
}