import { useState } from 'react'
import Head from 'next/head'

export default function Home() {
  const [keywords, setKeywords] = useState('')
  const [maxPages, setMaxPages] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [selectedModel, setSelectedModel] = useState('')
  const [models, setModels] = useState([])
  const [parsedRows, setParsedRows] = useState([])
  const [parsedHeaders, setParsedHeaders] = useState([])

  function parseTitleMeta(title) {
    const meta = { store: '', year: '', brand: '', model: '', itemId: '' }
    if (!title || typeof title !== 'string') return meta
    let text = title.trim()

    const storeMatch = text.match(/^【([^】]+)】\s*/)
    if (storeMatch) {
      meta.store = storeMatch[1].trim()
      text = text.slice(storeMatch[0].length).trim()
    }

    const idMatch = text.match(/#\s*(\d+)\s*$/)
    if (idMatch) {
      meta.itemId = idMatch[1]
      text = text.slice(0, idMatch.index).trim()
    }

    const yearMatch = text.match(/^(\d{4})\s+/)
    if (yearMatch) {
      meta.year = yearMatch[1]
      text = text.slice(yearMatch[0].length).trim()
    }

    const parts = text.split(/\s+/).filter(Boolean)
    if (parts.length > 1) {
      meta.brand = parts[0]
      meta.model = parts.slice(1).join(' ')
    } else {
      meta.model = text
    }

    return meta
  }

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setResult(null)
    setSelectedModel('')
    setModels([])
    setParsedRows([])
    setParsedHeaders([])

    try {
      const resp = await fetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keywords, max_pages: Number(maxPages) })
      })

      const text = await resp.text()
      try {
        const data = JSON.parse(text)
        if (!resp.ok) {
          setResult({ error: `API 錯誤 (${resp.status}): ${data.error || text}`, logs: data.logs })
        } else {
          const parsed = parseCSV(data.csv)
          const titleIndex = parsed.headers.indexOf('title')
          const modelIndex = parsed.headers.indexOf('model')
          const brandIndex = parsed.headers.indexOf('brand')
          const itemIdIndex = parsed.headers.indexOf('item_id')
          const priceIndex = parsed.headers.indexOf('price')
          const mileageIndex = parsed.headers.indexOf('mileage')
          const yearIndex = parsed.headers.indexOf('year')
          const ccIndex = parsed.headers.indexOf('cc')
          const storeIndex = parsed.headers.indexOf('store')
          const urlIndex = parsed.headers.indexOf('url')

          const rows = parsed.rows.map(row => {
            const title = titleIndex >= 0 ? row[titleIndex] : ''
            const meta = parseTitleMeta(title)
            const modelValue = modelIndex >= 0 && row[modelIndex] ? row[modelIndex] : meta.model
            return {
              row,
              title,
              store: storeIndex >= 0 && row[storeIndex] ? row[storeIndex] : meta.store,
              year: yearIndex >= 0 && row[yearIndex] ? row[yearIndex] : meta.year,
              brand: brandIndex >= 0 && row[brandIndex] ? row[brandIndex] : meta.brand,
              model: modelValue,
              itemId: itemIdIndex >= 0 && row[itemIdIndex] ? row[itemIdIndex] : meta.itemId,
              price: priceIndex >= 0 ? parseInt(row[priceIndex]) || null : null,
              mileage: mileageIndex >= 0 ? parseInt(row[mileageIndex]) || null : null,
              cc: ccIndex >= 0 ? parseInt(row[ccIndex]) || null : null,
              url: urlIndex >= 0 ? row[urlIndex] : '',
            }
          })

          const uniqueModels = [...new Set(rows.map(item => item.model).filter(Boolean))]
            .sort()
            .slice(0, 100)

          setModels(uniqueModels)
          setParsedHeaders(parsed.headers)
          setParsedRows(rows)
          setResult(data)
        }
      } catch (jsonError) {
        setResult({ error: `無效 JSON 回應 (${resp.status}): ${text}` })
      }
    } catch (error) {
      setResult({ error: `請求失敗: ${String(error)}` })
    } finally {
      setLoading(false)
    }
  }

  function download(filename, content, mime = 'text/plain') {
    const blob = new Blob([content], { type: mime })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  function parseCSV(csv) {
    const normalized = csv.replace(/\r\n?/g, '\n')
    const rows = []
    let current = ''
    let row = []
    let inQuotes = false

    for (let i = 0; i < normalized.length; i += 1) {
      const char = normalized[i]
      if (char === '"') {
        if (inQuotes && normalized[i + 1] === '"') {
          current += '"'
          i += 1
        } else {
          inQuotes = !inQuotes
        }
      } else if (char === ',' && !inQuotes) {
        row.push(current)
        current = ''
      } else if (char === '\n' && !inQuotes) {
        row.push(current)
        rows.push(row)
        row = []
        current = ''
      } else {
        current += char
      }
    }

    if (current !== '' || row.length > 0) {
      row.push(current)
      rows.push(row)
    }

    if (rows.length === 0) return { headers: [], rows: [] }
    const headers = rows[0].map(h => h.trim())
    const dataRows = rows.slice(1).map(r => r.map(cell => cell.trim()))
    return { headers, rows: dataRows }
  }

  function getFilteredData() {
    if (!parsedRows.length || !selectedModel) {
      return { headers: parsedHeaders, rows: [], stats: {}, storeStats: [] }
    }

    const filtered = parsedRows.filter(item => item.model === selectedModel)
    const stats = {
      count: filtered.length,
      avgPrice: 0,
      minPrice: 0,
      maxPrice: 0,
      avgMileage: 0,
      minMileage: 0,
      maxMileage: 0,
      avgYear: 0,
      minYear: 0,
      maxYear: 0,
      avgCC: 0,
    }

    const storeMap = {}
    const prices = []
    const mileages = []
    const years = []
    const ccs = []

    filtered.forEach(item => {
      if (item.price > 0) prices.push(item.price)
      if (item.mileage > 0) mileages.push(item.mileage)
      if (item.year && !Number.isNaN(Number(item.year))) years.push(Number(item.year))
      if (item.cc > 0) ccs.push(item.cc)

      const storeName = item.store || '未知販售地'
      if (!storeMap[storeName]) {
        storeMap[storeName] = { count: 0, prices: [], mileages: [], minPrice: Infinity, maxPrice: 0 }
      }
      const storeStat = storeMap[storeName]
      storeStat.count += 1
      if (item.price > 0) {
        storeStat.prices.push(item.price)
        storeStat.minPrice = Math.min(storeStat.minPrice, item.price)
        storeStat.maxPrice = Math.max(storeStat.maxPrice, item.price)
      }
      if (item.mileage > 0) {
        storeStat.mileages.push(item.mileage)
      }
    })

    if (prices.length > 0) {
      stats.avgPrice = Math.round(prices.reduce((a, b) => a + b, 0) / prices.length)
      stats.minPrice = Math.min(...prices)
      stats.maxPrice = Math.max(...prices)
    }
    if (mileages.length > 0) {
      stats.avgMileage = Math.round(mileages.reduce((a, b) => a + b, 0) / mileages.length)
      stats.minMileage = Math.min(...mileages)
      stats.maxMileage = Math.max(...mileages)
    }
    if (years.length > 0) {
      stats.avgYear = Math.round(years.reduce((a, b) => a + b, 0) / years.length)
      stats.minYear = Math.min(...years)
      stats.maxYear = Math.max(...years)
    }
    if (ccs.length > 0) {
      stats.avgCC = Math.round(ccs.reduce((a, b) => a + b, 0) / ccs.length)
    }

    const storeStats = Object.keys(storeMap).map(storeName => {
      const storeStat = storeMap[storeName]
      return {
        store: storeName,
        count: storeStat.count,
        avgPrice: storeStat.prices.length > 0 ? Math.round(storeStat.prices.reduce((a, b) => a + b, 0) / storeStat.prices.length) : 0,
        minPrice: storeStat.minPrice === Infinity ? 0 : storeStat.minPrice,
        maxPrice: storeStat.maxPrice,
        avgMileage: storeStat.mileages.length > 0 ? Math.round(storeStat.mileages.reduce((a, b) => a + b, 0) / storeStat.mileages.length) : 0,
      }
    }).sort((a, b) => b.count - a.count)

    return { headers: parsedHeaders, rows: filtered, stats, storeStats }
  }

  const filteredData = getFilteredData()

  return (
    <>
      <Head>
        <title>貳輪嶼二手機車數據分析系統</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      </Head>

      <style dangerouslySetInnerHTML={{ __html: `
        body {
          background: radial-gradient(circle at top, #0f172a, #020617);
          color: #f1f5f9;
          font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          margin: 0;
          padding: 0;
          min-height: 100vh;
        }

        .dashboard-container {
          max-width: 1300px;
          margin: 0 auto;
          padding: 40px 20px;
        }

        .header-panel {
          text-align: center;
          margin-bottom: 40px;
        }

        .title-gradient {
          background: linear-gradient(135deg, #38bdf8, #818cf8);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          font-weight: 700;
          font-size: 2.6rem;
          margin: 0 0 10px 0;
          letter-spacing: -0.5px;
        }

        .subtitle {
          color: #94a3b8;
          font-size: 1.1rem;
          margin: 0;
        }

        .glass-card {
          background: rgba(15, 23, 42, 0.6);
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 16px;
          padding: 24px;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
          margin-bottom: 30px;
        }

        .glass-card h2, .glass-card h3 {
          margin-top: 0;
          font-weight: 600;
          color: #f8fafc;
        }

        .form-grid {
          display: grid;
          grid-template-columns: 1fr 120px auto;
          gap: 16px;
          align-items: flex-end;
        }

        @media (max-width: 768px) {
          .form-grid {
            grid-template-columns: 1fr;
          }
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .form-group label {
          font-size: 0.9rem;
          font-weight: 500;
          color: #94a3b8;
        }

        .input-field {
          background: rgba(30, 41, 59, 0.7);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #fff;
          border-radius: 8px;
          padding: 12px;
          font-size: 1rem;
          transition: all 0.2s ease;
        }

        .input-field:focus {
          outline: none;
          border-color: #38bdf8;
          box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
        }

        .primary-btn {
          background: linear-gradient(135deg, #0284c7, #4f46e5);
          color: #fff;
          border: none;
          border-radius: 8px;
          padding: 14px 28px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
          height: 48px;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .primary-btn:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5);
        }

        .primary-btn:disabled {
          background: #334155;
          color: #94a3b8;
          cursor: not-allowed;
          box-shadow: none;
        }

        .sec-btn {
          background: rgba(30, 41, 59, 0.8);
          color: #f1f5f9;
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          padding: 10px 18px;
          font-size: 0.9rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
          display: inline-flex;
          align-items: center;
          gap: 8px;
        }

        .sec-btn:hover {
          background: rgba(51, 65, 85, 0.8);
          border-color: rgba(255, 255, 255, 0.2);
        }

        .excel-btn {
          background: rgba(31, 127, 32, 0.2);
          color: #4ade80;
          border: 1px solid rgba(74, 222, 128, 0.3);
        }

        .excel-btn:hover {
          background: rgba(31, 127, 32, 0.4);
          border-color: rgba(74, 222, 128, 0.5);
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }

        .stat-item {
          background: rgba(30, 41, 59, 0.4);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 12px;
          padding: 16px;
          text-align: center;
        }

        .stat-val {
          font-size: 1.8rem;
          font-weight: 700;
          color: #38bdf8;
          margin-top: 4px;
        }

        .stat-val-purple {
          color: #c084fc;
        }

        .stat-val-green {
          color: #4ade80;
        }

        .stat-val-orange {
          color: #fb923c;
        }

        .stat-label {
          font-size: 0.85rem;
          color: #94a3b8;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .table-wrapper {
          overflow-x: auto;
          border-radius: 12px;
          border: 1px solid rgba(255, 255, 255, 0.05);
          background: rgba(15, 23, 42, 0.4);
          margin-bottom: 20px;
        }

        .custom-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.9rem;
          text-align: left;
        }

        .custom-table th {
          background: rgba(15, 23, 42, 0.8);
          color: #38bdf8;
          padding: 14px 16px;
          font-weight: 600;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .custom-table td {
          padding: 14px 16px;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          color: #e2e8f0;
        }

        .custom-table tr:hover {
          background: rgba(255, 255, 255, 0.02);
        }

        .log-terminal {
          background: #090d16;
          border: 1px solid #1e293b;
          border-radius: 8px;
          padding: 16px;
          font-family: 'Consolas', monospace;
          font-size: 0.85rem;
          max-height: 240px;
          overflow-y: auto;
          color: #38bdf8;
        }

        .section-divider {
          border-top: 1px solid rgba(255, 255, 255, 0.08);
          margin: 30px 0;
        }

        .select-wrapper {
          position: relative;
        }

        .select-field {
          width: 100%;
          max-width: 500px;
          background: rgba(30, 41, 59, 0.7);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #fff;
          border-radius: 8px;
          padding: 12px;
          font-size: 1rem;
          cursor: pointer;
        }

        .select-field:focus {
          outline: none;
          border-color: #38bdf8;
        }
      ` }} />

      <div className="dashboard-container">
        <header className="header-panel">
          <h1 className="title-gradient">貳輪嶼二手機車數據分析系統</h1>
          <p className="subtitle">跨店車款分類分析 • 跨店價格比較 • 報表導出</p>
        </header>

        <section className="glass-card">
          <h2>系統操作與條件篩選</h2>
          <form onSubmit={submit} className="form-grid">
            <div className="form-group">
              <label>搜尋關鍵字：</label>
              <input
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                className="input-field"
                placeholder="例如: gogoro 或 125 或 SYM"
              />
            </div>

            <div className="form-group">
              <label>最大頁數：</label>
              <input
                type="number"
                value={maxPages}
                min={1}
                onChange={(e) => setMaxPages(e.target.value)}
                className="input-field"
              />
            </div>

            <button type="submit" disabled={loading} className="primary-btn">
              {loading ? (
                <span className="pulse">正在進行抓取與分析...</span>
              ) : (
                '開始抓取並分析'
              )}
            </button>
          </form>
        </section>

        {result && (
          <section className="glass-card">
            <h2>分析結果與數據導出</h2>

            {result.error && (
              <div style={{ color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)', padding: 14, borderRadius: 8, border: '1px solid rgba(239, 68, 68, 0.2)', marginBottom: 20 }}>
                {result.error}
              </div>
            )}

            {result.logs && (
              <details style={{ marginBottom: 20 }}>
                <summary style={{ cursor: 'pointer', fontWeight: '500', color: '#94a3b8', marginBottom: 10 }}>
                  檢視執行日誌（{result.logs.length} 行）
                </summary>
                <div className="log-terminal">
                  {result.logs.join('\n')}
                </div>
              </details>
            )}

            {result.rows !== undefined && (
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 24 }}>
                <span className="accent-badge">
                  ✓ 成功抓取與洗淨 {result.rows} 筆資料
                </span>
                
                {result.csv && (
                  <button onClick={() => download(result.csv_filename || 'listings.csv', result.csv, 'text/csv')} className="sec-btn">
                    下載 CSV 原始檔
                  </button>
                )}

                {result.excel && (
                  <button onClick={() => {
                    const link = document.createElement('a');
                    link.href = 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,' + result.excel;
                    link.download = result.excel_filename || 'report.xlsx';
                    link.click();
                  }} className="sec-btn excel-btn">
                    下載 Excel (含分頁分析)
                  </button>
                )}

                {result.html && (
                  <button onClick={() => download(result.html_filename || 'report.html', result.html, 'text/html')} className="sec-btn">
                    下載 HTML 立體報表
                  </button>
                )}
              </div>
            )}

            {models.length > 0 && (
              <>
                <div className="section-divider" />
                
                <div style={{ marginBottom: 24 }}>
                  <label style={{ display: 'block', fontSize: '1rem', fontWeight: '600', color: '#38bdf8', marginBottom: 8 }}>
                    選擇機車車款（不同分店之同款車已自動彙整）：
                  </label>
                  <div className="select-wrapper">
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="select-field"
                    >
                      <option value="">-- 請選擇車款 --</option>
                      {models.map((model, idx) => (
                        <option key={idx} value={model}>{model}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {!selectedModel && (
                  <div style={{ background: 'rgba(56, 189, 248, 0.05)', border: '1px dashed rgba(56, 189, 248, 0.2)', borderRadius: 12, padding: 20, textAlign: 'center', color: '#94a3b8' }}>
                    請在上方下拉式選單選擇欲查詢的「車款」，系統將會分類顯示該車款在全台各分店的價格比較與里程數據。
                  </div>
                )}

                {selectedModel && filteredData.rows.length > 0 && (
                  <>
                    <h3 style={{ color: '#38bdf8', marginBottom: 16 }}>
                      車款數據分析：{selectedModel}
                    </h3>
                    
                    <div className="stats-grid">
                      <div className="stat-item">
                        <div className="stat-label">上架總筆數</div>
                        <div className="stat-val">{filteredData.stats.count} 筆</div>
                      </div>
                      
                      {filteredData.stats.avgPrice > 0 && (
                        <div className="stat-item">
                          <div className="stat-label">平均價格</div>
                          <div className="stat-val stat-val-purple">NT$ {filteredData.stats.avgPrice.toLocaleString()}</div>
                        </div>
                      )}

                      {filteredData.stats.minPrice > 0 && (
                        <div className="stat-item">
                          <div className="stat-label">價格區間</div>
                          <div className="stat-val stat-val-green">
                            NT$ {filteredData.stats.minPrice.toLocaleString()} ~ {filteredData.stats.maxPrice.toLocaleString()}
                          </div>
                        </div>
                      )}

                      {filteredData.stats.avgMileage > 0 && (
                        <div className="stat-item">
                          <div className="stat-label">平均里程</div>
                          <div className="stat-val stat-val-orange">{filteredData.stats.avgMileage.toLocaleString()} km</div>
                        </div>
                      )}

                      {filteredData.stats.minYear > 0 && (
                        <div className="stat-item">
                          <div className="stat-label">出廠年份區間</div>
                          <div className="stat-val">
                            {filteredData.stats.minYear === filteredData.stats.maxYear ? filteredData.stats.minYear : `${filteredData.stats.minYear} ~ ${filteredData.stats.maxYear}`}
                          </div>
                        </div>
                      )}

                      {filteredData.stats.avgCC > 0 && (
                        <div className="stat-item">
                          <div className="stat-label">排氣量 (平均)</div>
                          <div className="stat-val">{filteredData.stats.avgCC} cc</div>
                        </div>
                      )}
                    </div>

                    {filteredData.storeStats.length > 0 && (
                      <div style={{ marginBottom: 30 }}>
                        <h4 style={{ color: '#94a3b8', margin: '0 0 12px 0' }}>各店售價與上架車數比較（跨店比較）</h4>
                        <div className="table-wrapper">
                          <table className="custom-table">
                            <thead>
                              <tr>
                                <th>販售分店</th>
                                <th style={{ textAlign: 'center' }}>上架數量</th>
                                <th style={{ textAlign: 'right' }}>最低價格</th>
                                <th style={{ textAlign: 'right' }}>最高價格</th>
                                <th style={{ textAlign: 'right' }}>平均價格</th>
                                <th style={{ textAlign: 'right' }}>平均行駛里程</th>
                              </tr>
                            </thead>
                            <tbody>
                              {filteredData.storeStats.map((store, idx) => (
                                <tr key={idx}>
                                  <td>{store.store}</td>
                                  <td style={{ textAlign: 'center', fontWeight: 'bold' }}>{store.count}</td>
                                  <td style={{ textAlign: 'right', color: '#4ade80' }}>
                                    {store.minPrice > 0 ? `NT$ ${store.minPrice.toLocaleString()}` : '-'}
                                  </td>
                                  <td style={{ textAlign: 'right', color: '#f87171' }}>
                                    {store.maxPrice > 0 ? `NT$ ${store.maxPrice.toLocaleString()}` : '-'}
                                  </td>
                                  <td style={{ textAlign: 'right', fontWeight: 'bold' }}>
                                    {store.avgPrice > 0 ? `NT$ ${store.avgPrice.toLocaleString()}` : '-'}
                                  </td>
                                  <td style={{ textAlign: 'right', color: '#fb923c' }}>
                                    {store.avgMileage > 0 ? `${store.avgMileage.toLocaleString()} km` : '-'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}

                    <div>
                      <h4 style={{ color: '#94a3b8', margin: '0 0 12px 0' }}>詳細車輛清單</h4>
                      <div className="table-wrapper">
                        <table className="custom-table">
                          <thead>
                            <tr>
                              <th style={{ width: 50, textAlign: 'center' }}>#</th>
                              <th>販售分店</th>
                              <th style={{ textAlign: 'right' }}>售價</th>
                              <th style={{ textAlign: 'right' }}>里程</th>
                              <th style={{ textAlign: 'center' }}>出廠年份</th>
                              <th style={{ textAlign: 'center' }}>排氣量</th>
                              <th>官網商品連結</th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredData.rows.slice(0, 50).map((item, rowIndex) => (
                              <tr key={rowIndex}>
                                <td style={{ textAlign: 'center', color: '#94a3b8' }}>{rowIndex + 1}</td>
                                <td>{item.store || '未知店家'}</td>
                                <td style={{ textAlign: 'right', fontWeight: 'bold', color: '#c084fc' }}>
                                  {item.price > 0 ? `NT$ ${item.price.toLocaleString()}` : '電洽'}
                                </td>
                                <td style={{ textAlign: 'right', color: '#fb923c' }}>
                                  {item.mileage > 0 ? `${item.mileage.toLocaleString()} km` : '-'}
                                </td>
                                <td style={{ textAlign: 'center' }}>{item.year || '-'}</td>
                                <td style={{ textAlign: 'center' }}>{item.cc > 0 ? `${item.cc} cc` : '-'}</td>
                                <td>
                                  {item.url ? (
                                    <a href={item.url} target="_blank" rel="noreferrer" style={{ color: '#38bdf8', textDecoration: 'none', fontWeight: '500' }}>
                                      前往貳輪嶼商品頁 ↗
                                    </a>
                                  ) : (
                                    '-'
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      {filteredData.rows.length > 50 && (
                        <div style={{ textAlign: 'center', padding: '10px 0', color: '#64748b', fontSize: '0.85rem' }}>
                          ...僅顯示前 50 筆，請點擊上方「下載 Excel」或「下載 HTML」查看完整數據。
                        </div>
                      )}
                    </div>
                  </>
                )}
              </>
            )}

            {result.png && (
              <div style={{ marginTop: 30 }}>
                <h3 style={{ color: '#38bdf8', marginBottom: 16 }}>數據分析圖表</h3>
                <div style={{ background: 'rgba(15, 23, 42, 0.5)', border: '1px solid rgba(255, 255, 255, 0.05)', borderRadius: 12, padding: 16, textAlign: 'center' }}>
                  <img src={`data:image/png;base64,${result.png}`} alt="Analysis" style={{ maxWidth: '100%', borderRadius: 8 }} />
                </div>
              </div>
            )}
          </section>
        )}
      </div>
    </>
  )
}
