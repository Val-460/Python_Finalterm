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
      setResult({ error: String(error) })
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
    <div style={{ maxWidth: 920, margin: '40px auto', fontFamily: 'Arial, sans-serif' }}>
      <h1>2Motor 二手機車 Serverless</h1>
      <p>在 Vercel 上直接執行，無需外部伺服器主機。</p>

      <form onSubmit={submit} style={{ display: 'grid', gap: 14, marginTop: 24 }}>
        <label>
          關鍵字：
          <input
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            style={{ width: '60%', marginLeft: 8 }}
          />
        </label>

        <label>
          最大頁數：
          <input
            type="number"
            value={maxPages}
            min={1}
            onChange={(e) => setMaxPages(e.target.value)}
            style={{ width: 96, marginLeft: 8 }}
          />
        </label>

        <button type="submit" disabled={loading} style={{ width: 180, padding: '10px 16px' }}>
          {loading ? '執行中...' : '開始抓取並分析'}
        </button>
      </form>

      {result && (
        <div style={{ marginTop: 30, padding: 18, border: '1px solid #ddd', borderRadius: 10, background: '#fafafa' }}>
          <h2>執行結果</h2>
          {result.error && <pre style={{ color: 'red' }}>{result.error}</pre>}
          {result.logs && (
            <div style={{ marginBottom: 16 }}>
              <strong>日誌：</strong>
              <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 220, overflow: 'auto', background: '#fff', padding: 10, border: '1px solid #eee' }}>
                {result.logs.join('\n')}
              </pre>
            </div>
          )}
          {result.rows !== undefined && <div>抓取筆數：{result.rows}</div>}

          {result.csv && (
            <button onClick={() => download(result.csv_filename || 'listings.csv', result.csv, 'text/csv')} style={{ marginTop: 14 }}>
              下載 CSV
            </button>
          )}

          {result.html && (
            <button onClick={() => download(result.html_filename || 'report.html', result.html, 'text/html')} style={{ marginTop: 14, marginLeft: 12 }}>
              下載 HTML
            </button>
          )}

          {result.png && (
            <div style={{ marginTop: 18 }}>
              <div>分析圖：</div>
              <img src={`data:image/png;base64,${result.png}`} alt="Analysis" style={{ maxWidth: '100%' }} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
