document.addEventListener("DOMContentLoaded", () => {
    // 綁定 HTML 的主要結構容器
    const timelineContainer = document.getElementById('timeline-app');

    // 專屬於特定工業板塊的戰術色彩
    const themeColors = {
        "Semiconductors": "#58a6ff",                       // 藍色
        "Drones": "#d29922",                               // 琥珀色
        "Defense Weapons": "#f85149",                      // 紅色
        "Ballistic Materials (UHMWPE/Ceramic)": "#3fb950",  // 綠色
        "Sensors & Electronics": "#a371f7"                 // 紫色
    };

    // 主非同步渲染流程（完美對接 Vercel Serverless API）
    async function renderInteractiveTimeline() {
        try {
            if (timelineContainer) {
                timelineContainer.innerHTML = `<div class="loading">Fetching tactical assets and expanded market analytics...</div>`;
            }

            // 呼叫 Vercel Serverless 後端 API
            const response = await fetch('/api/Pycode');
            if (!response.ok) throw new Error("Vercel API response was not OK");
            const data = await response.json();

            if (data.status !== "success") throw new Error("Data parsing failure from Vercel function.");

            // 清空容器以利動態載入雲端編譯元件
            timelineContainer.innerHTML = "";

            // 用來存放圖表渲染設定的陣列
            let chartConfigs = [];

            // 開始巡迴並動態建立 HTML 組件
            data.timeline_data.forEach((event, index) => {
                const eventElement = document.createElement('div');
                eventElement.className = 'timeline-card';

                // 1. 建立硬體規格與感測器超連結標籤 (安全加密傳參，避免 Vercel JSON 解析出錯)
                let hardwareHTML = "";
                if (event.hardware_and_tech_breakdown) {
                    for (const [hardwareName, techDetails] of Object.entries(event.hardware_and_tech_breakdown)) {

                        // 🛠️ 標註形式優化：使用 encodeURIComponent 確保特殊字元在雲端傳輸時不會搞碎 HTML 結構
                        const sensorsLinks = techDetails.chips_sensors.map(sensor => {
                            const safeSensorName = encodeURIComponent(sensor);
                            return `<a href="javascript:void(0)" class="sensor-click-link" style="color: #3b82f6; text-decoration: underline; cursor: pointer; margin-right: 4px;" onclick="showSensorDetails('${safeSensorName}')">${sensor}</a>`;
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
                }

                // 2. 動態建立 Canvas 區塊（對應 Chart.js 趨勢圖表）
                let chartsHtml = "";
                if (event.market_analytics && event.market_analytics.graphs) {
                    chartsHtml += `<div class="chart-grid">`;
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
                }

                // 3. 建立金融關聯性說明區塊 (相容多種欄位)
                let financialSummary = event.market_analytics?.summary || "";
                let trackingAssetHtml = "";

                if (event.market_impact) {
                    financialSummary = event.market_impact.analysis || financialSummary;
                    if (event.market_impact.tracked_assets && event.market_impact.tracked_assets[0]) {
                        trackingAssetHtml = `<br/><small>System Status Check: TSMC (TPE:2330): <strong>${event.market_impact.tracked_assets[0].trend}</strong></small>`;
                    }
                }

                // 4. 組裝全功能卡片節點
                eventElement.innerHTML = `
                    <div class="timeline-header">
                        <h2>${event.exercise}</h2>
                        <span class="badge-date">${event.date}</span>
                    </div>
                    <p class="summary-text">${event.context}</p>

                    <div class="market-box">
                        <h3>📈 Financial Market Correlation & Volatility</h3>
                        <p>${financialSummary}</p>
                        ${trackingAssetHtml}
                        ${chartsHtml}
                    </div>

                    <div class="tech-breakdown-section">
                        <h3>🛠️ Deployed Tech Hardware Breakdown</h3>
                        ${hardwareHTML}
                    </div>
                    <hr/>
                `;

                // 將卡片塞入主要 App DOM 容器
                timelineContainer.appendChild(eventElement);
            });

            // 5. 🛠️ 雲端關鍵優化：放棄不穩定的 setTimeout，改用 requestAnimationFrame
            // 這能確保 Vercel 載入完成並在瀏覽器真正渲染畫面的瞬間，精準繪製 Chart.js
            requestAnimationFrame(() => {
                chartConfigs.forEach(config => {
                    renderLineChart(config.id, config.label, config.data, config.color);
                });
            });

        } catch (error) {
            console.error("Error processing Vercel timeline pipeline:", error);
            if (timelineContainer) {
                timelineContainer.innerHTML = `<div class="loading" style="color: #ff7b72;">Failed to dynamically render analytics. Please check Vercel Function Logs.</div>`;
            }
        }
    }

    // 啟動主渲染流程
    renderInteractiveTimeline();
});

// ==========================================
// 📊 Chart.js 線條圖表渲染函數
// ==========================================
function renderLineChart(canvasId, label, trendData, themeColor) {
    const canvasElement = document.getElementById(canvasId);
    if (!canvasElement) return; // 防呆

    const ctx = canvasElement.getContext('2d');
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
                backgroundColor: themeColor + '1A', // 10% 透明度
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

// ==========================================
// 💡 「點擊藍字跳出詳細視窗」核心互動邏輯
// ==========================================
function showSensorDetails(encodedSensorName) {
    // 🛠️ 解碼被安全加密的感測器名稱
    const sensorName = decodeURIComponent(encodedSensorName);

    let modal = document.getElementById('sensor-modal');
    let overlay = document.getElementById('modal-overlay');

    if (!modal) {
        // 建立彈窗黑色半透明遮罩
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

    // 依據點擊的感測器名稱，提供對應的深科技規格介紹
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

    // 將資料塞入彈窗並呈現
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