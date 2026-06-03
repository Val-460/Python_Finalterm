document.addEventListener("DOMContentLoaded", () => {
    const appContainer = document.getElementById("timeline-app");

    // 1. 新增：硬體逆向查詢字典（告訴系統這個藍字出現在哪台飛機/船艦上）
    const componentToHardwareMap = {
        "Type 1475 AESA Radar": ["J-20 Stealth Fighter"],
        "EOTS (Electro-Optical Targeting System)": ["J-20 Stealth Fighter"],
        "GaAs/GaN T/R Modules": ["J-20 Stealth Fighter"],
        "Type 1493 AESA Radar": ["J-16 Strike Fighter"],
        "IRST (Infrared Search and Track)": ["J-16 Strike Fighter"],
        "Type 346A S-band Active Phased Array Radar": ["Type 052D Destroyer"],
        "Towed Array Sonar": ["Type 052D Destroyer"],
        "High-power RF Jamming sub-systems": ["Type 052D Destroyer"],
        "Radiation-hardened guidance chips": ["Dongfeng-15/16/17 Ballistic Missiles"],
        "Laser Gyroscopes": ["Dongfeng-15/16/17 Ballistic Missiles"],
        "Beidou-3 Navigation transceivers": ["Dongfeng-15/16/17 Ballistic Missiles"],
        "Synthetic Aperture Radar (SAR)": ["TB-001 & BZK-005 Reconnaissance Drones"],
        "High-resolution electro-optical/infrared (EO/IR) turrets": ["TB-001 & BZK-005 Reconnaissance Drones"],
        "Type 360 Air/Surface Search Radar": ["PLA Coast Guard Cutters (Type 054A variants)"],
        "Electro-optical surveillance turrets": ["PLA Coast Guard Cutters (Type 054A variants)"]
    };

    appContainer.innerHTML = '<div class="loading">Fetching tactical assets and expanded market analytics...</div>';

    fetch('/api/Pycode')
        .then(response => {
            if (!response.ok) throw new Error("Network response was not OK");
            return response.json();
        })
        .then(data => {
            appContainer.innerHTML = "";

            if (data.status === "success") {
                const themeColors = {
                    "Semiconductors": "#58a6ff",
                    "Drones": "#d29922",
                    "Defense Weapons": "#f85149",
                    "Ballistic Materials (UHMWPE/Ceramic)": "#3fb950",
                    "Sensors & Electronics": "#a371f7"
                };

                data.timeline_data.forEach((event, index) => {
                    // 2. 修改：動態將藍字陣列轉化為「可點擊的超連結標籤」
                    let hardwareHtml = "";
                    for (const [name, specs] of Object.entries(event.hardware_and_tech_breakdown)) {

                        // 將原本的陣列，每個元素都包上帶有 data-tech 屬性的 span
                        const clickableSensorsHtml = specs.chips_sensors.map(sensor => {
                            return `<span class="tech-clickable" data-tech="${sensor.strip()}">${sensor}</span>`;
                        }).join(", ");

                        hardwareHtml += `
                            <div class="hardware-spec">
                                <h4>${name} (${specs.category})</h4>
                                <p><strong>Deep-Tech Components:</strong> ${specs.components.join(", ")}</p>
                                <p><strong>Avionics & Sensors:</strong> <span class="highlight-tech">${clickableSensorsHtml}</span></p>
                                <p><strong>Advanced Materials:</strong> ${specs.materials.join(", ")}</p>
                            </div>
                        `;
                    }

                    // 3. 圖表 Grid 建立 (保持原樣)
                    let chartsHtml = `<div class="chart-grid">`;
                    let chartConfigs = [];
                    let sectorIndex = 0;
                    for (const [sectorName, trendData] of Object.entries(event.market_analytics.graphs)) {
                        const canvasId = `chart-${index}-${sectorIndex}`;
                        chartsHtml += `<div class="chart-wrapper"><canvas id="${canvasId}"></canvas></div>`;
                        chartConfigs.push({
                            id: canvasId,
                            label: `${sectorName} (14-Day Trend)`,
                            data: trendData,
                            color: themeColors[sectorName] || "#8b949e"
                        });
                        sectorIndex++;
                    }
                    chartsHtml += `</div>`;

                    const cardWrapper = document.createElement("div");
                    cardWrapper.className = "timeline-card";
                    cardWrapper.innerHTML = `
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
                    `;

                    appContainer.appendChild(cardWrapper);

                    chartConfigs.forEach(config => {
                        renderLineChart(config.id, config.label, config.data, config.color);
                    });
                });

                // 4. 新增：監聽藍字點擊事件
                document.querySelectorAll(".tech-clickable").forEach(element => {
                    element.addEventListener("click", (e) => {
                        const techName = e.target.getAttribute("data-tech");
                        const deployedOn = componentToHardwareMap[techName] || ["Unknown Platform"];

                        // 呼叫彈窗顯示說明
                        showTechModal(techName, deployedOn);
                    });
                });

            } else {
                appContainer.innerHTML = '<div class="loading">Failed to load analytics payload.</div>';
            }
        });
});

// 5. 新增：精美自訂彈窗函式（代替難看的內建 alert）
function showTechModal(techName, platforms) {
    // 檢查有沒有舊的彈窗，有就先刪除
    const oldModal = document.getElementById("tech-custom-modal");
    if (oldModal) oldModal.remove();

    const modal = document.createElement("div");
    modal.id = "tech-custom-modal";
    modal.innerHTML = `
        <div class="modal-content">
            <h3>🔍 Component Cross-Reference</h3>
            <p class="modal-tech-name">${techName}</p>
            <div class="modal-divider"></div>
            <p class="modal-label">🔑 Deployed Tactical Platforms:</p>
            <ul>
                ${platforms.map(p => `<li>✈️ <strong>${p}</strong></li>`).join("")}
            </ul>
            <button onclick="document.getElementById('tech-custom-modal').remove()">Dismiss</button>
        </div>
    `;
    document.body.appendChild(modal);
}

// 輔助函式：移除前後空白
String.prototype.strip = function() {
    return this.replace(/^\s+|\s+$/g, "");
};

// renderLineChart 保持不變...