import { useState } from 'react'

export default function Home() {
  const [keywords, setKeywords] = useState('')
  const [maxPages, setMaxPages] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const backend = process.env.NEXT_PUBLIC_BACKEND_URL || ''

  async function submit(e) {
    e.preventDefault()
    if (!backend) {
      alert('Configure NEXT_PUBLIC_BACKEND_URL environment variable to point to the Python backend')
      return
    }
    setLoading(true)
    setResult(null)
    try {
      const resp = await fetch(`${backend.replace(/\/+$/, '')}/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keywords, max_pages: Number(maxPages) })
      })
      const data = await resp.json()
      setResult(data)
    } catch (err) {
      setResult({ error: String(err) })
    } finally {
      setLoading(false)
    }
  }

  function download(filename, content, mime='text/plain') {
    const blob = new Blob([content], { type: mime })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{maxWidth:900,margin:'40px auto',fontFamily:'Arial, sans-serif'}}>
      <h1>2Motor Scraper (Web)</h1>
      <form onSubmit={submit} style={{display:'grid',gap:12}}>
        <label>
          關鍵字: <input value={keywords} onChange={e=>setKeywords(e.target.value)} style={{width:'60%'}} />
        </label>
        <label>
          最大頁數: <input type="number" value={maxPages} onChange={e=>setMaxPages(e.target.value)} style={{width:80}} />
        </label>
        <div>
          <button type="submit" disabled={loading}>{loading? '執行中…':'開始抓取並分析'}</button>
        </div>
      </form>

      {result && (
        <div style={{marginTop:24}}>
          <h2>結果</h2>
          {result.error && <pre style={{color:'red'}}>{result.error}</pre>}
          {result.rows !== undefined && <div>抓取筆數: {result.rows}</div>}

          {result.csv && (
            <div style={{marginTop:12}}>
              <button onClick={()=>download(result.csv_filename || 'listings.csv', result.csv, 'text/csv')}>下載 CSV</button>
            </div>
          )}

          {result.html && (
            <div style={{marginTop:12}}>
              <button onClick={()=>download(result.html_filename || 'report.html', result.html, 'text/html')}>下載 HTML 報表</button>
            </div>
          )}

          {result.png && (
            <div style={{marginTop:12}}>
              <img src={`data:image/png;base64,${result.png}`} alt="分析圖" style={{maxWidth:'100%'}} />
              <div><button onClick={()=>{ const b=atob(result.png); const u8=new Uint8Array(Array.from(b).map(c=>c.charCodeAt(0))); const blob=new Blob([u8],{type:'image/png'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='analysis.png'; a.click(); URL.revokeObjectURL(url);}}>下載 PNG</button></div>
            </div>
          )}

        </div>
      )}

      <footer style={{marginTop:40,fontSize:12,color:'#666'}}>
        部署說明：將此目錄部署到 Vercel，並在環境變數 `NEXT_PUBLIC_BACKEND_URL` 設定後端 URL。
      </footer>
    </div>
  )
}
