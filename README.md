# 貳輪部品電商市場大數據分析平台 🏍️📊

本專案是一個大學程式設計期末專案，以**前後端分離**、**多執行緒異步架構**打造的「貳輪部品電商市場大數據分析平台」。本平台專門爬取目標電商網站（貳輪部品 [shop.2motor.tw](https://shop.2motor.tw/collections/all)），將商品價格、折數與圖片等數據進行清洗、分析與視覺化，並提供雲端託管與單機 GUI 面板。

---

## 🛠️ 技術棧說明

- **數據抓取層**：Python + **Playwright** 進行非同步網頁渲染爬取（前 3 頁商品）。
- **數據分析與可視化**：**Pandas** 資料清洗與折扣運算，**Matplotlib** 繪製「價格直方圖」、「折扣幅度散佈圖」與「熱門品牌 Top 5 佔比圓餅圖」。
- **資料庫層**：**SQLAlchemy ORM**。相容 SQLite（本機開發，支援多執行緒相容）與 PostgreSQL（Render 雲端資料庫，支援自動補齊 psycopg2 驅動）。
- **後端 API (Backend)**：**FastAPI** 框架，提供 Swagger UI 自動化測試頁面，並託管靜態圖表。
- **前端 UI (Frontend)**：**Python Tkinter** 桌面應用程式，僅負責聯網對接 FastAPI 後端，無任何本機資料庫與爬網邏輯。

---

## 📂 專案目錄結構 (已優化整合，總數低於 10 個檔案)

```text
motor_data_analysis/
├── backend/                        # 後端 API 與數據處理服務 (極簡單檔案)
│   ├── server.py                   # 整合了設定、資料庫模型、爬蟲、Pandas 分析、Matplotlib 繪圖與 FastAPI
│   └── static/charts/              # 存放生成的分析圖表 (.png)
│
├── frontend/                       # 前端 Tkinter 桌面控制面板 (極簡單檔案)
│   └── app.py                      # 整合了 Tkinter 介面、HTTP requests 通訊與 Pillow 圖片縮放
│
├── .gitignore                      # Git 忽略清單
├── requirements.txt                # 全域統一 Python 套件依賴清單
├── run_backend.bat                 # 後端雙擊啟動檔 (Windows CRLF 格式)
├── run_frontend.bat                # 前端雙擊啟動檔 (Windows CRLF 格式)
└── README.md                       # 本說明文件
```

---

## 🚀 快速啟動指南

### 1. 後端 (FastAPI) 本地啟動與設定

#### 方式 A：雙擊批次檔直接啟動 (推薦給 Windows 使用者)
- 本專案根目錄下已建置 **`run_backend.bat`**。
- 您只需**雙擊 `run_backend.bat`**，此批次檔會自動幫您進行設定並啟動後端，完全免打指令。

#### 方式 B：開發者手動執行
在終端機切換至 `backend` 目錄下執行以下指令：
```bash
# 1. 切換至 backend 資料夾
cd backend

# 2. 建立並啟動虛擬環境 (可選)
python -m venv venv
.\venv\Scripts\activate

# 3. 安裝依賴套件 (全域統一清單在根目錄)
pip install -r ../requirements.txt

# 4. 安裝 Playwright 所需的 Chromium 瀏覽器核心 (首次執行時需要)
python -m playwright install chromium

# 5. 啟動 FastAPI 服務
python server.py
```
- 啟動成功後，後端預設執行於 `http://127.0.0.1:8000`。
- 開啟瀏覽器輸入 `http://127.0.0.1:8000/docs` 可開啟 Swagger UI 測試 API。

---

### 2. 前端 (Tkinter) 啟動與打包

#### 方式 A：雙擊批次檔直接啟動 (推薦給測試者與非組員同學)
- 本專案根目錄下已建置 **`run_frontend.bat`**。
- 同學或教授在已安裝 Python 的 Windows 電腦上，**直接雙擊 `run_frontend.bat`** 即可自動安裝所需套件並開啟 Tkinter 介面，完全不需開啟終端機。

#### 方式 B：開發者手動執行
在終端機進入 `frontend` 目錄下執行以下指令：
```bash
# 1. 切換至 frontend 資料夾
cd frontend

# 2. 建立並啟動虛擬環境 (可選)
python -m venv venv
.\venv\Scripts\activate

# 3. 安裝前端依賴套件 (全域統一清單在根目錄)
pip install -r ../requirements.txt

# 4. 啟動 Tkinter 單機面板
python app.py
```

#### 方式 C：打包為獨立 `.exe` 執行檔 (PyInstaller)
若想要發布完全獨立且不需安裝 Python 環境的單一執行檔，請在安裝 `pyinstaller` 後於 `frontend` 目錄下執行：
```bash
# 安裝打包工具
pip install pyinstaller

# 進行打包 (打包為單一檔案、不顯示終端機黑視窗)
pyinstaller --noconsole --onefile app.py
```
打包完成後，可在 `frontend/dist/app.exe` 取得獨立執行檔。

---

## ☁️ 雲端部署建議 (Render.com)

1. **資料庫建立**：
   - 在 Render 上建立一個 **PostgreSQL** 資料庫服務。
   - 複製它的 **External Database URL**。
2. **後端 Web Service 部署**：
   - 新增一個 Web Service，並將 Repository 連結至您的 Git 專案。
   - 選擇環境為 `Python`。
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r ../requirements.txt && playwright install chromium`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables (環境變數)**:
     - 新增一個環境變數 `DATABASE_URL`，值為剛才複製的 PostgreSQL Database URL。
     - *註：本專案已在 `server.py` 中寫好防呆邏輯，會自動將 `postgres://` 轉為 `postgresql+psycopg2://`，請放心貼上。*
