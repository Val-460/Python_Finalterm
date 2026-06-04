import { useState } from 'react'

export default function Home() {
  const [keywords, setKeywords] = useState('')
  const [maxPages, setMaxPages] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [selectedModel, setSelectedModel] = useState('')
  const [models, setModels] = useState([])

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setResult(null)
    setSelectedModel('')
    setModels([])

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
          // Extract unique models from CSV
          const parsed = parseCSV(data.csv)
          const titleIndex = parsed.headers.indexOf('title')
          const uniqueModels = titleIndex >= 0 
            ? [...new Set(parsed.rows.map(row => row[titleIndex]).filter(Boolean))]
                .sort()
                .slice(0, 100)
            : []
          setModels(uniqueModels)
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

  function getParsedCSV() {
    if (!result || !result.csv) return { headers: [], rows: [] }
    return parseCSV(result.csv)
  }

  function getFilteredData(parsed) {
    if (!parsed.headers.length || !selectedModel) {
      return { headers: [], rows: [], stats: {}, storeStats: [] }
    }

    const titleIndex = parsed.headers.indexOf('title')
    const priceIndex = parsed.headers.indexOf('price')
    const mileageIndex = parsed.headers.indexOf('mileage')
    const yearIndex = parsed.headers.indexOf('year')
    const ccIndex = parsed.headers.indexOf('cc')
    const storeIndex = parsed.headers.indexOf('store')

    const filtered = parsed.rows.filter(row => titleIndex >= 0 && row[titleIndex] === selectedModel)
    const stats = {
      count: filtered.length,
      avgPrice: 0,
      minPrice: 0,
      maxPrice: 0,
      avgMileage: 0,
      minMileage: 0,
      maxMileage: 0,
      avgYear: 0,
      avgCC: 0,
    }

    const storeMap = {}
    const prices = []
    const mileages = []
    const years = []
    const ccs = []

    filtered.forEach(row => {
      const price = parseInt(row[priceIndex]) || 0
      const mileage = parseInt(row[mileageIndex]) || 0
      const year = parseInt(row[yearIndex]) || 0
      const cc = parseInt(row[ccIndex]) || 0
      const store = storeIndex >= 0 ? (row[storeIndex] || '未知販售地') : '未知販售地'

      if (price > 0) prices.push(price)
      if (mileage > 0) mileages.push(mileage)
      if (year > 0) years.push(year)
      if (cc > 0) ccs.push(cc)

      if (!storeMap[store]) {
        storeMap[store] = { count: 0, prices: [], mileages: [], minPrice: Infinity, maxPrice: 0 }
      }
      const storeStat = storeMap[store]
      storeStat.count += 1
      if (price > 0) {
        storeStat.prices.push(price)
        storeStat.minPrice = Math.min(storeStat.minPrice, price)
        storeStat.maxPrice = Math.max(storeStat.maxPrice, price)
      }
      if (mileage > 0) {
        storeStat.mileages.push(mileage)
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
    }
    if (ccs.length > 0) {
      stats.avgCC = Math.round(ccs.reduce((a, b) => a + b, 0) / ccs.length)
    }

    const storeStats = Object.keys(storeMap).map(storeName => {
      const storeStat = storeMap[storeName]
      const avgPrice = storeStat.prices.length > 0 ? Math.round(storeStat.prices.reduce((a, b) => a + b, 0) / storeStat.prices.length) : 0
      const avgMileage = storeStat.mileages.length > 0 ? Math.round(storeStat.mileages.reduce((a, b) => a + b, 0) / storeStat.mileages.length) : 0
      return {
        store: storeName,
        count: storeStat.count,
        avgPrice,
        minPrice: storeStat.minPrice === Infinity ? 0 : storeStat.minPrice,
        maxPrice: storeStat.maxPrice,
        avgMileage,
      }
    }).sort((a, b) => b.count - a.count)

    return { headers: parsed.headers, rows: filtered, stats, storeStats }
  }

  const parsedCSV = getParsedCSV()
  const filteredData = getFilteredData(parsedCSV)

  return (
    <div style={{ maxWidth: 1200, margin: '40px auto', fontFamily: 'Arial, sans-serif', lineHeight: 1.6 }}>
      <h1>2Motor 二手機車 Serverless Web UI</h1>
      <p>這個網站將原本的二手機車爬蟲與分析程式包裝為一個可直接部署到 Vercel 的 Serverless 應用。</p>
      <p>輸入搜尋關鍵字與最大頁數後，網站會呼叫 serverless Python API，抓取 2Motor 二手機車資料並產出報表。</p>

      <section style={{ padding: 18, border: '1px solid #e0e0e0', borderRadius: 10, background: '#f9fafb', marginTop: 24 }}>
        <h2>操作說明</h2>
        <ol>
          <li>輸入「關鍵字」來篩選車款，例如「125」、「Gogoro」、「SYM」。</li>
          <li>設定要抓取的最大頁數，數字越大可能抓到更多資料。</li>
          <li>按下「開始抓取並分析」，等待結果顯示於下方。</li>
          <li>若成功，您可以直接在網站上瀏覽試算表、下載 CSV 與 HTML 報表，並檢視分析圖。</li>
        </ol>
      </section>

      <form onSubmit={submit} style={{ display: 'grid', gap: 14, marginTop: 24 }}>
        <label style={{ display: 'flex', flexDirection: 'column' }}>
          關鍵字：
          <input
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            style={{ width: '100%', padding: '10px', marginTop: 6 }}
            placeholder="例如: gogoro 或 125"
          />
        </label>

        <label style={{ display: 'flex', flexDirection: 'column' }}>
          最大頁數：
          <input
            type="number"
            value={maxPages}
            min={1}
            onChange={(e) => setMaxPages(e.target.value)}
            style={{ width: 120, padding: '10px', marginTop: 6 }}
          />
        </label>

        <button type="submit" disabled={loading} style={{ width: 220, padding: '12px 18px', background: '#0070f3', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
          {loading ? '執行中...' : '開始抓取並分析'}
        </button>
      </form>

      {result && (
        <div style={{ marginTop: 30, padding: 18, border: '1px solid #ddd', borderRadius: 10, background: '#fff' }}>
          <h2>執行結果</h2>
          {result.error && <pre style={{ color: 'red', whiteSpace: 'pre-wrap' }}>{result.error}</pre>}
          {result.logs && (
            <details style={{ marginBottom: 16 }}>
              <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>檢視日誌（{result.logs.length} 行）</summary>
              <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 240, overflow: 'auto', background: '#f4f4f4', padding: 12, borderRadius: 6, marginTop: 8 }}>{result.logs.join('\n')}</pre>
            </details>
          )}
          {result.rows !== undefined && <div style={{ fontSize: 16, fontWeight: 'bold', marginBottom: 12 }}>✓ 成功抓取 {result.rows} 筆資料</div>}

          {result.csv && (
            <div style={{ marginBottom: 24 }}>
              <h3>車款篩選與數據分析</h3>
              <div style={{ marginBottom: 12, display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
                <div style={{ fontSize: 14, color: '#333' }}>
                  可選車款：{models.length} 種
                </div>
                <button onClick={() => download(result.csv_filename || 'listings.csv', result.csv, 'text/csv')} style={{ padding: '8px 12px', background: '#111', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>下載 CSV</button>
                {result.excel && (
                  <button onClick={() => { const link = document.createElement('a'); link.href = 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,' + result.excel; link.download = result.excel_filename || 'report.xlsx'; link.click(); }} style={{ padding: '8px 12px', background: '#1f7f20', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>下載 Excel</button>
                )}
              </div>

              {models.length > 0 && (
                <div style={{ marginBottom: 20, padding: 14, background: '#f5f9fc', borderRadius: 6, border: '1px solid #d1e3f2' }}>
                  <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <strong>請先選擇車款：</strong>
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      style={{ padding: 10, fontSize: 14, borderRadius: 4, border: '1px solid #999', width: '100%', maxWidth: 500 }}
                    >
                      <option value="">-- 選擇車款 --</option>
                      {models.map((model, idx) => (
                        <option key={idx} value={model}>{model}</option>
                      ))}
                    </select>
                  </label>
                </div>
              )}

              {!selectedModel && models.length > 0 && (
                <div style={{ marginBottom: 18, padding: 14, background: '#fff4e5', borderRadius: 6, border: '1px solid #ffd699' }}>
                  <strong>提示：</strong> 請先從上方下拉選單選擇車款，系統會顯示該車款的販售位置、價格與里程統計。
                </div>
              )}

              {selectedModel && filteredData.rows.length === 0 && (
                <div style={{ marginBottom: 18, padding: 14, background: '#fdecea', borderRadius: 6, border: '1px solid #f5c6cb', color: '#721c24' }}>
                  已選車款：<strong>{selectedModel}</strong>，目前沒有符合資料。
                </div>
              )}

              {selectedModel && filteredData.rows.length > 0 && (
                <>
                  <div style={{ marginBottom: 18, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
                    <div style={{ background: '#e3f2fd', border: '1px solid #90caf9', borderRadius: 6, padding: 12, textAlign: 'center' }}>
                      <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>總筆數</div>
                      <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1976d2' }}>{filteredData.stats.count}</div>
                    </div>
                    {filteredData.stats.avgPrice > 0 && (
                      <div style={{ background: '#f3e5f5', border: '1px solid #ce93d8', borderRadius: 6, padding: 12, textAlign: 'center' }}>
                        <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>平均價格</div>
                        <div style={{ fontSize: 18, fontWeight: 'bold', color: '#7b1fa2' }}>NT${filteredData.stats.avgPrice.toLocaleString()}</div>
                      </div>
                    )}
                    {filteredData.stats.minPrice > 0 && (
                      <div style={{ background: '#fce4ec', border: '1px solid #f48fb1', borderRadius: 6, padding: 12, textAlign: 'center' }}>
                        <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>價格範圍</div>
                        <div style={{ fontSize: 14, fontWeight: 'bold', color: '#c2185b' }}>NT${filteredData.stats.minPrice.toLocaleString()} ~ NT${filteredData.stats.maxPrice.toLocaleString()}</div>
                      </div>
                    )}
                    {filteredData.stats.avgMileage > 0 && (
                      <div style={{ background: '#e8f5e9', border: '1px solid #81c784', borderRadius: 6, padding: 12, textAlign: 'center' }}>
                        <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>平均里程</div>
                        <div style={{ fontSize: 18, fontWeight: 'bold', color: '#388e3c' }}>{filteredData.stats.avgMileage.toLocaleString()} km</div>
                      </div>
                    )}
                    {filteredData.stats.minMileage > 0 && (
                      <div style={{ background: '#ffe0b2', border: '1px solid #ffb74d', borderRadius: 6, padding: 12, textAlign: 'center' }}>
                        <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>里程範圍</div>
                        <div style={{ fontSize: 14, fontWeight: 'bold', color: '#e65100' }}>{filteredData.stats.minMileage.toLocaleString()} ~ {filteredData.stats.maxMileage.toLocaleString()} km</div>
                      </div>
                    )}
                    {filteredData.stats.avgYear > 0 && (
                      <div style={{ background: '#fff3e0', border: '1px solid #ffe0b2', borderRadius: 6, padding: 12, textAlign: 'center' }}>
                        <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>平均年份</div>
                        <div style={{ fontSize: 18, fontWeight: 'bold', color: '#ef6c00' }}>{filteredData.stats.avgYear}</div>
                      </div>
                    )}
                    {filteredData.stats.avgCC > 0 && (
                      <div style={{ background: '#f1f8e9', border: '1px solid #c5e1a5', borderRadius: 6, padding: 12, textAlign: 'center' }}>
                        <div style={{ fontSize: 12, color: '#555', marginBottom: 4 }}>平均排氣量</div>
                        <div style={{ fontSize: 18, fontWeight: 'bold', color: '#558b2f' }}>{filteredData.stats.avgCC} cc</div>
                      </div>
                    )}
                  </div>

                  {filteredData.storeStats.length > 0 && (
                    <div style={{ marginBottom: 18 }}>
                      <div style={{ fontSize: 16, fontWeight: 'bold', marginBottom: 10 }}>不同販售位置統計</div>
                      <div style={{ overflowX: 'auto', border: '1px solid #ccc', borderRadius: 6, boxShadow: '0 2px 4px rgba(0,0,0,0.08)' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, backgroundColor: '#fff' }}>
                          <thead>
                            <tr style={{ background: '#1976d2', color: '#fff' }}>
                              <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'left' }}>販售位置</th>
                              <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'center' }}>筆數</th>
                              <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>平均價格</th>
                              <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>最低價格</th>
                              <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>最高價格</th>
                              <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>平均里程</th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredData.storeStats.map((store, idx) => (
                              <tr key={idx} style={{ background: idx % 2 === 0 ? '#fff' : '#f7fbff' }}>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10 }}>{store.store}</td>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'center' }}>{store.count}</td>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>{store.avgPrice > 0 ? `NT${store.avgPrice.toLocaleString()}` : '-'}</td>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>{store.minPrice > 0 ? `NT${store.minPrice.toLocaleString()}` : '-'}</td>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>{store.maxPrice > 0 ? `NT${store.maxPrice.toLocaleString()}` : '-'}</td>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>{store.avgMileage > 0 ? `${store.avgMileage.toLocaleString()} km` : '-'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  <div style={{ marginBottom: 18 }}>
                    <div style={{ fontSize: 16, fontWeight: 'bold', marginBottom: 10 }}>篩選後數據表格（只顯示主要欄位）</div>
                    <div style={{ overflowX: 'auto', border: '1px solid #ccc', borderRadius: 6, boxShadow: '0 2px 4px rgba(0,0,0,0.08)' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, backgroundColor: '#fff' }}>
                        <thead>
                          <tr style={{ background: '#4472C4', color: '#fff' }}>
                            <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'center', width: 40 }}>#</th>
                            <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'left' }}>販售位置</th>
                            <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>價格</th>
                            <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>里程</th>
                            <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'center' }}>年份</th>
                            <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'center' }}>排氣量</th>
                            <th style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'left' }}>連結</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(() => {
                            const titleIndex = filteredData.headers.indexOf('title')
                            const storeIndex = filteredData.headers.indexOf('store')
                            const priceIndex = filteredData.headers.indexOf('price')
                            const mileageIndex = filteredData.headers.indexOf('mileage')
                            const yearIndex = filteredData.headers.indexOf('year')
                            const ccIndex = filteredData.headers.indexOf('cc')
                            const urlIndex = filteredData.headers.indexOf('url')
                            return filteredData.rows.slice(0, 50).map((row, rowIndex) => (
                              <tr key={rowIndex} style={{ background: rowIndex % 2 === 0 ? '#fff' : '#f0f2f5', borderBottom: '1px solid #e0e0e0' }}>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'center' }}>{rowIndex + 1}</td>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10 }}>{storeIndex >= 0 ? row[storeIndex] : '-'}</td>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>{priceIndex >= 0 && row[priceIndex] ? `NT${Number(row[priceIndex]).toLocaleString()}` : '-'}</td>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'right' }}>{mileageIndex >= 0 && row[mileageIndex] ? `${Number(row[mileageIndex]).toLocaleString()} km` : '-'}</td>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'center' }}>{yearIndex >= 0 ? row[yearIndex] : '-'}</td>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'center' }}>{ccIndex >= 0 ? row[ccIndex] : '-'}</td>
                                <td style={{ border: '1px solid #d0d0d0', padding: 10, textAlign: 'left', maxWidth: 230, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                  {urlIndex >= 0 && row[urlIndex] ? <a href={row[urlIndex]} target="_blank" rel="noreferrer" style={{ color: '#0d47a1' }}>前往連結</a> : '-'}
                                </td>
                              </tr>
                            ))
                          })()}
                        </tbody>
                      </table>
                    </div>
                    {filteredData.rows.length > 50 && <div style={{ padding: 12, background: '#f9f9f9', borderTop: '1px solid #ccc', textAlign: 'center', color: '#666', fontSize: 12 }}>...還有 {filteredData.rows.length - 50} 筆資料，請下載完整 Excel 或 CSV 查看全部內容</div>}
                  </div>
                </>
              )}
            </div>
          )}

          {result.html && (
            <div style={{ marginBottom: 24 }}>
              <button onClick={() => download(result.html_filename || 'report.html', result.html, 'text/html')} style={{ padding: '8px 12px', background: '#111', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>下載 HTML 報表</button>
            </div>
          )}

          {result.png && (
            <div style={{ marginBottom: 24 }}>
              <h3>分析圖表</h3>
              <img src={`data:image/png;base64,${result.png}`} alt="Analysis" style={{ maxWidth: '100%', borderRadius: 10, border: '1px solid #ddd' }} />
            </div>
          )}
        </div>
      )}

      <section style={{ marginTop: 32, padding: 18, border: '1px solid #e0e0e0', borderRadius: 10, background: '#f9fafb' }}>
        <h2>本網站做什麼</h2>
        <p>此網站整合了原始的二手機車爬蟲與分析程式：透過服務端 Python API 抓取 2Motor 車款資料，解析價格、里程、年份與排氣量，並產生報表與圖表。</p>
      </section>
    </div>
  )
}
