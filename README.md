# 2Motor 二手機車抓取與分析專案

## 專案概覽
本專案為 `2Motor` 二手機車網站資料抓取與分析工具，採用 Playwright 爬蟲 + Pandas 分析 + Tkinter GUI。這是一個已模組化、可測試、可生成報表的專案。

## 目錄結構

- `src/`
  - `config.py` - 應用程式設定、輸出路徑與常數管理
  - `utils.py` - 資料清理與數值轉換輔助函式
  - `scraper.py` - Playwright 網頁爬蟲與資料擷取邏輯
  - `analyzer.py` - Pandas 清理、去重、Excel/HTML 報表與圖表輸出
  - `pipeline.py` - 背景執行管線整合與日誌通知
  - `gui.py` - Tkinter 使用者介面與程式啟動入口
- `tests/` - 單元測試
- `outputs/` - 產生的結果檔案：CSV、圖表 PNG、HTML、Excel
- `archive/` - 保留的舊版/備份程式碼
- `debug/` - 供程式執行時寫入的偵錯輸出（目前為空）
- `run_2wheel.py` - 專案啟動腳本
- `.gitignore` - 忽略項目設定

## 清理後狀態

- 已移除舊執行日誌與過期產物：`run_log.txt`、`run_new_log.txt`、`report.html`
- 已移除非正式測試與偵錯輔助檔案：`test_gui_minimal.py`
- 已移除舊版偵錯輔助腳本目錄 `scripts/`
- 已移除過期 debug JSON 檔案
- 已刪除 Python bytecode 快取資料夾 `__pycache__/`

## 執行方式

1. 啟動虛擬環境（若有）：
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
2. 執行專案：
   ```powershell
   .\.venv\Scripts\python.exe run_2wheel.py
   ```

## 測試

執行全部單元測試：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## 注意事項

- 若要重新啟用偵錯輸出，`src/scraper.py` 會自動寫入 `debug/html_pages/` 和 `debug/link_logs/`。
- `outputs/` 保留為本專案正常執行的結果檔案資料夾。

## Vercel 無伺服器部署

此專案已新增根目錄 Next.js 前端以及 Python API，可直接部署到 Vercel，無需外部伺服器主機。
- `package.json` 和 `pages/index.js` 用於網站前端。
- `api/scrape.py` 是 Vercel Python serverless 函式，會呼叫 `src/scraper.py` 和 `src/analyzer.py`。
- `requirements.txt` 列出 Python 相依套件。
- `vercel.json` 定義 Vercel 建構器：Next.js 前端與 Python API。

本地測試：

```powershell
python -m pip install -r requirements.txt
npm install
npm run dev
```

部署到 Vercel：
1. 將整個專案資料夾連至 Vercel。
2. Vercel 自動偵測 `package.json` 與 `vercel.json`。
3. 上傳並部署。
