import { useState } from 'react'

export default function Home() {
  const [keywords, setKeywords] = useState('')
  const [maxPages, setMaxPages] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  async function submit(event) {
    event.preventDefault()
    setLoading(true)
    setResult(null)

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

  return (
    <div style={{ maxWidth: 920, margin: '40px auto', fontFamily: 'Arial, sans-serif', lineHeight: 1.6 }}>
      <h1>2Motor 二手機車 Serverless Web UI</h1>
      <p>這個網站將原本的二手機車爬蟲與分析程式包裝為一個可直接部署到 Vercel 的 Serverless 應用。</p>
      <p>輸入搜尋關鍵字與最大頁數後，網站會呼叫 serverless Python API，抓取 2Motor 二手機車資料並產出報表。</p>

      <section style={{ padding: 18, border: '1px solid #e0e0e0', borderRadius: 10, background: '#f9fafb', marginTop: 24 }}>
        <h2>操作說明</h2>
        <ol>
          <li>輸入「關鍵字」來篩選車款，例如「125」、「Gogoro」、「SYM」。</li>
          <li>設定要抓取的最大頁數，數字越大可能抓到更多資料。</li>
          <li>按下「開始抓取並分析」，等待結果顯示於下方。</li>
          <li>若成功，您可以直接下載 CSV 與 HTML 報表，並檢視生成的分析圖。</li>
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
            <div style={{ marginBottom: 16 }}>
              <strong>日誌：</strong>
              <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 240, overflow: 'auto', background: '#f4f4f4', padding: 12, borderRadius: 6 }}>{result.logs.join('\n')}</pre>
            </div>
          )}
          {result.rows !== undefined && <div>抓取資料筆數：{result.rows}</div>}

          <div style={{ marginTop: 16, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {result.csv && (
              <button onClick={() => download(result.csv_filename || 'listings.csv', result.csv, 'text/csv')} style={{ padding: '10px 16px', background: '#111', color: '#fff', border: 'none', borderRadius: 6 }}>下載 CSV</button>
            )}
            {result.html && (
              <button onClick={() => download(result.html_filename || 'report.html', result.html, 'text/html')} style={{ padding: '10px 16px', background: '#111', color: '#fff', border: 'none', borderRadius: 6 }}>下載 HTML</button>
            )}
          </div>

          {result.png && (
            <div style={{ marginTop: 22 }}>
              <div style={{ marginBottom: 8 }}>分析圖：</div>
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
