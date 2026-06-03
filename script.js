// Targgit rebase --continueet a structural container in your HTML index to draw out components dynamically
const timelineContainer = document.getElementById('timeline-app');

async function renderInteractiveTimeline() {
    try {
        if(timelineContainer) {
            timelineContainer.innerHTML = `<p class="loading">Loading Timeline Data & Scraping Financial Frameworks...</p>`;
        }

        // Call the serverless Python script
        const response = await fetch('/api/Pycode');
        const data = await response.json();

        if (data.status !== "success") throw new Error("Data parsing failure.");

        // Clear container to load compiled elements
        timelineContainer.innerHTML = "";

        // Build HTML components dynamically
        data.timeline_data.forEach(event => {
            const eventElement = document.createElement('div');
            eventElement.className = 'timeline-card';

            // 1. Title and Context Header
            let hardwareHTML = '';
            
            // Loop through nested hardware tech components sent by Python
            for (const [hardwareName, techDetails] of Object.entries(event.hardware_and_tech_breakdown)) {
                hardwareHTML += `
                    <div class="hardware-spec">
                        <h4>✈️ Hull/Platform: ${hardwareName} (${techDetails.category})</h4>
                        <p><strong>Advanced Materials:</strong> ${techDetails.materials.join(', ')}</p>
                        <p><strong>Sub-systems & Components:</strong> ${techDetails.components.join(', ')}</p>
                        <p><strong>Chips, Radars & Sensors:</strong> <span class="highlight-tech">${techDetails.chips_sensors.join(', ')}</span></p>
                    </div>
                `;
            }

            eventElement.innerHTML = `
                <div class="timeline-header">
                    <span class="badge-date">${event.date}</span>
                    <h2>${event.exercise}</h2>
                </div>
                <p class="summary-text">${event.context}</p>
                
                <div class="market-box">
                    <h3>📈 Financial Market Corelation</h3>
                    <p>${event.market_impact.analysis}</p>
                    <small>System Status Check: TSMC (TPE:2330): <strong>${event.market_impact.tracked_assets[0].trend}</strong></small>
                </div>

                <div class="tech-breakdown-section">
                    <h3>🛠️ Deployed Tech Hardware Breakdown</h3>
                    ${hardwareHTML}
                </div>
                <hr/>
            `;
            timelineContainer.appendChild(eventElement);
        });

    } catch (error) {
        console.error("Error processing timeline pipeline:", error);
        if(timelineContainer) {
            timelineContainer.innerHTML = `<p class="error">Failed to dynamically render analytics. Check local server terminal configurations.</p>`;
        }
    }
}

// Run layout on window startup
document.addEventListener('DOMContentLoaded', renderInteractiveTimeline);