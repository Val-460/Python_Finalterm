document.addEventListener("DOMContentLoaded", () => {
    const appContainer = document.getElementById("timeline-app");

    appContainer.innerHTML = '<div class="loading">Fetching tactical assets and expanded market analytics...</div>';

    fetch('/api/Pycode')
        .then(response => {
            if (!response.ok) throw new Error("Network response was not OK");
            return response.json();
        })
        .then(data => {
            appContainer.innerHTML = "";

            if (data.status === "success") {
                // Tactical color palette for specific industrial sectors
                const themeColors = {
                    "Semiconductors": "#58a6ff",                  // Blue
                    "Drones": "#d29922",                          // Amber
                    "Defense Weapons": "#f85149",                 // Red
                    "Ballistic Materials (UHMWPE/Ceramic)": "#3fb950", // Green
                    "Sensors & Electronics": "#a371f7"            // Purple
                };

                data.timeline_data.forEach((event, index) => {
                    // 1. Build hardware specifications HTML
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

                    // 2. Dynamically build canvas grids for all available sectors
                    let chartsHtml = `<div class="chart-grid">`;
                    let chartConfigs = [];

                    let sectorIndex = 0;
                    for (const [sectorName, trendData] of Object.entries(event.market_analytics.graphs)) {
                        const canvasId = `chart-${index}-${sectorIndex}`;
                        chartsHtml += `
                            <div class="chart-wrapper">
                                <canvas id="${canvasId}"></canvas>
                            </div>
                        `;

                        chartConfigs.push({
                            id: canvasId,
                            label: `${sectorName} (14-Day Trend)`,
                            data: trendData,
                            color: themeColors[sectorName] || "#8b949e"
                        });
                        sectorIndex++;
                    }
                    chartsHtml += `</div>`;

                    // 3. Assemble the full timeline card
                    const cardHtml = `
                        <div class="timeline-card">
                            <div class="timeline-header">
                                <h2>${event.exercise}</h2>
                                <span class="badge-date">${event.date}</span>
                            </div>
                            <p class="summary-text">${event.context}</p>

                            <div class="tech-breakdown-section">
                                <h3>Frontline Hardware & Component Vector Breakdown</h3>
                                ${hardwareHtml}
                            </div>

                            <div class="market-box">
                                <h3>Sector-Specific Volatility Tracking</h3>
                                <p>${event.market_analytics.summary}</p>
                                ${chartsHtml}
                            </div>
                        </div>
                    `;

                    appContainer.innerHTML += cardHtml;

                    // 4. Render Chart.js instances after DOM updates
                    setTimeout(() => {
                        chartConfigs.forEach(config => {
                            renderLineChart(config.id, config.label, config.data, config.color);
                        });
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

function renderLineChart(canvasId, label, trendData, themeColor) {
    const ctx = document.getElementById(canvasId).getContext('2d');

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
                backgroundColor: themeColor + '1A', // Slight transparency for the fill
                borderWidth: 2,
                tension: 0.3,
                pointRadius: 3,
                pointBackgroundColor: themeColor
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#c9d1d9', font: { size: 11 } } }
            },
            scales: {
                x: { grid: { color: '#30363d' }, ticks: { color: '#8b949e', font: { size: 10 } } },
                y: { grid: { color: '#30363d' }, ticks: { color: '#8b949e', font: { size: 10 } } }
            }
        }
    });
}