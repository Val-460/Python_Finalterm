import { useState, useEffect } from 'react'
import Head from 'next/head'

const BRANCHES = [
  { name: "新北中和店", address: "新北市中和區景平路 159 號", phone: "02-2242-2321", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_zhonghe" },
  { name: "新北樹林店", address: "新北市樹林區中正路 410 號", phone: "02-2688-5522", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_shulin" },
  { name: "台北大同店", address: "台北市大同區延平北路三段 100 號", phone: "02-2599-1122", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_datong" },
  { name: "新北板橋店", address: "新北市板橋區文化路二段 320 號", phone: "02-2250-9988", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_banqiao" },
  { name: "新北三重店", address: "新北市三重區重新路四段 80 號", phone: "02-2970-7766", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_sanchong" },
  { name: "桃園中壢店", address: "桃園市中壢區延平路 200 號", phone: "03-425-3344", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_zhongli" },
  { name: "新竹中華店", address: "新竹市東區中華路二段 500 號", phone: "03-522-8877", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_hsinchu" },
  { name: "台中崇德店", address: "台中市北屯區崇德路二段 300 號", phone: "04-2244-5566", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_chongde" },
  { name: "台中一中店", address: "台中市北區三民路三段 250 號", phone: "04-2225-8899", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_yizhong" },
  { name: "彰化金馬店", address: "彰化市金馬路二段 600 號", phone: "04-722-3344", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_changhua" },
  { name: "台南公園店", address: "台南市北區公園路 800 號", phone: "06-251-2233", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_tainan" },
  { name: "高雄三民店", address: "高雄市三民區九如一路 400 號", phone: "07-380-5566", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_kaohsiung" },
  { name: "高雄鳳山店", address: "高雄市鳳山區光遠路 100 號", phone: "07-740-8899", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_fengshan" },
  { name: "宜蘭羅東店", address: "宜蘭縣羅東鎮純精路二段 150 號", phone: "03-955-6677", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_luodong" },
  { name: "花蓮中山店", address: "花蓮縣花蓮市中山路 700 號", phone: "03-833-2211", hours: "10:00 - 21:00", line: "https://line.me/ti/p/2motor_hualien" }
];

function cleanLocName(name) {
  if (!name) return "";
  let clean = name;
  const cities = ["新北", "台北", "桃園", "新竹", "台中", "彰化", "台南", "高雄", "宜蘭", "花蓮"];
  cities.forEach(city => {
    clean = clean.replace(city, "");
  });
  return clean.replace("店", "").strip ? clean.replace("店", "").trim() : clean.replace("店", "").trim();
}

export default function Home() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [products, setProducts] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [charts, setCharts] = useState(null);
  const [crawling, setCrawling] = useState(false);
  const [crawlStatus, setCrawlStatus] = useState(null);
  const [error, setError] = useState('');
  
  // Filter States
  const [brandFilter, setBrandFilter] = useState('全部');
  const [locationFilter, setLocationFilter] = useState('全部');
  const [kwFilter, setKwFilter] = useState('');
  const [priceMaxFilter, setPriceMaxFilter] = useState('');
  const [mileMaxFilter, setMileMaxFilter] = useState('');
  
  // Selection & Compare
  const [selectedBikes, setSelectedBikes] = useState([]);
  const [showCompareModal, setShowCompareModal] = useState(false);

  // Store tab branch
  const [selectedBranch, setSelectedBranch] = useState(BRANCHES[0]);

  // Sorting
  const [sortField, setSortField] = useState('id');
  const [sortAsc, setSortAsc] = useState(true);

  // Fetch API URL Helper (detect client/server)
  const apiBase = ''; // Vercel handles requests to /api/ on the same host

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setError('');
    try {
      const pResp = await fetch('/api/v1/products');
      if (!pResp.ok) throw new Error("尚未爬取商品資料，請點擊上方按鈕執行大數據爬蟲");
      const pData = await pResp.json();
      setProducts(pData);

      const aResp = await fetch('/api/v1/analysis');
      if (aResp.ok) {
        const aData = await aResp.json();
        setAnalysis(aData);
      }

      const cResp = await fetch('/api/v1/analysis/charts', { method: 'POST' });
      if (cResp.ok) {
        const cData = await cResp.json();
        setCharts(cData);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const startCrawl = async () => {
    setCrawling(true);
    setError('');
    try {
      const resp = await fetch('/api/v1/crawl', { method: 'POST' });
      const data = await resp.json();
      if (resp.ok && data.status === 'success') {
        loadData();
      } else {
        throw new Error(data.message || '爬蟲失敗');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setCrawling(false);
    }
  };

  // Poll status during crawl
  useEffect(() => {
    let timer;
    if (crawling) {
      timer = setInterval(async () => {
        try {
          const resp = await fetch('/api/v1/crawl/status');
          if (resp.ok) {
            const data = await resp.json();
            setCrawlStatus(data);
            if (!data.is_running) {
              setCrawling(false);
              loadData();
            }
          }
        } catch (e) {
          // ignore
        }
      }, 1000);
    } else {
      setCrawlStatus(null);
    }
    return () => clearInterval(timer);
  }, [crawling]);

  // Brands extracted dynamically
  const brands = products.length > 0
    ? ['全部', ...Array.from(new Set(products.map(p => p.brand).filter(Boolean)))]
    : ['全部'];

  // Handle Row Selection for Comparison
  const handleSelectBike = (bike) => {
    if (selectedBikes.find(b => b.id === bike.id)) {
      setSelectedBikes(selectedBikes.filter(b => b.id !== bike.id));
    } else {
      if (selectedBikes.length >= 3) {
        alert("最多只能選取 3 台車進行橫向對比！");
        return;
      }
      setSelectedBikes([...selectedBikes, bike]);
    }
  };

  // Filters & Sorting logic
  const filteredProducts = products.filter(p => {
    if (brandFilter !== '全部' && p.brand !== brandFilter) return false;
    if (locationFilter !== '全部') {
      const bShort = cleanLocName(locationFilter);
      const pLoc = cleanLocName(p.location || '');
      if (!pLoc.includes(bShort)) return false;
    }
    if (kwFilter && !p.title.toLowerCase().includes(kwFilter.toLowerCase())) return false;
    if (priceMaxFilter && p.current_price > Number(priceMaxFilter) * 10000) return false;
    if (mileMaxFilter && p.mileage > Number(mileMaxFilter)) return false;
    return true;
  });

  const sortedProducts = [...filteredProducts].sort((a, b) => {
    let valA = a[sortField];
    let valB = b[sortField];
    if (valA === undefined) return 1;
    if (valB === undefined) return -1;
    
    if (typeof valA === 'string') {
      return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    return sortAsc ? valA - valB : valB - valA;
  });

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(true);
    }
  };

  // Best specs for highlighting in comparison
  const getBestSpecs = () => {
    if (selectedBikes.length === 0) return {};
    const prices = selectedBikes.map(b => b.current_price);
    const mileages = selectedBikes.map(b => b.mileage);
    const years = selectedBikes.map(b => b.year);

    return {
      minPrice: Math.min(...prices),
      minMileage: Math.min(...mileages),
      maxYear: Math.max(...years)
    };
  };

  const bestSpecs = getBestSpecs();

  // Export Planner
  const exportAppointmentGuide = (bike) => {
    if (!bike) return;
    const now = new Date();
    const nowStr = `${now.getFullYear()}${(now.getMonth()+1).toString().padStart(2, '0')}${now.getDate().toString().padStart(2, '0')}_${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}`;
    
    const branchName = bike.location || "未指定分店";
    const branchInfo = BRANCHES.find(b => cleanLocName(b.name) === cleanLocName(branchName)) || BRANCHES[0];

    const mdContent = `# 貳輪嶼二手機車預約看車規劃書 (${bike.title})

## 1. 預約車輛詳細資訊

*   **車輛名稱**：${bike.title}
*   **參考網址**：${bike.url}
*   **出廠年份**：${bike.year} 年
*   **引擎排氣量**：${bike.displacement} cc
*   **行駛里程數**：${bike.mileage.toLocaleString()} 公里
*   **原電商售價**：NT$ ${bike.original_price.toLocaleString()} 元
*   **智能特價**：NT$ ${bike.current_price.toLocaleString()} 元 (省下 NT$ ${(bike.original_price - bike.current_price).toLocaleString()} 元)
*   **CP 值指數**：${bike.cp_index} (${bike.cp_label})

---

## 2. 實體看車門市資訊 (O2O 導航指引)

*   **看車門市**：${branchInfo.name}
*   **門市地址**：${branchInfo.address}
*   **門市電話**：${branchInfo.phone}
*   **營業時間**：${branchInfo.hours}
*   **LINE 聯絡**：${branchInfo.line}

---

## 3. 二手機車現場驗車 10 大防呆檢查表

為了確保您現場看車不踩雷，請嚴格核對以下 10 大項目：

| 檢查項目 | 檢查要點與步驟 | 現場核對結果 (Pass/Fail) |
| :--- | :--- | :---: |
| **1. 冷車啟動檢查** | 務必請店家在您到達前**不要熱車**。觸摸排氣管確認為冷態。按下發動鈕，觀察能否在 2-3 秒內一觸即發，且無異音。 | [ ] 正常 / [ ] 異常 |
| **2. 引擎漏油痕跡** | 趴下檢查引擎底部、墊片處、避震器油封處，確認無新鮮油污滲漏，地表無油滴。 | [ ] 正常 / [ ] 異常 |
| **3. 前後輪胎磨損** | 檢查輪胎胎紋深度。若低於 1.6mm (或磨損至指示點) 現場要求更換。確認輪胎製造日期是否過舊。 | [ ] 正常 / [ ] 異常 |
| **4. 避震與回彈測試** | 用力下壓前叉與後避震，感受阻尼是否過軟。確認避震器內管乾淨無油漬，沒有因老化漏油。 | [ ] 正常 / [ ] 異常 |
| **5. 龍頭與車架轉向** | 跨騎上車，原地左打右打龍頭。確認手感順暢無卡滯感。煞車拉桿是否鬆動、歪斜。 | [ ] 正常 / [ ] 異常 |
| **6. 煞車制動檢查** | 檢查前後煞車碟盤磨損深度、煞車皮厚度是否偏薄。煞車總泵油量是否充足。 | [ ] 正常 / [ ] 異常 |
| **7. 排氣檢驗與煙色** | 發動後用手背在排氣口後方感受氣流，有無藍煙(吃機油)或濃黑煙(燃燒不完全)，正常應為無色無味或白煙。 | [ ] 正常 / [ ] 異常 |
| **8. 車架有無溶接痕** | 拆開馬桶(車廂)或骨架處，確認無扭曲變形、防鏽漆剝落或二次焊接痕跡(防範重大事故車)。 | [ ] 正常 / [ ] 異常 |
| **9. 行照產權與車號** | 核對行照的**車身號碼/引擎號碼**與車輛實體鋼印是否完全一致。確認年份與里程是否跟網路上有大幅落差。 | [ ] 正常 / [ ] 異常 |
| **10. 保固責任與條款** | 詢問實體保固期(如引擎、保固範圍)，並確認合約中是否有非事故車、非泡水車與里程保證。 | [ ] 正常 / [ ] 異常 |

> **⚠️ 注意事項：**
> 二手機車買賣合約請務必使用中華民國「二手車買賣定型化契約」，凡是口頭承諾的保固與送配件，請全數要求白紙黑字寫入合約備註欄內，以保障自身權益。
`;

    const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `預約看車規劃書_${bike.title.replace(/\s+/g, '_')}_${nowStr}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-[#121214] text-[#eeeeee] font-sans antialiased">
      <Head>
        <title>🏍️ 二手機車 CP 值智能選購與全台尋車導航系統</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet" />
      </Head>

      {/* Top Banner Header */}
      <header className="border-b border-[#30363d] bg-[#1e1e24] py-4 px-6 sticky top-0 z-40 shadow-lg backdrop-blur-md bg-opacity-80">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🏍️</span>
            <div>
              <h1 className="text-xl md:text-2xl font-bold bg-gradient-to-r from-[#00adb5] to-[#58a6ff] bg-clip-text text-transparent">
                二手機車 CP 值智能選購與全台尋車導航系統
              </h1>
              <p className="text-xs text-[#b2bec3]">貳輪嶼官方數據大數據即時定位分析與 O2O 導航面板</p>
            </div>
          </div>
          
          <div className="flex gap-3 items-center">
            {crawling ? (
              <div className="flex items-center gap-2 text-sm text-[#e67e22]">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-[#e67e22] border-t-transparent"></div>
                <span>{crawlStatus ? `${crawlStatus.status} (${crawlStatus.scraped_count} 筆)` : '執行爬網中...'}</span>
              </div>
            ) : (
              <button 
                onClick={startCrawl}
                className="bg-[#27ae60] hover:bg-[#2ecc71] text-white px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-md"
              >
                🚀 執行大數據爬蟲
              </button>
            )}

            <button 
              onClick={loadData}
              className="bg-[#e67e22] hover:bg-[#f39c12] text-white px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-md"
            >
              📊 載入數據
            </button>
            
            <a 
              href="/api/v1/report/excel"
              className="bg-[#2980b9] hover:bg-[#3498db] text-white px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-md inline-block"
            >
              📥 Excel 報表
            </a>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto p-4 md:p-6">
        {error && (
          <div className="bg-[#e74c3c] bg-opacity-20 border border-[#e74c3c] text-[#eeeeee] p-4 rounded-lg mb-6 flex justify-between items-center">
            <span>⚠️ 錯誤提示：{error}</span>
            <button onClick={() => setError('')} className="text-sm font-bold opacity-80 hover:opacity-100">關閉</button>
          </div>
        )}

        {/* Tab Bar */}
        <div className="flex border-b border-[#30363d] mb-6 gap-2">
          {[
            { id: 'dashboard', label: '📊 數據看板與推薦' },
            { id: 'search', label: '🔍 全台車源篩選對比' },
            { id: 'stores', label: '📍 實體門市尋車' },
            { id: 'charts', label: '📈 市場統計圖表' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-5 py-3 text-sm font-bold border-b-2 transition-all ${
                activeTab === tab.id
                  ? 'border-[#00adb5] text-[#00adb5]'
                  : 'border-transparent text-[#b2bec3] hover:text-[#eeeeee]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Contents */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Metric Cards */}
            {analysis && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { title: "在售車輛總數", val: `${analysis.total_count} 輛`, color: "#00adb5" },
                  { title: "市場平均車價", val: `NT$ ${intVal(analysis.avg_current_price).toLocaleString()}`, color: "#58a6ff" },
                  { title: "市場平均里程", val: `${intVal(analysis.avg_mileage).toLocaleString()} km`, color: "#f59e0b" },
                  { title: "超值車源比例", val: `${(analysis.value_choices_count / analysis.total_count * 100).toFixed(1)}%`, color: "#2ecc71" }
                ].map((card, idx) => (
                  <div key={idx} className="bg-[#1e1e24] p-5 rounded-xl border border-[#30363d] shadow-md relative overflow-hidden">
                    <div className="absolute top-0 left-0 h-1 w-full" style={{ backgroundColor: card.color }}></div>
                    <span className="text-xs text-[#b2bec3] block mb-2">{card.title}</span>
                    <strong className="text-2xl font-bold" style={{ color: card.color }}>{card.val}</strong>
                  </div>
                ))}
              </div>
            )}

            {/* Top 10 Tables Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* CP Top 10 */}
              <div className="bg-[#1e1e24] p-5 rounded-xl border border-[#30363d] shadow-lg">
                <h2 className="text-lg font-bold text-[#2ecc71] mb-4 flex items-center gap-2">
                  🔥 全網性價比超值神車榜 Top 10 (越高越划算)
                </h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left text-[#eeeeee]">
                    <thead>
                      <tr className="border-b border-[#30363d] text-[#b2bec3] bg-[#121214]">
                        <th className="p-3">車款名稱</th>
                        <th className="p-3">年份</th>
                        <th className="p-3 text-right">里程 (km)</th>
                        <th className="p-3 text-right">價格 (元)</th>
                        <th className="p-3 text-center">CP指數</th>
                        <th className="p-3 text-center">標籤</th>
                      </tr>
                    </thead>
                    <tbody>
                      {products
                        .sort((a, b) => b.cp_index - a.cp_index)
                        .slice(0, 10)
                        .map((p, idx) => (
                          <tr key={idx} className="border-b border-[#30363d] hover:bg-[#21262d]">
                            <td className="p-3 font-semibold truncate max-w-[150px]">{p.title}</td>
                            <td className="p-3">{p.year}</td>
                            <td className="p-3 text-right">{intVal(p.mileage).toLocaleString()}</td>
                            <td className="p-3 text-right font-bold text-[#e67e22]">{intVal(p.current_price).toLocaleString()}</td>
                            <td className="p-3 text-center font-bold text-[#2ecc71]">{p.cp_index.toFixed(2)}</td>
                            <td className="p-3 text-center">
                              <span className="bg-[#2ecc71] text-white px-2 py-0.5 rounded text-[10px] font-bold">超值</span>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Low Mileage Top 10 */}
              <div className="bg-[#1e1e24] p-5 rounded-xl border border-[#30363d] shadow-lg">
                <h2 className="text-lg font-bold text-[#58a6ff] mb-4 flex items-center gap-2">
                  🏍️ 全網低里程優質精選 Top 10
                </h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left text-[#eeeeee]">
                    <thead>
                      <tr className="border-b border-[#30363d] text-[#b2bec3] bg-[#121214]">
                        <th className="p-3">車款名稱</th>
                        <th className="p-3">年份</th>
                        <th className="p-3 text-right">里程 (km)</th>
                        <th className="p-3 text-right">價格 (元)</th>
                        <th className="p-3 text-center">CP指數</th>
                        <th className="p-3 text-center">標籤</th>
                      </tr>
                    </thead>
                    <tbody>
                      {products
                        .sort((a, b) => a.mileage - b.mileage)
                        .slice(0, 10)
                        .map((p, idx) => (
                          <tr key={idx} className="border-b border-[#30363d] hover:bg-[#21262d]">
                            <td className="p-3 font-semibold truncate max-w-[150px]">{p.title}</td>
                            <td className="p-3">{p.year}</td>
                            <td className="p-3 text-right font-bold text-[#58a6ff]">{intVal(p.mileage).toLocaleString()}</td>
                            <td className="p-3 text-right text-[#e67e22]">{intVal(p.current_price).toLocaleString()}</td>
                            <td className="p-3 text-center">{p.cp_index.toFixed(2)}</td>
                            <td className="p-3 text-center">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold text-white ${
                                p.cp_label === '超值' ? 'bg-[#2ecc71]' : p.cp_label === '合理' ? 'bg-[#3498db]' : 'bg-[#e74c3c]'
                              }`}>{p.cp_label}</span>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'search' && (
          <div className="space-y-6">
            {/* Filter Panel */}
            <div className="bg-[#1e1e24] p-5 rounded-xl border border-[#30363d] shadow-md">
              <h3 className="text-sm font-bold text-[#00adb5] mb-4">🔧 進階車源條件篩選</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 items-end">
                <div>
                  <label className="text-xs text-[#b2bec3] block mb-2">廠牌品牌</label>
                  <select 
                    value={brandFilter} 
                    onChange={e => setBrandFilter(e.target.value)}
                    className="w-full bg-[#121214] border border-[#30363d] rounded-lg p-2 text-sm text-[#eeeeee] focus:border-[#00adb5]"
                  >
                    {brands.map((b, i) => <option key={i} value={b}>{b}</option>)}
                  </select>
                </div>
                
                <div>
                  <label className="text-xs text-[#b2bec3] block mb-2">實體門市</label>
                  <select 
                    value={locationFilter} 
                    onChange={e => setLocationFilter(e.target.value)}
                    className="w-full bg-[#121214] border border-[#30363d] rounded-lg p-2 text-sm text-[#eeeeee]"
                  >
                    <option value="全部">全部門市</option>
                    {BRANCHES.map((b, i) => <option key={i} value={b.name}>{b.name}</option>)}
                  </select>
                </div>

                <div>
                  <label className="text-xs text-[#b2bec3] block mb-2">預算上限 (萬元)</label>
                  <input 
                    type="number" 
                    placeholder="不限" 
                    value={priceMaxFilter}
                    onChange={e => setPriceMaxFilter(e.target.value)}
                    className="w-full bg-[#121214] border border-[#30363d] rounded-lg p-2 text-sm text-[#eeeeee]"
                  />
                </div>

                <div>
                  <label className="text-xs text-[#b2bec3] block mb-2">里程上限 (公里)</label>
                  <input 
                    type="number" 
                    placeholder="不限" 
                    value={mileMaxFilter}
                    onChange={e => setMileMaxFilter(e.target.value)}
                    className="w-full bg-[#121214] border border-[#30363d] rounded-lg p-2 text-sm text-[#eeeeee]"
                  />
                </div>

                <div>
                  <label className="text-xs text-[#b2bec3] block mb-2">關鍵字搜尋</label>
                  <input 
                    type="text" 
                    placeholder="搜尋型號..." 
                    value={kwFilter}
                    onChange={e => setKwFilter(e.target.value)}
                    className="w-full bg-[#121214] border border-[#30363d] rounded-lg p-2 text-sm text-[#eeeeee]"
                  />
                </div>

                <div className="flex gap-2">
                  <button 
                    disabled={selectedBikes.length < 2}
                    onClick={() => setShowCompareModal(true)}
                    className="w-full bg-[#3f51b5] hover:bg-[#5c6bc0] disabled:bg-gray-700 disabled:opacity-40 text-white p-2 rounded-lg text-sm font-semibold transition-all"
                  >
                    ⚖️ 對比 ({selectedBikes.length})
                  </button>
                </div>
              </div>
            </div>

            {/* List Table */}
            <div className="bg-[#1e1e24] p-5 rounded-xl border border-[#30363d] shadow-lg">
              <div className="flex justify-between items-center mb-4">
                <span className="text-xs text-[#b2bec3]">已篩選出 {sortedProducts.length} 筆車輛資訊</span>
                {selectedBikes.length > 0 && (
                  <button 
                    onClick={() => setSelectedBikes([])}
                    className="text-xs text-[#e74c3c] hover:underline"
                  >
                    清除選取
                  </button>
                )}
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left text-[#eeeeee]">
                  <thead>
                    <tr className="border-b border-[#30363d] text-[#b2bec3] bg-[#121214] select-none cursor-pointer">
                      <th className="p-3 text-center">選取</th>
                      <th className="p-3" onClick={() => handleSort('title')}>商品名稱 {sortField === 'title' && (sortAsc ? '▲' : '▼')}</th>
                      <th className="p-3 text-center" onClick={() => handleSort('brand')}>廠牌 {sortField === 'brand' && (sortAsc ? '▲' : '▼')}</th>
                      <th className="p-3 text-center" onClick={() => handleSort('displacement')}>排氣量 {sortField === 'displacement' && (sortAsc ? '▲' : '▼')}</th>
                      <th className="p-3 text-center" onClick={() => handleSort('year')}>年份 {sortField === 'year' && (sortAsc ? '▲' : '▼')}</th>
                      <th className="p-3 text-right" onClick={() => handleSort('mileage')}>里程 {sortField === 'mileage' && (sortAsc ? '▲' : '▼')}</th>
                      <th className="p-3 text-center" onClick={() => handleSort('location')}>門市 {sortField === 'location' && (sortAsc ? '▲' : '▼')}</th>
                      <th className="p-3 text-right" onClick={() => handleSort('current_price')}>價格 {sortField === 'current_price' && (sortAsc ? '▲' : '▼')}</th>
                      <th className="p-3 text-center" onClick={() => handleSort('cp_index')}>CP指數 {sortField === 'cp_index' && (sortAsc ? '▲' : '▼')}</th>
                      <th className="p-3 text-center" onClick={() => handleSort('cp_label')}>評級 {sortField === 'cp_label' && (sortAsc ? '▲' : '▼')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedProducts.map((p, idx) => {
                      const isSelected = !!selectedBikes.find(b => b.id === p.id);
                      return (
                        <tr 
                          key={idx} 
                          onClick={() => handleSelectBike(p)}
                          className={`border-b border-[#30363d] hover:bg-[#21262d] cursor-pointer ${
                            isSelected ? 'bg-[#00adb5] bg-opacity-10' : ''
                          }`}
                        >
                          <td className="p-3 text-center" onClick={e => e.stopPropagation()}>
                            <input 
                              type="checkbox" 
                              checked={isSelected}
                              onChange={() => handleSelectBike(p)}
                              className="rounded accent-[#00adb5]"
                            />
                          </td>
                          <td className="p-3 font-semibold">
                            <a href={p.url} target="_blank" onClick={e => e.stopPropagation()} className="hover:underline text-[#58a6ff]">
                              {p.title}
                            </a>
                          </td>
                          <td className="p-3 text-center">{p.brand}</td>
                          <td className="p-3 text-center">{p.displacement} cc</td>
                          <td className="p-3 text-center">{p.year}</td>
                          <td className="p-3 text-right font-mono">{intVal(p.mileage).toLocaleString()} km</td>
                          <td className="p-3 text-center text-[#b2bec3]">{p.location}</td>
                          <td className="p-3 text-right font-bold text-[#e67e22]">NT$ {intVal(p.current_price).toLocaleString()}</td>
                          <td className="p-3 text-center font-bold text-[#00adb5]">{p.cp_index.toFixed(2)}</td>
                          <td className="p-3 text-center">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold text-white ${
                              p.cp_label === '超值' ? 'bg-[#2ecc71]' : p.cp_label === '合理' ? 'bg-[#3498db]' : 'bg-[#e74c3c]'
                            }`}>{p.cp_label}</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'stores' && (
          <div className="bg-[#1e1e24] p-5 rounded-xl border border-[#30363d] shadow-lg">
            <h2 className="text-lg font-bold text-[#00adb5] mb-6">📍 貳輪嶼全台實體門市庫存尋車導航</h2>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {/* Branch List */}
              <div className="md:col-span-1 border-r border-[#30363d] pr-4 space-y-2 max-h-[500px] overflow-y-auto">
                {BRANCHES.map((branch, i) => (
                  <button
                    key={i}
                    onClick={() => setSelectedBranch(branch)}
                    className={`w-full text-left p-3 rounded-lg text-sm font-semibold transition-all ${
                      selectedBranch.name === branch.name
                        ? 'bg-[#00adb5] text-white shadow'
                        : 'hover:bg-[#121214] text-[#b2bec3]'
                    }`}
                  >
                    📍 {branch.name}
                  </button>
                ))}
              </div>

              {/* Branch Detail & Inventory */}
              <div className="md:col-span-3 space-y-6">
                <div className="bg-[#121214] p-4 rounded-xl border border-[#30363d]">
                  <h3 className="text-lg font-bold text-[#00adb5] mb-3">{selectedBranch.name}</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-[#b2bec3]">
                    <div>🗺️ 地址：<span className="text-[#eeeeee]">{selectedBranch.address}</span></div>
                    <div>📞 電話：<span className="text-[#eeeeee]">{selectedBranch.phone}</span></div>
                    <div>⏰ 營業時間：<span className="text-[#eeeeee]">{selectedBranch.hours}</span></div>
                    <div>🟢 LINE 專人諮詢：<a href={selectedBranch.line} target="_blank" className="text-[#58a6ff] hover:underline">點此加入</a></div>
                  </div>
                </div>

                {/* Branch Inventory Table */}
                <div>
                  <h4 className="text-sm font-bold text-[#eeeeee] mb-3">🚗 該店在庫車輛清單</h4>
                  <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-[#30363d] text-[#b2bec3] bg-[#121214]">
                          <th className="p-2">車款名稱</th>
                          <th className="p-2 text-center">年份</th>
                          <th className="p-2 text-right">里程 (km)</th>
                          <th className="p-2 text-right">價格 (元)</th>
                          <th className="p-2 text-center">CP值</th>
                          <th className="p-2 text-center">規劃書</th>
                        </tr>
                      </thead>
                      <tbody>
                        {products
                          .filter(p => {
                            const bShort = cleanLocName(selectedBranch.name);
                            const pLoc = cleanLocName(p.location || '');
                            return pLoc.includes(bShort);
                          })
                          .map((p, idx) => (
                            <tr key={idx} className="border-b border-[#30363d] hover:bg-[#21262d]">
                              <td className="p-2 font-semibold">{p.title}</td>
                              <td className="p-2 text-center">{p.year}</td>
                              <td className="p-2 text-right">{intVal(p.mileage).toLocaleString()}</td>
                              <td className="p-2 text-right text-[#e67e22]">{intVal(p.current_price).toLocaleString()}</td>
                              <td className="p-2 text-center font-bold text-[#00adb5]">{p.cp_index.toFixed(2)}</td>
                              <td className="p-2 text-center">
                                <button 
                                  onClick={() => exportAppointmentGuide(p)}
                                  className="bg-[#27ae60] hover:bg-[#2ecc71] text-white px-2 py-1 rounded text-[10px] font-semibold"
                                >
                                  📝 匯出
                                </button>
                              </td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'charts' && (
          <div className="bg-[#1e1e24] p-5 rounded-xl border border-[#30363d] shadow-lg space-y-6">
            <h2 className="text-lg font-bold text-[#00adb5] mb-4">📈 市場大數據統計與可視化圖表</h2>
            {charts ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-[#121214] p-3 rounded-lg border border-[#30363d] text-center">
                  <h3 className="text-xs font-bold text-[#b2bec3] mb-2">二手機車售價分布直方圖</h3>
                  <img src={charts.histogram_url} alt="Price Histogram" className="max-w-full rounded-md shadow-md" />
                </div>
                
                <div className="bg-[#121214] p-3 rounded-lg border border-[#30363d] text-center">
                  <h3 className="text-xs font-bold text-[#b2bec3] mb-2">里程數與售價關係散佈圖</h3>
                  <img src={charts.scatter_url} alt="Mileage Scatter Plot" className="max-w-full rounded-md shadow-md" />
                </div>

                <div className="bg-[#121214] p-3 rounded-lg border border-[#30363d] text-center md:col-span-2">
                  <h3 className="text-xs font-bold text-[#b2bec3] mb-2">熱門在庫品牌市佔率 (Top 5)</h3>
                  <img src={charts.brand_pie_url} alt="Brand Share Pie Chart" className="max-w-full md:max-w-[60%] mx-auto rounded-md shadow-md" />
                </div>
              </div>
            ) : (
              <div className="text-center py-20 text-[#b2bec3] text-sm">
                暫無圖表數據。請確認您已點擊「📊 載入數據」獲取圖表連結。
              </div>
            )}
          </div>
        )}
      </main>

      {/* Specifications Comparison Modal */}
      {showCompareModal && selectedBikes.length > 0 && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-70 backdrop-blur-sm">
          <div className="bg-[#1e1e24] rounded-xl border border-[#30363d] max-w-4xl w-full p-6 shadow-2xl relative">
            <button 
              onClick={() => setShowCompareModal(false)}
              className="absolute top-4 font-bold text-lg right-4 text-[#b2bec3] hover:text-[#eeeeee]"
            >
              ✕
            </button>
            <h3 className="text-lg font-bold text-[#00adb5] mb-6 flex items-center gap-2">
              ⚖️ 心儀機車規格橫向對比
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {selectedBikes.map((bike, index) => {
                const isBestPrice = bike.current_price === bestSpecs.minPrice;
                const isBestMileage = bike.mileage === bestSpecs.minMileage;
                const isBestYear = bike.year === bestSpecs.maxYear;

                return (
                  <div key={index} className="bg-[#121214] p-4 rounded-xl border border-[#30363d] space-y-4">
                    <h4 className="font-bold text-[#58a6ff] truncate text-sm">{bike.title}</h4>
                    <hr className="border-[#30363d]" />
                    <div className="space-y-2 text-xs">
                      <div className={`p-2 rounded ${isBestPrice ? 'bg-[#27ae60] bg-opacity-20 border border-[#27ae60]' : ''}`}>
                        💵 價格：<span className="font-bold text-[#e67e22]">NT$ {intVal(bike.current_price).toLocaleString()}</span> {isBestPrice && '🏆'}
                      </div>
                      
                      <div className={`p-2 rounded ${isBestMileage ? 'bg-[#27ae60] bg-opacity-20 border border-[#27ae60]' : ''}`}>
                        🛣️ 里程：<span className="font-bold">{intVal(bike.mileage).toLocaleString()} km</span> {isBestMileage && '🏆'}
                      </div>

                      <div className={`p-2 rounded ${isBestYear ? 'bg-[#27ae60] bg-opacity-20 border border-[#27ae60]' : ''}`}>
                        📅 年份：<span className="font-bold">{bike.year} 年</span> {isBestYear && '🏆'}
                      </div>

                      <div className="p-2">
                        🔥 CP值：<span className="font-bold text-[#00adb5]">{bike.cp_index.toFixed(2)} ({bike.cp_label})</span>
                      </div>

                      <div className="p-2 text-[#b2bec3]">
                        📍 實體門市：<span>{bike.location}</span>
                      </div>

                      <div className="p-2 text-[#b2bec3]">
                        🏍️ 排氣量：<span>{bike.displacement} cc</span>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => exportAppointmentGuide(bike)}
                      className="w-full bg-[#27ae60] hover:bg-[#2ecc71] text-white p-2 rounded-lg text-xs font-bold transition-all shadow"
                    >
                      📝 匯出此車預約看車規劃書
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="max-w-7xl mx-auto py-10 text-center text-xs text-[#b2bec3] border-t border-[#30363d] mt-10">
        <p>二手機車大數據分析平台 © 2026</p>
        <p className="mt-2 text-[10px]">部署指引：將此專案目錄推送到 GitHub 並導入 Vercel，設定 <code>DATABASE_URL</code> 可持久保存爬取數據。</p>
      </footer>
    </div>
  )
}

function intVal(val) {
  if (val === undefined || val === null) return 0;
  return Math.round(Number(val));
}
