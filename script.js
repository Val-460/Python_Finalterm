// Target a structural container in your HTML index to draw out components dynamically
const timelineContainer = document.getElementById('timeline-app');

async function renderInteractiveTimeline() {
    try {
        if(timelineContainer) {
            timelineContainer.innerHTML = `<p class="loading">Loading Timeline Data & Scraping Financial Frameworks...</p>`;
        }

        // Call the serverless Python script (保持 Vercel 形式)
        const response = await fetch('/api/Pycode');
        const data = await response.json();

        if (data.status !== "success") throw new Error("Data parsing failure.");

        // Clear container to load compiled elements
        timelineContainer.innerHTML = "";

        // Build HTML components dynamically
        data.timeline_data.forEach(event => {
            const eventElement = document.createElement('div');
            eventElement.className = 'timeline-card';

            // 1. Loop through nested hardware tech components sent by Python
            let hardwareHTML = '';
            for (const [hardwareName, techDetails] of Object.entries(event.hardware_and_tech_breakdown)) {

                // 將晶片陣列轉換成帶有 onclick 的藍字超連結標籤
                const sensorsLinks = techDetails.chips_sensors.map(sensor => {
                    return `<a href="javascript:void(0)" class="sensor-click-link" style="color: #3b82f6; text-decoration: underline; cursor: pointer; font-weight: bold;" onclick="showSensorDetails('${sensor}')">${sensor}</a>`;
                }).join(', ');

                hardwareHTML += `
                    <div class="hardware-spec">
                        <h4>✈️ Hull/Platform: ${hardwareName} (${techDetails.category})</h4>
                        <p><strong>Advanced Materials:</strong> ${techDetails.materials.join(', ')}</p>
                        <p><strong>Sub-systems & Components:</strong> ${techDetails.components.join(', ')}</p>
                        <p><strong>Chips, Radars & Sensors:</strong> <span class="highlight-tech">${sensorsLinks}</span></p>
                    </div>
                `;
            }

            // 2. 補回原本 Vercel 網頁上的圖表容器與 HTML 結構
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

                <div class="chart-section">
                    <h3>Sector-Specific Volatility Tracking</h3>
                    <p class="chart-desc">Defense (Drones/Weapons) and protective material suppliers show sharp 48-hour demand spikes.</p>
                    <div class="charts-container" style="display: flex; gap: 20px; margin-top: 15px;">
                        <div class="chart-wrapper" style="flex: 1; background: #111827; padding: 15px; border-radius: 8px;">
                            <canvas id="materials-chart-${event.exercise.replace(/\s+/g, '-')}" width="100" height="50"></canvas>
                        </div>
                        <div class="chart-wrapper" style="flex: 1; background: #111827; padding: 15px; border-radius: 8px;">
                            <canvas id="weapons-chart-${event.exercise.replace(/\s+/g, '-')}" width="100" height="50"></canvas>
                        </div>
                    </div>
                </div>

                <div class="tech-breakdown-section" style="margin-top: 20px;">
                    <h3>🛠️ Deployed Tech Hardware Breakdown</h3>
                    ${hardwareHTML}
                </div>
                <hr style="border: 0; border-top: 1px solid #374151; margin: 30px 0;"/>
            `;
            timelineContainer.appendChild(eventElement);

            // 3. 補回動態繪製圖表的 JavaScript 邏輯 (使用 Chart.js)
            // 這裡會自動幫你在畫面上畫出綠色與紅色的 14 天趨勢線圖
            setTimeout(() => {
                initTimelineCharts(event.exercise.replace(/\s+/g, '-'));
            }, 0);
        });

    } catch (error) {
        console.error("Error processing timeline pipeline:", error);
        if(timelineContainer) {
            timelineContainer.innerHTML = `<p class="error">Failed to dynamically render analytics. Check local server terminal configurations.</p>`;
        }
    }
}

// 💡 補回原本專案用來畫圖表的底層函式
function initTimelineCharts(chartId) {
    if (typeof Chart === 'undefined') return; // 如果網頁沒載入 Chart.js 就先跳出

    // 模擬 14 天的波動數據
    const labels = Array.from({length: 14}, (_, i) => `Day ${i+1}`);

    // 材料趨勢 (綠線)
    const matCtx = document.getElementById(`materials-chart-${chartId}`);
    if (matCtx) {
        new Chart(matCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Ballistic Materials (14-Day Trend)',
                    data: [31, 32, 31, 33, 32, 34, 33, 35, 34, 36, 35, 37, 36, 38],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: { responsive: true, plugins: { legend: { labels: { color: '#fff' } } } }
        });
    }

    // 武器趨勢 (紅線)
    const wepCtx = document.getElementById(`weapons-chart-${chartId}`);
    if (wepCtx) {
        new Chart(wepCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Defense Weapons (14-Day Trend)',
                    data: [58, 60, 63, 62, 61, 61, 62, 61, 60, 62, 64, 64, 63, 64],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: { responsive: true, plugins: { legend: { labels: { color: '#fff' } } } }
        });
    }
}

// ==========================================
// 💡 點擊藍字跳出詳細視窗互動邏輯 (保持不變)
// ==========================================
function showSensorDetails(sensorName) {
    let modal = document.getElementById('sensor-modal');
    let overlay = document.getElementById('modal-overlay');

    if (!modal) {
        overlay = document.createElement('div');
        overlay.id = 'modal-overlay';
        overlay.style = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:999; display:none;';
        overlay.onclick = closeModal;
        document.body.appendChild(overlay);

        modal = document.createElement('div');
        modal.id = 'sensor-modal';
        modal.style = 'position:fixed; top:50%; left:50%; transform:translate(-50%, -50%); background:#1f2937; color:#f3f4f6; padding:24px; border-radius:12px; z-index:1000; box-shadow:0 10px 25px rgba(0,0,0,0.5); width:90%; max-width:450px; border:1px solid #374151; display:none; font-family:sans-serif;';
        modal.innerHTML = `
            <h3 id="modal-title" style="margin-top:0; color:#60a5fa; font-size:1.4rem;"></h3>
            <p id="modal-desc" style="line-height:1.6; color:#d1d5db; margin:16px 0 24px 0;"></p>
            <button onclick="closeModal()" style="background:#ef4444; color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:bold; float:right;">關閉</button>
        `;
        document.body.appendChild(modal);
    }

    let description = "這是該載具配備的核心電子/感測系統。";
    if (sensorName.includes("Type 1493 AESA Radar")) {
        description = "Type 1493 為殲-16（J-16）所裝備的主動電子掃描陣列雷達（AESA）。擁有極佳的多目標追蹤與遠距離鎖定能力，能有效指導 PL-15 等遠程空對空飛彈進行視距外打擊。";
    } else if (sensorName.includes("IRST")) {
        description = "紅外線搜索追蹤系統（Infrared Search and Track）。這是一種被動感測器，允許戰機在「不開啟雷達（無線電靜默）」的情況下，透過捕捉敵機散發的熱源來進行悄悄追蹤，極具戰術隱蔽價值。";
    } else if (sensorName.includes("Type 1475 AESA Radar")) {
        description = "Type 1475 是專為殲-20（J-20）隱形戰機研發的高端雷達，具備低可偵測性技術（LPI），使其在搜索敵機時不易被對方的雷達告警接收器察覺。";
    } else if (sensorName.includes("EOTS")) {
        description = "光電分散式孔徑系統 / 光電瞄準系統。整合了紅外線前視與全週向光電偵測功能，提供飛行員 360 度無死角的戰場動態視野，並具備超強的隱形跟蹤與對地高精度打擊瞄準能力。";
    } else if (sensorName.includes("Type 346A")) {
        description = "被譽為「海之星」的 S 頻段主動相控陣雷達，安裝於 052D 型驅逐艦。其四面巨大的陣列天線能提供 360 度全方位、遠距離的空情監視，是全艦區域防空飛彈系統的靈魂大腦。";
    }

    document.getElementById('modal-title').innerText = sensorName;
    document.getElementById('modal-desc').innerText = description;
    modal.style.display = 'block';
    overlay.style.display = 'block';
}

function closeModal() {
    const modal = document.getElementById('sensor-modal');
    const overlay = document.getElementById('modal-overlay');
    if (modal) modal.style.display = 'none';
    if (overlay) overlay.style.display = 'none';
}

// Run layout on window startup
document.addEventListener('DOMContentLoaded', renderInteractiveTimeline);