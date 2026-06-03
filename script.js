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
                const themeColors = {
                    "Semiconductors": "#58a6ff",
                    "Drones": "#d29922",
                    "Defense Weapons": "#f85149",
                    "Ballistic Materials (UHMWPE/Ceramic)": "#3fb950",
                    "Sensors & Electronics": "#a371f7"
                };

                let chartConfigs = [];
                let fullHtml = "";

                data.timeline_data.forEach((event, index) => {
                    // 1. 建立硬體規格 HTML
                    let hardwareHtml = "";
                    for (const [name, specs] of Object.entries(event.hardware_and_tech_breakdown)) {

                        // 【關鍵修改】將感測器陣列字串，轉換成帶有 onclick 事件的藍字 HTML 標籤
                        const sensorsHtml = specs.chips_sensors.map(item => {
                            const trimmedItem = item.trim();
                            // 這裡加上了 cursor:pointer 讓它滑過去變手指，並綁定你給的 showSensorDetails 函式
                            return `<span class="highlight-tech" style="cursor: pointer; text-decoration: underline;" onclick="showSensorDetails('${trimmedItem.replace(/'/g, "\\'")}')">${trimmedItem}</span>`;
                        }).join(", ");

                        hardwareHtml += `
                            <div class="hardware-spec">
                                <h4>${name} (${specs.category})</h4>
                                <p><strong>Deep-Tech Components:</strong> ${specs.components.join(", ")}</p>
                                <p><strong>Avionics & Sensors:</strong> ${sensorsHtml}</p>
                                <p><strong>Advanced Materials:</strong> ${specs.materials.join(", ")}</p>
                            </div>
                        `;
                    }

                    // 2. 建立 Canvas 網格
                    let chartsHtml = `<div class="chart-grid">`;
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

                    // 3. 累積卡片 HTML 字串
                    fullHtml += `
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
                });

                // 一次性寫入 DOM
                appContainer.innerHTML = fullHtml;

                // 渲染 Chart.js
                requestAnimationFrame(() => {
                    chartConfigs.forEach(config => {
                        renderLineChart(config.id, config.label, config.data, config.color);
                    });
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

// 全局變數儲存圖表實例
const activeCharts = {};

function renderLineChart(canvasId, label, trendData, themeColor) {
    const canvasElement = document.getElementById(canvasId);
    if (!canvasElement) return;

    const ctx = canvasElement.getContext('2d');

    if (activeCharts[canvasId]) {
        activeCharts[canvasId].destroy();
    }

    const labels = trendData.map(item => item.day);
    const dataPoints = trendData.map(item => item.price);

    activeCharts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: dataPoints,
                borderColor: themeColor,
                backgroundColor: themeColor + '1A',
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


// ========================================================
// 💡 以下為您提供的「點擊藍字跳出詳細視窗」互動邏輯 (保持全域作用域)
// ========================================================

function showSensorDetails(sensorName) {
    // 1. 檢查網頁上有沒有現成的彈窗元件，沒有的話就動態建立一個
    let modal = document.getElementById('sensor-modal');
    let overlay = document.getElementById('modal-overlay');

    if (!modal) {
        // 建立彈窗黑底遮罩
        overlay = document.createElement('div');
        overlay.id = 'modal-overlay';
        overlay.style = 'position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:999; display:none;';
        overlay.onclick = closeModal;
        document.body.appendChild(overlay);

        // 建立彈窗主體
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

    // 2. 依據點擊的感測器名稱，給予相對應的規格介紹說明
    let description = "這是該載具配備的核心電子/感測系統。";

    if (sensorName.includes("Type 1493 AESA Radar")) {
        description = "Type 1493 為殲-16（J-16）所裝備的主動電子掃描陣列雷達（AESA）。擁有極佳的多目標追蹤與遠距離鎖定能力，能有效指導 PL-15 等遠程空對空飛彈進行視距外打擊。";
    } else if (sensorName.includes("IRST")) {
        description = "紅外線搜索追蹤系統（Infrared Search and Track）。這是一種被動感測器，允許戰機在「不開啟雷達（無線電靜默）」的情況下，透過捕捉敵機散發的熱源來進行悄悄追蹤，極具戰術隱蔽價值。";
    } else if (sensorName.includes("Type 1475 AESA Radar")) {
        description = "Type 1475（即機載三座標主動相控陣雷達）是專為殲-20（J-20）隱形戰機研發的高端雷達，具備低可偵測性技術（LPI），使其在搜索敵機時不易被對方的雷達告警接收器察覺。";
    } else if (sensorName.includes("EOTS")) {
        description = "光電分散式孔徑系統 / 光電瞄準系統。整合了紅外線前視與全週向光電偵測功能，提供飛行員 360 度無死角的戰場動態視野，並具備超強的隱形跟蹤與對地高精度打擊瞄準能力。";
    } else if (sensorName.includes("Type 346A")) {
        description = "被譽為「海之星」的 S 頻段主動相控陣雷達，安裝於 052D 型驅逐艦。其四面巨大的陣列天線能提供 360 度全方位、遠距離的空情監視，是全艦區域防空飛彈系統（如海紅旗-9）的靈魂大腦。";
    }

    // 3. 將資料帶入並顯示彈窗
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