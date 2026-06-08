# 2Motor 二手機車抓取與分析專案 | 2Motor Second-Hand Motorcycle Scraper & Analytics

[繁體中文說明](#traditional-chinese) | [English Description](#english)

---

<a name="traditional-chinese"></a>
## 🇹🇼 繁體中文說明

### 專案概覽
本專案為針對 `2Motor 貳輪嶼` 二手機車網站（[https://shop.2motor.tw/](https://shop.2motor.tw/)）所開發的資料抓取與分析工具。
它集成了 **Playwright/BeautifulSoup4 網頁爬蟲**、**Pandas 資料洗淨與分析**、以及 **Matplotlib 統計視覺化**，並提供 **本地桌面 GUI (Tkinter)** 與 **Vercel Serverless 雲端網頁版 (Next.js + Python API)** 雙重執行模式。

本系統能自動將不同店家/分店銷售的「相同機車車款」進行合併歸類，產出包含統計分析的 Excel 試算表、深色主題互動式 HTML 網頁報表與分佈圖表，幫助使用者快速掌握全台二手機車市場的行情與里程車況。

### 主要功能
1. **多管道資料抓取 (Scraping)**：自動發送 HTTP 請求並解析網頁結構，提取機車標題、價格、里程數、出廠年份、排氣量 (cc) 以及來源店家等屬性。
2. **跨店車款分類與歸一化**：透過正則表達式自動辨識車款型號與廠牌，並將分散在不同分店（例如：新北店、台中店）的同一款車歸類為相同車型，進行跨店售價與里程比較。
3. **多格式報表導出 (Reporting)**：
   * **Excel 試算表**：包含 `車款彙整分析`（跨店統計平均價、最值、里程）與 `所有車輛清單`（原始細節與 URL）雙工作表。
   * **HTML 互動報表**：採用現代深色主題（Dark Mode）與分頁設計，方便直接在瀏覽器中查閱與排序。
   * **Matplotlib 統計圖表**：產出包含價格分佈直方圖、里程分佈直方圖、出廠年份分佈、里程與價格散佈圖、年份與價格散佈圖及商家熱度排行等 6 合 1 分析圖。
4. **雙介面執行模式**：
   * **本地桌面版 (Tkinter GUI)**：適合本地快速執行、即時觀察背景執行日誌，並可一鍵開啟產出的 HTML 報表。
   * **Vercel 雲端 Web 版 (Next.js + Flask API)**：可直接部署於 Vercel，提供極簡現代的響應式深色 Dashboard。

---

### 目錄結構
* `api/`：Vercel Serverless 雲端 API 路由。
  * `scrape.py` - Flask 服務端，執行爬蟲管線並以 Base64 編碼回傳 Excel, HTML 及 PNG。
* `src/`：核心 Python 原始碼。
  * `config.py` - 網站路徑、輸出檔案名稱、預設參數等全域變數設定。
  * `utils.py` - 數值與型態轉換之安全處理函數。
  * `scraper.py` - 商品卡片解析與正則表達式欄位提取器。
  * `analyzer.py` - Pandas 洗淨去重、Excel/HTML 報表與 Matplotlib 圖表生成邏輯。
  * `pipeline.py` - 整合爬蟲與分析的同步執行管線，供本地 GUI 調用。
  * `gui.py` - Tkinter 視窗界面與執行日誌輸出。
* `pages/`：Next.js 前端網頁。
  * `index.js` - Dashboard 網頁端介面（現代深色玻璃擬物風格）。
* `tests/`：各模組單元測試（包含 Scraper, Analyzer 等）。
* `outputs/`：本地執行產生的結果資料夾（CSV, XLSX, HTML, PNG）。
* `run_2wheel.py` - 本地桌面程式啟動點。
* `vercel.json` - Vercel Serverless 的構建與路由配置。
* `requirements.txt` - Python 依賴套件清單。
* `package.json` - Next.js 前端專案配置。

---

### 執行與部署說明

#### 1. 本地執行桌面 GUI
1. 確保已安裝 Python 3 及相依套件：
   ```powershell
   python -m pip install -r requirements.txt
   ```
2. 啟動桌面應用程式：
   ```powershell
   python run_2wheel.py
   ```
3. 在視窗中設定篩選條件，點擊「開始抓取」即可於 `outputs/` 目錄取得分析結果。

#### 2. 本地開發 Next.js 網頁版
1. 安裝 Node 套件：
   ```bash
   npm install
   ```
2. 啟動開發伺服器：
   ```bash
   npm run dev
   ```
3. 開啟瀏覽器訪問 `http://localhost:3000`。

#### 3. 部署到 Vercel
直接將本專案連接至 Vercel 帳號，Vercel 會自動讀取 `vercel.json` 並執行 Next.js 前端編譯與部署 `api/scrape.py` 作為 Python Serverless Functions。

#### 4. 執行單元測試
在專案根目錄下執行：
```powershell
python -m unittest discover -s tests
```

---

<a name="english"></a>
## 🇺🇸 English Description

### Project Overview
This project is an advanced data scraping and analysis toolkit developed for the `2Motor` secondhand motorcycle website ([https://shop.2motor.tw/](https://shop.2motor.tw/)). 
It integrates a **BeautifulSoup4 web scraper**, **Pandas data processing**, and **Matplotlib statistical visualization** in a dual-mode application featuring a **Local Desktop GUI (Tkinter)** and a **Vercel Serverless Web UI (Next.js + Python API)**.

The system automatically categorizes and groups identical motorcycle models across different store branches (e.g., Taipei, Taichung). It evaluates local market prices, mileages, and age ranges, exporting them into formatted Excel workbooks, dynamic dark-mode HTML reports, and analytical charts.

### Key Features
1. **Robust Scraper**: Retrieves motorcycle listings, extracting title, brand, model, price, mileage, manufacturing year, displacement (cc), and selling store.
2. **Model Aggregation & normalization**: Processes product titles using regular expressions. Items from different branches are clustered under unified model groups to allow cross-store pricing and mileage analysis.
3. **Multi-Format Export**:
   * **Excel Spreadsheet**: Includes two worksheets: `車款彙整分析` (Model Summary Analysis with aggregations) and `所有車輛清單` (detailed breakdown of all listings with URLs).
   * **Interactive HTML Report**: Features a responsive dark-themed dashboard layout with tabs for quick switching between model analysis and raw data.
   * **Matplotlib Visualizations**: Produces a 6-in-1 graphical chart showcasing price distributions, mileage spreads, manufacturing year histograms, scatter plots (price vs. mileage/year), and top branches.
4. **Dual Interface**:
   * **Desktop Mode (Tkinter GUI)**: Simplifies local operations, piping execution logs in real-time, and letting users open generated HTML files in one click.
   * **Cloud Web Mode (Next.js)**: Optimized for seamless Vercel deployment, featuring a modern glassmorphism UI dashboard.

---

### Directory Architecture
* `api/`: Vercel Serverless python backend functions.
  * `scrape.py` - Handles POST requests, runs pipelines, and returns base64-encoded reports.
* `src/`: Python core implementation scripts.
  * `config.py` - Path configs, parameters, and global settings.
  * `utils.py` - Safe integer and float conversion helper methods.
  * `scraper.py` - Web request dispatching and tag parser.
  * `analyzer.py` - Pandas processing, excel formatting, HTML templating, and matplotlib charting.
  * `pipeline.py` - Orchestrates scraping and analysis processes for local execution.
  * `gui.py` - Tkinter GUI controls and background thread logger.
* `pages/`: Next.js UI component pages.
  * `index.js` - Responsive premium dashboard UI.
* `tests/`: Unit test suite for verifying scraper, utility, and analyzer methods.
* `outputs/`: Local generation output folder (CSV, Excel, HTML, PNG).
* `run_2wheel.py` - Desktop application launch script.
* `vercel.json` - Vercel builds and backend route configurations.
* `requirements.txt` - Python module dependencies.
* `package.json` - Node module configurations for the Next.js frontend.

---

### Execution & Deployment

#### 1. Local Desktop GUI
1. Install Python 3 requirements:
   ```powershell
   python -m pip install -r requirements.txt
   ```
2. Start the Tkinter application:
   ```powershell
   python run_2wheel.py
   ```
3. Set your search query, choose limits, click "Start Scrape", and check outputs in `outputs/`.

#### 2. Local Next.js Web Dev
1. Install node dependencies:
   ```bash
   npm install
   ```
2. Launch dev server:
   ```bash
   npm run dev
   ```
3. Open `http://localhost:3000` in your browser.

#### 3. Vercel Cloud Deployment
Push the project repository to GitHub and link it to your Vercel account. Vercel automatically detects the `vercel.json` schema, hosting the Next.js frontend and deploying `api/scrape.py` as an serverless Python environment.

#### 4. Run Unit Tests
To verify implementation logic, run:
```powershell
python -m unittest discover -s tests
```
