// Target a structural container in your HTML index to draw out components dynamically
const timelineContainer = document.getElementById('timeline-app');

async function renderInteractiveTimeline() {
    try {
        if(timelineContainer) {
            timelineContainer.innerHTML = `<p class="loading">Loading Timeline Data & Scraping Financial Frameworks...</p>`;
        }

        // Call the serverless Python script (符合 Vercel 形式)
        const response = await fetch('/api/Pycode');
        const data = await response.json();

        if (data.status !== "success") throw new Error("Data parsing failure.");

        // Clear container to load compiled elements
        timelineContainer.innerHTML = "";

        // Build HTML components dynamically
        data.timeline_data.forEach(event => {
            const eventElement = document.createElement('div');
            eventElement.className = 'timeline-card';

            // 1. 還原你原本的 Frontline Hardware 結構，並加上藍字點擊
            let hardwareHTML = '';
            for (const [hardwareName, techDetails] of Object.entries(event.hardware_and_tech_breakdown)) {

                // 💡 精準微調：把原本的純文字轉換成可以點擊的超連結，帶入 Modal 功能
                const sensorsLinks = techDetails.chips_sensors.map(sensor => {
                    return `<a href="javascript:void(0)" class="sensor-click-link" style="color: #3b82f6; text-decoration: underline; cursor: pointer; font-weight: bold;" onclick="showSensorDetails('${sensor}')">${sensor}</a>`;
                }).join(', ');

                // 這裡完全採用你截圖中顯示的 class 與排版樣式
                hardwareHTML += `
                    <div class="hardware-spec">
                        <h4>${hardwareName} (${techDetails.category})</h4>
                        <p><strong>Deep-Tech Components:</strong> ${techDetails.components.join(', ')}</p>
                        <p><strong>Avionics & Sensors:</strong> <span class="highlight-tech">${sensorsLinks}</span></p>
                        <p><strong>Advanced Materials:</strong> ${techDetails.materials.join(', ')}</p>
                    </div>
                `;
            }

            // 2. 核心大還原：這段完全複製你原本擁有四張趨勢圖的完美 HTML 模板結構
            eventElement.innerHTML = `
                <div class="timeline-header">
                    <h2>${event.exercise}</h2>
                    <span class="badge-date">${event.date}</span>
                </div>
                <p class="summary-text">${event.context}</p>

                <h3 style="color: #ff7a00; margin-top: 25px; font-size: 1.15rem;">Frontline Hardware & Component Vector Breakdown</h3>
                <div class="tech-breakdown-section">
                    ${hardwareHTML}
                </div>

                <div class="market-box" style="margin-top: 25px;">
                    <h3 style="color: #10b981;">Sector-Specific Volatility Tracking</h3>
                    <p>${event.market_impact.analysis}</p>
                    <small style="display:block; margin-top:10px;">System Status Check: TSMC (TPE:2330): <strong>${event.market_impact.tracked_assets[0].trend}</strong></small>
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

// ==========================================
// 💡 以下是新增的「點擊藍字跳出詳細視窗」互動邏輯
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
        description = "Type 1475（即機載三座標主動相控陣雷達）是專為殲-20（J-20）隱形戰機研發的高端雷達，具備低可偵測性技術（LPI），使其在搜索敵機時不易被對方的雷達告警接收器察覺。";
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
