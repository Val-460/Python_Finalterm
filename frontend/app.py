import tkinter as tk
from tkinter import ttk, messagebox
import threading
import io
import os
import re
import datetime
import requests
from typing import List, Dict, Any, Optional
from PIL import Image, ImageTk

# =====================================================================
# 1. 聯網 API 客戶端 (API CLIENT)
# =====================================================================
class APIClient:
    """與後端 FastAPI 進行 HTTP 溝通的客戶端"""
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    def set_base_url(self, new_url: str):
        self.base_url = new_url.rstrip("/")

    def ping(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def trigger_crawl(self) -> Dict[str, Any]:
        response = requests.post(f"{self.base_url}/api/v1/crawl", timeout=180)
        if response.status_code != 200:
            raise Exception(response.json().get("detail", "爬蟲執行失敗"))
        return response.json()

    def get_products(self) -> List[Dict[str, Any]]:
        response = requests.get(f"{self.base_url}/api/v1/products", timeout=10)
        if response.status_code != 200:
            raise Exception("撈取商品清單失敗")
        return response.json()

    def get_analysis(self) -> Dict[str, Any]:
        response = requests.get(f"{self.base_url}/api/v1/analysis", timeout=10)
        if response.status_code != 200:
            raise Exception(response.json().get("detail", "撈取分析統計失敗，請確認是否已爬網"))
        return response.json()

    def get_charts(self) -> Dict[str, str]:
        response = requests.post(f"{self.base_url}/api/v1/analysis/charts", timeout=10)
        if response.status_code != 200:
            raise Exception(response.json().get("detail", "取得圖表資訊失敗"))
        data = response.json()
        return {
            "histogram_url": f"{self.base_url}{data['histogram_url']}" if data.get('histogram_url') else "",
            "scatter_url": f"{self.base_url}{data['scatter_url']}" if data.get('scatter_url') else "",
            "brand_pie_url": f"{self.base_url}{data['brand_pie_url']}" if data.get('brand_pie_url') else ""
        }

    def download_chart_image(self, full_url: str) -> bytes:
        if not full_url:
            return b""
        response = requests.get(full_url, timeout=10)
        if response.status_code != 200:
            raise Exception("下載圖表影像失敗")
        return response.content

    def get_crawl_status(self) -> Dict[str, Any]:
        response = requests.get(f"{self.base_url}/api/v1/crawl/status", timeout=5)
        if response.status_code != 200:
            raise Exception("取得爬蟲狀態失敗")
        return response.json()

    def download_excel_report(self) -> bytes:
        response = requests.get(f"{self.base_url}/api/v1/report/excel", timeout=30)
        if response.status_code != 200:
            raise Exception("Excel 報表未生成，請先執行爬蟲載入數據。")
        return response.content

# =====================================================================
# 2. 圖片轉換與門市資料 (CONSTANTS & IMAGE UTILS)
# =====================================================================
def convert_bytes_to_tk_image(img_bytes: bytes, target_width: int = 480, target_height: int = 320) -> Optional[ImageTk.PhotoImage]:
    """將二進位影像流轉換為 Pillow Tkinter PhotoImage 並等比縮放"""
    if not img_bytes:
        return None
    try:
        image = Image.open(io.BytesIO(img_bytes))
        image_resized = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image_resized)
    except Exception:
        return None

BRANCHES = [
    {"name": "新北中和店", "address": "新北市中和區景平路 159 號", "phone": "02-2242-2321", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_zhonghe"},
    {"name": "新北樹林店", "address": "新北市樹林區中正路 410 號", "phone": "02-2688-5522", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_shulin"},
    {"name": "台北大同店", "address": "台北市大同區延平北路三段 100 號", "phone": "02-2599-1122", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_datong"},
    {"name": "新北板橋店", "address": "新北市板橋區文化路二段 320 號", "phone": "02-2250-9988", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_banqiao"},
    {"name": "新北三重店", "address": "新北市三重區重新路四段 80 號", "phone": "02-2970-7766", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_sanchong"},
    {"name": "桃園中壢店", "address": "桃園市中壢區延平路 200 號", "phone": "03-425-3344", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_zhongli"},
    {"name": "新竹中華店", "address": "新竹市東區中華路二段 500 號", "phone": "03-522-8877", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_hsinchu"},
    {"name": "台中崇德店", "address": "台中市北屯區崇德路二段 300 號", "phone": "04-2244-5566", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_chongde"},
    {"name": "台中一中店", "address": "台中市北區三民路三段 250 號", "phone": "04-2225-8899", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_yizhong"},
    {"name": "彰化金馬店", "address": "彰化市金馬路二段 600 號", "phone": "04-722-3344", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_changhua"},
    {"name": "台南公園店", "address": "台南市北區公園路 800 號", "phone": "06-251-2233", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_tainan"},
    {"name": "高雄三民店", "address": "高雄市三民區九如一路 400 號", "phone": "07-380-5566", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_kaohsiung"},
    {"name": "高雄鳳山店", "address": "高雄市鳳山區光遠路 100 號", "phone": "07-740-8899", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_fengshan"},
    {"name": "宜蘭羅東店", "address": "宜蘭縣羅東鎮純精路二段 150 號", "phone": "03-955-6677", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_luodong"},
    {"name": "花蓮中山店", "address": "花蓮縣花蓮市中山路 700 號", "phone": "03-833-2211", "hours": "10:00 - 21:00", "line": "https://line.me/ti/p/2motor_hualien"}
]

def clean_loc_name(name: str) -> str:
    """移去門市名稱中的縣市與店字，方便模糊匹配"""
    if not name:
        return ""
    for city in ["新北", "台北", "桃園", "新竹", "台中", "彰化", "台南", "高雄", "宜蘭", "花蓮"]:
        name = name.replace(city, "")
    return name.replace("店", "").strip()

# =====================================================================
# 3. Tkinter 視窗主應用程式 (UI APP)
# =====================================================================
class MotorAnalysisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("二手機車 CP 值智能選購與全台尋車導航系統 - 單機控制面板")
        self.root.geometry("1200x800")
        self.root.minsize(1050, 700)
        
        self.client = APIClient("http://127.0.0.1:8000")
        
        # 暫存資料
        self.all_products = []
        self.hist_image = None
        self.scatter_image = None
        self.brand_pie_image = None
        
        # Sleek Dark Mode 配色
        self.bg_color = "#121214"
        self.panel_color = "#1e1e24"
        self.accent_color = "#00adb5"
        self.text_color = "#eeeeee"
        self.sec_text_color = "#b2bec3"
        self.btn_bg = "#3f51b5"
        self.btn_active = "#5c6bc0"
        
        self.root.configure(bg=self.bg_color)
        self.setup_styles()
        self.build_ui()
        self.check_backend_connection()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background=self.bg_color, foreground=self.text_color)
        self.style.configure('TNotebook', background=self.bg_color, borderwidth=0)
        self.style.configure('TNotebook.Tab', background=self.panel_color, foreground=self.sec_text_color, padding=[15, 6], font=('Microsoft JhengHei', 10, 'bold'))
        self.style.map('TNotebook.Tab', background=[('selected', self.accent_color)], foreground=[('selected', '#ffffff')])
        self.style.configure('TFrame', background=self.bg_color)
        self.style.configure('Card.TFrame', background=self.panel_color, relief='flat')
        self.style.configure('TLabel', background=self.bg_color, foreground=self.text_color, font=('Microsoft JhengHei', 10))
        self.style.configure('Header.TLabel', background=self.bg_color, foreground=self.accent_color, font=('Microsoft JhengHei', 16, 'bold'))
        self.style.configure('CardTitle.TLabel', background=self.panel_color, foreground=self.sec_text_color, font=('Microsoft JhengHei', 11))
        self.style.configure('CardVal.TLabel', background=self.panel_color, foreground=self.text_color, font=('Consolas', 18, 'bold'))
        self.style.configure('Status.TLabel', background=self.bg_color, foreground="#e74c3c", font=('Microsoft JhengHei', 9, 'italic'))
        self.style.configure('Treeview', background=self.panel_color, fieldbackground=self.panel_color, foreground=self.text_color, rowheight=26, font=('Microsoft JhengHei', 9))
        self.style.configure('Treeview.Heading', background="#2d2d38", foreground=self.text_color, relief='flat', font=('Microsoft JhengHei', 10, 'bold'))
        self.style.map('Treeview', background=[('selected', self.accent_color)])
        self.style.configure('Vertical.TScrollbar', gripcount=0, background=self.panel_color, troughcolor=self.bg_color, borderwidth=0)

    def build_ui(self):
        top_frame = tk.Frame(self.root, bg=self.bg_color, height=60)
        top_frame.pack(fill=tk.X, padx=20, pady=10)
        
        title_label = ttk.Label(top_frame, text="🏍️ 二手機車 CP 值智能選購與全台尋車導航系統", style="Header.TLabel")
        title_label.pack(side=tk.LEFT, pady=5)
        
        self.status_text = tk.StringVar(value="正在偵測後端服務...")
        self.status_label = ttk.Label(top_frame, textvariable=self.status_text, style="Status.TLabel")
        self.status_label.pack(side=tk.RIGHT, padx=10, pady=10)

        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg=self.bg_color, bd=0, sashwidth=4)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        sidebar = tk.Frame(main_paned, bg=self.panel_color, width=280)
        main_paned.add(sidebar)
        self.right_container = tk.Frame(main_paned, bg=self.bg_color)
        main_paned.add(self.right_container)
        
        # Sidebar Controls
        sb_title = tk.Label(sidebar, text="控制設定面板", bg=self.panel_color, fg=self.text_color, font=('Microsoft JhengHei', 12, 'bold'), pady=15)
        sb_title.pack(fill=tk.X)
        
        api_config_frame = tk.LabelFrame(sidebar, text=" API 伺服器設定 ", bg=self.panel_color, fg=self.accent_color, font=('Microsoft JhengHei', 9), padx=10, pady=10, bd=1, relief='solid')
        api_config_frame.pack(fill=tk.X, padx=15, pady=10)
        self.api_url_var = tk.StringVar(value="http://127.0.0.1:8000")
        api_entry = tk.Entry(api_config_frame, textvariable=self.api_url_var, bg=self.bg_color, fg=self.text_color, insertbackground=self.text_color, font=('Consolas', 10), bd=0)
        api_entry.pack(fill=tk.X, ipady=4, pady=5)
        conn_btn = tk.Button(api_config_frame, text="測試並儲存連線", bg=self.btn_bg, fg="#ffffff", activebackground=self.btn_active, activeforeground="#ffffff", font=('Microsoft JhengHei', 9, 'bold'), bd=0, command=self.check_backend_connection)
        conn_btn.pack(fill=tk.X, pady=5)

        action_frame = tk.LabelFrame(sidebar, text=" 決策數據操作 ", bg=self.panel_color, fg=self.accent_color, font=('Microsoft JhengHei', 9), padx=10, pady=10, bd=1, relief='solid')
        action_frame.pack(fill=tk.X, padx=15, pady=10)
        self.crawl_btn = tk.Button(action_frame, text="🚀 執行雲端大數據爬蟲", bg="#27ae60", fg="#ffffff", activebackground="#2ecc71", activeforeground="#ffffff", font=('Microsoft JhengHei', 10, 'bold'), bd=0, height=2, command=self.start_crawl_thread)
        self.crawl_btn.pack(fill=tk.X, pady=8)
        self.load_btn = tk.Button(action_frame, text="📊 載入與分析數據", bg="#e67e22", fg="#ffffff", activebackground="#f39c12", activeforeground="#ffffff", font=('Microsoft JhengHei', 10, 'bold'), bd=0, height=2, command=self.load_data_and_charts)
        self.load_btn.pack(fill=tk.X, pady=8)
        self.excel_btn = tk.Button(action_frame, text="📥 匯出 Excel 完整報表", bg="#2980b9", fg="#ffffff", activebackground="#3498db", activeforeground="#ffffff", font=('Microsoft JhengHei', 10, 'bold'), bd=0, height=2, command=self.export_excel_report)
        self.excel_btn.pack(fill=tk.X, pady=8)
        self.html_btn = tk.Button(action_frame, text="🌐 開啟 HTML 互動報表", bg="#8e44ad", fg="#ffffff", activebackground="#9b59b6", activeforeground="#ffffff", font=('Microsoft JhengHei', 10, 'bold'), bd=0, height=2, command=self.open_html_report)
        self.html_btn.pack(fill=tk.X, pady=8)

        # 進度條
        self.progress_bar = ttk.Progressbar(action_frame, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=8)
        self.progress_bar['value'] = 0

        self.progress_text = tk.StringVar(value="等待指令...")
        progress_lbl = tk.Label(sidebar, textvariable=self.progress_text, bg=self.panel_color, fg=self.sec_text_color, font=('Microsoft JhengHei', 9), justify=tk.LEFT, wraplength=230)
        progress_lbl.pack(fill=tk.X, padx=15, pady=20)
        
        # Tabs Container
        self.notebook = ttk.Notebook(self.right_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10)
        
        self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_search = ttk.Frame(self.notebook)
        self.tab_store = ttk.Frame(self.notebook)
        self.tab_charts = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_dashboard, text=" 數據看板與推薦 ")
        self.notebook.add(self.tab_search, text=" 全台車源篩選對比 ")
        self.notebook.add(self.tab_store, text=" 實體門市與預約看車 ")
        self.notebook.add(self.tab_charts, text=" 市場統計圖表 ")
        
        self.setup_dashboard_tab()
        self.setup_search_tab()
        self.setup_store_tab()
        self.setup_charts_tab()

    # =====================================================================
    # Tab 1: Dashboard (數據概覽與排行)
    # =====================================================================
    def setup_dashboard_tab(self):
        lbl_intro = ttk.Label(self.tab_dashboard, text="📌 二手機車決策分析數據面板", font=('Microsoft JhengHei', 13, 'bold'))
        lbl_intro.pack(anchor=tk.W, pady=15, padx=20)
        
        metrics_frame = ttk.Frame(self.tab_dashboard)
        metrics_frame.pack(fill=tk.X, padx=15)
        self.card_total = self.create_card(metrics_frame, "商品抓取總量", "0 輛", 0, 0)
        self.card_avg_orig = self.create_card(metrics_frame, "市場平均原價", "NT$ 0", 0, 1)
        self.card_avg_curr = self.create_card(metrics_frame, "市場平均里程", "0 公里", 1, 0)
        self.card_discount = self.create_card(metrics_frame, "超值車源佔比", "0.0%", 1, 1)
        
        lists_frame = ttk.Frame(self.tab_dashboard)
        lists_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Left Top 10 CP
        cp_frame = ttk.LabelFrame(lists_frame, text=" 🔥 全網性價比超值神車榜 Top 10 (越高越超值) ", padding=10)
        cp_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        cols = ("title", "year", "mileage", "price", "cp_index", "cp_label")
        self.tree_cp_top = ttk.Treeview(cp_frame, columns=cols, show="headings")
        self.tree_cp_top.heading("title", text="車款名稱")
        self.tree_cp_top.heading("year", text="年份")
        self.tree_cp_top.heading("mileage", text="里程 (km)")
        self.tree_cp_top.heading("price", text="價格 (NT$)")
        self.tree_cp_top.heading("cp_index", text="CP指數")
        self.tree_cp_top.heading("cp_label", text="性價比")
        
        self.tree_cp_top.column("title", width=160, anchor=tk.W)
        self.tree_cp_top.column("year", width=50, anchor=tk.CENTER)
        self.tree_cp_top.column("mileage", width=70, anchor=tk.E)
        self.tree_cp_top.column("price", width=85, anchor=tk.E)
        self.tree_cp_top.column("cp_index", width=65, anchor=tk.CENTER)
        self.tree_cp_top.column("cp_label", width=65, anchor=tk.CENTER)
        
        cp_scroll = ttk.Scrollbar(cp_frame, orient=tk.VERTICAL, command=self.tree_cp_top.yview)
        self.tree_cp_top.configure(yscrollcommand=cp_scroll.set)
        self.tree_cp_top.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cp_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_cp_top.bind("<Double-1>", lambda e: self.on_double_click_item(self.tree_cp_top))

        # Right Top 10 Low Mileage
        mile_frame = ttk.LabelFrame(lists_frame, text=" 🏍️ 低里程精選極新車榜 Top 10 (里程數最低) ", padding=10)
        mile_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        self.tree_mile_top = ttk.Treeview(mile_frame, columns=cols, show="headings")
        self.tree_mile_top.heading("title", text="車款名稱")
        self.tree_mile_top.heading("year", text="年份")
        self.tree_mile_top.heading("mileage", text="里程 (km)")
        self.tree_mile_top.heading("price", text="價格 (NT$)")
        self.tree_mile_top.heading("cp_index", text="CP指數")
        self.tree_mile_top.heading("cp_label", text="性價比")
        
        self.tree_mile_top.column("title", width=160, anchor=tk.W)
        self.tree_mile_top.column("year", width=50, anchor=tk.CENTER)
        self.tree_mile_top.column("mileage", width=70, anchor=tk.E)
        self.tree_mile_top.column("price", width=85, anchor=tk.E)
        self.tree_mile_top.column("cp_index", width=65, anchor=tk.CENTER)
        self.tree_mile_top.column("cp_label", width=65, anchor=tk.CENTER)
        
        mile_scroll = ttk.Scrollbar(mile_frame, orient=tk.VERTICAL, command=self.tree_mile_top.yview)
        self.tree_mile_top.configure(yscrollcommand=mile_scroll.set)
        self.tree_mile_top.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mile_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_mile_top.bind("<Double-1>", lambda e: self.on_double_click_item(self.tree_mile_top))

    def create_card(self, parent, title, init_val, row, col):
        card = ttk.Frame(parent, style='Card.TFrame', padding=12)
        card.grid(row=row, column=col, padx=8, pady=6, sticky='nsew')
        parent.grid_columnconfigure(col, weight=1)
        parent.grid_rowconfigure(row, weight=1)
        lbl_title = ttk.Label(card, text=title, style='CardTitle.TLabel')
        lbl_title.pack(anchor=tk.W, pady=1)
        val_var = tk.StringVar(value=init_val)
        lbl_val = ttk.Label(card, textvariable=val_var, style='CardVal.TLabel')
        lbl_val.pack(anchor=tk.W, pady=3)
        return val_var

    # =====================================================================
    # Tab 2: Search & Compare (進階篩選與多車對比)
    # =====================================================================
    def setup_search_tab(self):
        # Top filter panel
        filter_frame = ttk.LabelFrame(self.tab_search, text=" 進階組合篩選面板 ", padding=10)
        filter_frame.pack(fill=tk.X, padx=15, pady=10)
        
        # Grid weights
        for idx in range(6):
            filter_frame.grid_columnconfigure(idx, weight=1)

        # 品牌
        ttk.Label(filter_frame, text="廠牌品牌:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.filter_brand = ttk.Combobox(filter_frame, values=["全部"], state="readonly", width=12)
        self.filter_brand.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.filter_brand.set("全部")
        self.filter_brand.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        # 門市
        ttk.Label(filter_frame, text="實體分店:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.filter_location = ttk.Combobox(filter_frame, values=["全部"] + [b["name"] for b in BRANCHES], state="readonly", width=12)
        self.filter_location.grid(row=0, column=3, padx=5, pady=5, sticky=tk.EW)
        self.filter_location.set("全部")
        self.filter_location.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        # 關鍵字
        ttk.Label(filter_frame, text="關鍵字搜尋:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.filter_kw = tk.Entry(filter_frame, bg=self.bg_color, fg=self.text_color, insertbackground=self.text_color, bd=1, relief="solid", width=15)
        self.filter_kw.grid(row=0, column=5, padx=5, pady=5, sticky=tk.EW)
        self.filter_kw.bind("<KeyRelease>", lambda e: self.apply_filters())

        # 預算與排氣量篩選
        ttk.Label(filter_frame, text="預算上限 (萬元):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.filter_price_max = tk.Entry(filter_frame, bg=self.bg_color, fg=self.text_color, insertbackground=self.text_color, bd=1, relief="solid", width=10)
        self.filter_price_max.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        self.filter_price_max.bind("<KeyRelease>", lambda e: self.apply_filters())

        ttk.Label(filter_frame, text="里程上限 (公里):").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.filter_mile_max = tk.Entry(filter_frame, bg=self.bg_color, fg=self.text_color, insertbackground=self.text_color, bd=1, relief="solid", width=10)
        self.filter_mile_max.grid(row=1, column=3, padx=5, pady=5, sticky=tk.EW)
        self.filter_mile_max.bind("<KeyRelease>", lambda e: self.apply_filters())

        # 對比按鈕
        self.compare_btn = tk.Button(filter_frame, text="⚖️ 進行橫向規格對比 (選取2~3輛)", bg=self.btn_bg, fg="#ffffff", activebackground=self.btn_active, font=('Microsoft JhengHei', 9, 'bold'), bd=0, command=self.trigger_comparison)
        self.compare_btn.grid(row=1, column=4, columnspan=2, padx=5, pady=5, sticky=tk.EW, ipady=2)

        # Main Table View
        table_frame = ttk.Frame(self.tab_search)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        cols = ("id", "title", "brand", "cc", "year", "mileage", "location", "price", "cp_index", "cp_label")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.heading("id", text="編號", command=lambda: self.sort_column("id", False))
        self.tree.heading("title", text="商品車款名稱", command=lambda: self.sort_column("title", False))
        self.tree.heading("brand", text="品牌", command=lambda: self.sort_column("brand", False))
        self.tree.heading("cc", text="CC數", command=lambda: self.sort_column("cc", False))
        self.tree.heading("year", text="年份", command=lambda: self.sort_column("year", False))
        self.tree.heading("mileage", text="里程 (km)", command=lambda: self.sort_column("mileage", False))
        self.tree.heading("location", text="存放分店", command=lambda: self.sort_column("location", False))
        self.tree.heading("price", text="售價 (NT$)", command=lambda: self.sort_column("price", False))
        self.tree.heading("cp_index", text="CP指數", command=lambda: self.sort_column("cp_index", False))
        self.tree.heading("cp_label", text="CP標籤", command=lambda: self.sort_column("cp_label", False))

        self.tree.column("id", width=45, anchor=tk.CENTER)
        self.tree.column("title", width=250, anchor=tk.W)
        self.tree.column("brand", width=70, anchor=tk.CENTER)
        self.tree.column("cc", width=65, anchor=tk.CENTER)
        self.tree.column("year", width=55, anchor=tk.CENTER)
        self.tree.column("mileage", width=85, anchor=tk.E)
        self.tree.column("location", width=95, anchor=tk.CENTER)
        self.tree.column("price", width=85, anchor=tk.E)
        self.tree.column("cp_index", width=65, anchor=tk.CENTER)
        self.tree.column("cp_label", width=65, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Double-1>", lambda e: self.on_double_click_item(self.tree))

    # =====================================================================
    # Tab 3: Store Navigator & O2O Guide (門市尋車與看車導航)
    # =====================================================================
    def setup_store_tab(self):
        lbl_intro = ttk.Label(self.tab_store, text="📌 實體分店 inventories 與現場看車導航預約", font=('Microsoft JhengHei', 12, 'bold'))
        lbl_intro.pack(anchor=tk.W, pady=10, padx=20)
        
        main_layout = tk.PanedWindow(self.tab_store, orient=tk.HORIZONTAL, bg=self.bg_color, bd=0, sashwidth=4)
        main_layout.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        # Left list of branches
        left_frame = ttk.LabelFrame(main_layout, text=" 選擇實體門市 ", padding=10)
        main_layout.add(left_frame)
        
        self.branch_listbox = tk.Listbox(left_frame, bg=self.panel_color, fg=self.text_color, selectbackground=self.accent_color, selectforeground="#ffffff", font=('Microsoft JhengHei', 10), bd=0)
        self.branch_listbox.pack(fill=tk.BOTH, expand=True)
        for b in BRANCHES:
            self.branch_listbox.insert(tk.END, f" 📍 {b['name']}")
        self.branch_listbox.bind("<<ListboxSelect>>", self.on_branch_select)
        
        # Right info & list
        right_frame = ttk.Frame(main_layout)
        main_layout.add(right_frame)

        # Top card for branch info
        self.branch_info_frame = ttk.LabelFrame(right_frame, text=" 門市詳細資訊 ", padding=12)
        self.branch_info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.lbl_branch_name = ttk.Label(self.branch_info_frame, text="請從左側選擇分店", font=('Microsoft JhengHei', 12, 'bold'), foreground=self.accent_color)
        self.lbl_branch_name.pack(anchor=tk.W, pady=2)
        
        self.lbl_branch_detail = ttk.Label(self.branch_info_frame, text="地址：-\n電話：-\n營業時間：-\n在庫統計：-", justify=tk.LEFT)
        self.lbl_branch_detail.pack(anchor=tk.W, pady=4)

        # Under info: list of inventory
        inv_frame = ttk.LabelFrame(right_frame, text=" 本分店在庫車輛清單 ", padding=10)
        inv_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        cols = ("title", "year", "mileage", "price", "cp_label")
        self.tree_branch_inv = ttk.Treeview(inv_frame, columns=cols, show="headings")
        self.tree_branch_inv.heading("title", text="車款名稱")
        self.tree_branch_inv.heading("year", text="年份")
        self.tree_branch_inv.heading("mileage", text="里程 (km)")
        self.tree_branch_inv.heading("price", text="售價 (NT$)")
        self.tree_branch_inv.heading("cp_label", text="性價比")
        
        self.tree_branch_inv.column("title", width=220, anchor=tk.W)
        self.tree_branch_inv.column("year", width=55, anchor=tk.CENTER)
        self.tree_branch_inv.column("mileage", width=85, anchor=tk.E)
        self.tree_branch_inv.column("price", width=85, anchor=tk.E)
        self.tree_branch_inv.column("cp_label", width=70, anchor=tk.CENTER)
        
        inv_scroll = ttk.Scrollbar(inv_frame, orient=tk.VERTICAL, command=self.tree_branch_inv.yview)
        self.tree_branch_inv.configure(yscrollcommand=inv_scroll.set)
        self.tree_branch_inv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inv_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_branch_inv.bind("<Double-1>", lambda e: self.on_double_click_item(self.tree_branch_inv))

        # Bottom action button
        self.export_btn = tk.Button(right_frame, text="📝 匯出所選車款預約看車規劃書 (含驗車 10 大防呆檢查表)", bg="#27ae60", fg="#ffffff", activebackground="#2ecc71", font=('Microsoft JhengHei', 10, 'bold'), bd=0, height=2, command=self.export_appointment_guide)
        self.export_btn.pack(fill=tk.X, padx=10, pady=10)

    # =====================================================================
    # Tab 4: Charts Visualized (市場統計分析圖表)
    # =====================================================================
    def setup_charts_tab(self):
        canvas = tk.Canvas(self.tab_charts, bg=self.bg_color, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_charts, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        lbl_title = ttk.Label(scrollable_frame, text="📈 市場分析圖表可視化", font=('Microsoft JhengHei', 12, 'bold'))
        lbl_title.pack(anchor=tk.W, pady=10, padx=20)
        
        charts_layout = tk.Frame(scrollable_frame, bg=self.bg_color)
        charts_layout.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # 價格分布直方圖
        hist_frame = tk.LabelFrame(charts_layout, text=" 二手機車價格分布直方圖 (萬元) ", bg=self.panel_color, fg=self.accent_color, font=('Microsoft JhengHei', 9), padx=10, pady=10)
        hist_frame.grid(row=0, column=0, padx=10, pady=10)
        self.lbl_hist_img = tk.Label(hist_frame, text="請先載入數據", bg=self.bg_color, fg=self.sec_text_color, width=65, height=18)
        self.lbl_hist_img.pack()
        
        # 里程/現價散佈圖
        scatter_frame = tk.LabelFrame(charts_layout, text=" 里程與現價散佈圖 (性價比分類) ", bg=self.panel_color, fg=self.accent_color, font=('Microsoft JhengHei', 9), padx=10, pady=10)
        scatter_frame.grid(row=0, column=1, padx=10, pady=10)
        self.lbl_scatter_img = tk.Label(scatter_frame, text="請先載入數據", bg=self.bg_color, fg=self.sec_text_color, width=65, height=18)
        self.lbl_scatter_img.pack()

        # 品牌市佔圓餅圖
        pie_frame = tk.LabelFrame(charts_layout, text=" 熱門品牌市佔圓餅圖 (Top 5) ", bg=self.panel_color, fg=self.accent_color, font=('Microsoft JhengHei', 9), padx=10, pady=10)
        pie_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        self.lbl_pie_img = tk.Label(pie_frame, text="請先載入數據", bg=self.bg_color, fg=self.sec_text_color, width=65, height=18)
        self.lbl_pie_img.pack()

    # =====================================================================
    # API & EVENT HANDLERS
    # =====================================================================
    def check_backend_connection(self):
        url = self.api_url_var.get()
        self.client.set_base_url(url)
        self.status_text.set("正在測試 API 連線...")
        self.root.update_idletasks()
        if self.client.ping():
            self.status_text.set("🟢 API 連線成功 (正常工作)")
            self.status_label.configure(foreground="#2ecc71")
            self.progress_text.set("連線成功，準備就緒！")
        else:
            self.status_text.set("🔴 API 連線失敗 (請確認後端是否啟動)")
            self.status_label.configure(foreground="#e74c3c")
            self.progress_text.set("連線失敗。請確認 FastAPI 後端服務是否已開啟。")

    def export_excel_report(self):
        from tkinter import filedialog
        try:
            excel_bytes = self.client.download_excel_report()
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
                title="儲存 Excel 完整報表",
                initialfile="貳輪嶼機車CP值大數據分析報表.xlsx"
            )
            if file_path:
                with open(file_path, "wb") as f:
                    f.write(excel_bytes)
                messagebox.showinfo("匯出成功", f"Excel 報表已成功匯出至：\n{file_path}")
        except Exception as e:
            messagebox.showerror("匯出失敗", f"匯出 Excel 報表失敗: {e}")

    def open_html_report(self):
        import webbrowser
        url = f"{self.client.base_url}/static/reports/report.html"
        try:
            resp = requests.head(url, timeout=5)
            if resp.status_code == 200:
                webbrowser.open(url)
            else:
                messagebox.showerror("開啟失敗", "HTML 報表不存在，請先執行爬蟲更新數據。")
        except Exception as e:
            messagebox.showerror("錯誤", f"開啟 HTML 報表失敗: {e}")

    def start_crawl_thread(self):
        self.crawl_btn.configure(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = 16  # 預估共 16 頁
        self.progress_text.set("正在初始化增量爬蟲與快取中...")
        
        # 啟動爬蟲背景執行緒
        thread = threading.Thread(target=self.run_crawl)
        thread.daemon = True
        thread.start()
        
        # 啟動進度條更新輪詢
        self.polling_active = True
        poll_thread = threading.Thread(target=self.poll_crawl_status_loop)
        poll_thread.daemon = True
        poll_thread.start()

    def run_crawl(self):
        try:
            result = self.client.trigger_crawl()
            self.root.after(0, self.on_crawl_success, result)
        except Exception as e:
            self.root.after(0, self.on_crawl_failed, str(e))

    def poll_crawl_status_loop(self):
        import time
        while self.polling_active:
            try:
                data = self.client.get_crawl_status()
                if data["is_running"]:
                    curr = data["current_page"]
                    status_text = data["status"]
                    scraped_count = data["scraped_count"]
                    self.root.after(0, self.update_progress, curr, status_text, scraped_count)
            except Exception:
                pass
            time.sleep(0.5)

    def update_progress(self, current_page, status_text, scraped_count):
        if current_page > self.progress_bar['maximum']:
            self.progress_bar['maximum'] = current_page
            
        self.progress_bar['value'] = current_page
        
        max_val = self.progress_bar['maximum']
        pct = int((current_page / max_val) * 100) if max_val > 0 else 0
        pct = min(100, pct)
        
        self.progress_text.set(
            f"正在爬取貳輪嶼車源資訊...\n"
            f"進度: ({status_text})\n"
            f"目前已載入 {scraped_count} 筆車源"
        )

    def on_crawl_success(self, result):
        self.polling_active = False
        self.crawl_btn.configure(state=tk.NORMAL)
        self.progress_bar['value'] = self.progress_bar['maximum']
        messagebox.showinfo("爬蟲完工", f"資料抓取與 CP 值分析成功！\n共載入及分析了 {result['scraped_count']} 台二手機車。")
        self.progress_text.set(f"爬蟲成功！完成 {result['scraped_count']} 台車輛 CP 相對定位分析。")
        self.load_data_and_charts()

    def on_crawl_failed(self, err_msg):
        self.polling_active = False
        self.crawl_btn.configure(state=tk.NORMAL)
        self.progress_bar['value'] = 0
        messagebox.showerror("爬蟲錯誤", f"無法完成爬蟲: {err_msg}")
        self.progress_text.set(f"爬蟲失敗。原因: {err_msg}")

    def load_data_and_charts(self):
        self.load_btn.configure(state=tk.DISABLED)
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = 6
        self.progress_text.set("正在與 API 伺服器通訊... (0%)")
        thread = threading.Thread(target=self.run_load_data)
        thread.daemon = True
        thread.start()

    def run_load_data(self):
        try:
            self.root.after(0, self.update_load_progress, 0, "正在獲取商品清單... (0%)")
            products = self.client.get_products()
            
            self.root.after(0, self.update_load_progress, 1, "正在計算大數據統計資訊... (16%)")
            analysis = self.client.get_analysis()
            
            self.root.after(0, self.update_load_progress, 2, "正在產生市場圖表連結... (33%)")
            charts = self.client.get_charts()
            
            self.root.after(0, self.update_load_progress, 3, "正在下載價格分佈圖... (50%)")
            hist_bytes = self.client.download_chart_image(charts["histogram_url"])
            
            self.root.after(0, self.update_load_progress, 4, "正在下載里程價格分佈圖... (66%)")
            scatter_bytes = self.client.download_chart_image(charts["scatter_url"])
            
            self.root.after(0, self.update_load_progress, 5, "正在下載品牌市佔圓餅圖... (83%)")
            pie_bytes = self.client.download_chart_image(charts["brand_pie_url"])
            
            self.root.after(0, self.update_load_progress, 6, "影像與數據下載完成，正在更新介面... (100%)")
            self.root.after(50, self.on_load_success, products, analysis, hist_bytes, scatter_bytes, pie_bytes)
        except Exception as e:
            self.root.after(0, self.on_load_failed, str(e))

    def update_load_progress(self, step_num, message):
        self.progress_bar['value'] = step_num
        self.progress_text.set(message)

    def on_load_success(self, products, analysis, hist_bytes, scatter_bytes, pie_bytes):
        self.load_btn.configure(state=tk.NORMAL)
        self.all_products = products
        
        # 更新指標卡
        self.card_total.set(f"{analysis['total_count']} 輛")
        self.card_avg_orig.set(f"NT$ {int(analysis['avg_current_price']):,}")
        self.card_avg_curr.set(f"{int(analysis['avg_mileage']):,} km")
        
        ratio = (analysis['value_choices_count'] / analysis['total_count'] * 100) if analysis['total_count'] > 0 else 0
        self.card_discount.set(f"{ratio:.1f}% ({analysis['value_choices_count']}輛超值)")

        # 填寫廠牌 Combobox
        brands = sorted(list(set([p["brand"] for p in products if p["brand"]])))
        self.filter_brand["values"] = ["全部"] + brands

        # 填寫 Tab 1 排行榜
        for item in self.tree_cp_top.get_children():
            self.tree_cp_top.delete(item)
        for item in self.tree_mile_top.get_children():
            self.tree_mile_top.delete(item)
            
        cp_sorted = sorted(products, key=lambda x: x.get("cp_index", 0.0), reverse=True)[:10]
        for p in cp_sorted:
            self.tree_cp_top.insert("", tk.END, values=(
                p["title"], p["year"], f"{int(p['mileage']):,}", f"{int(p['current_price']):,}", p["cp_index"], p["cp_label"]
            ), tags=(p["url"],))

        mile_sorted = sorted(products, key=lambda x: x.get("mileage", 999999.0))[:10]
        for p in mile_sorted:
            self.tree_mile_top.insert("", tk.END, values=(
                p["title"], p["year"], f"{int(p['mileage']):,}", f"{int(p['current_price']):,}", p["cp_index"], p["cp_label"]
            ), tags=(p["url"],))

        # 重新整理篩選 Treeview
        self.apply_filters()

        # 影像載入與快取
        self.hist_image = convert_bytes_to_tk_image(hist_bytes, 480, 320)
        if self.hist_image:
            self.lbl_hist_img.configure(image=self.hist_image, text="")
        else:
            self.lbl_hist_img.configure(image="", text="暫無圖表數據 (請先執行爬蟲)")
            
        self.scatter_image = convert_bytes_to_tk_image(scatter_bytes, 480, 320)
        if self.scatter_image:
            self.lbl_scatter_img.configure(image=self.scatter_image, text="")
        else:
            self.lbl_scatter_img.configure(image="", text="暫無圖表數據 (請先執行爬蟲)")

        self.brand_pie_image = convert_bytes_to_tk_image(pie_bytes, 480, 320)
        if self.brand_pie_image:
            self.lbl_pie_img.configure(image=self.brand_pie_image, text="")
        else:
            self.lbl_pie_img.configure(image="", text="暫無圖表數據 (請先執行爬蟲)")
            
        self.progress_text.set("大數據與分析圖表載入完畢！")
        messagebox.showinfo("載入成功", "數據與市場統計圖表載入成功！")

    def on_load_failed(self, err_msg):
        self.load_btn.configure(state=tk.NORMAL)
        messagebox.showerror("載入失敗", f"讀取數據失敗: {err_msg}")
        self.progress_text.set(f"載入失敗: {err_msg}")

    def apply_filters(self):
        brand = self.filter_brand.get()
        location = self.filter_location.get()
        kw = self.filter_kw.get().strip().lower()
        
        max_p_str = self.filter_price_max.get().strip()
        max_m_str = self.filter_mile_max.get().strip()
        
        max_price = float(max_p_str) * 10000.0 if max_p_str.isdigit() else float('inf')
        max_mileage = float(max_m_str) if max_m_str.isdigit() else float('inf')

        # 濾清
        filtered = []
        for p in self.all_products:
            if brand != "全部" and p["brand"] != brand:
                continue
            if location != "全部":
                b_short = clean_loc_name(location)
                p_loc = clean_loc_name(p["location"] or "")
                if b_short not in p_loc:
                    continue
            if kw and kw not in p["title"].lower():
                continue
            if p["current_price"] > max_price:
                continue
            if p["mileage"] > max_mileage:
                continue
            filtered.append(p)

        # 填寫表格
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for p in filtered:
            self.tree.insert("", tk.END, values=(
                p["id"], p["title"], p["brand"] or "其他", f"{p['displacement']} cc", p["year"],
                f"{int(p['mileage']):,}", p["location"] or "其他", f"{int(p['current_price']):,}",
                p["cp_index"], p["cp_label"]
            ), tags=(p["url"],))

    def sort_column(self, col, reverse):
        l = []
        for k in self.tree.get_children(""):
            val = self.tree.set(k, col)
            cleaned_val = val
            if col == "price":
                cleaned_val = val.replace(",", "").strip()
            elif col == "mileage":
                cleaned_val = val.replace(",", "").strip()
            elif col == "cc":
                cleaned_val = val.replace(" cc", "").strip()
            elif col == "id" or col == "year" or col == "cp_index":
                cleaned_val = val
                
            try:
                l.append((float(cleaned_val), k))
            except ValueError:
                l.append((val.lower(), k))
                
        l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            self.tree.move(k, "", index)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    # =====================================================================
    # MULTI-MOTOR COMPARISON popup (多車橫向對比視窗)
    # =====================================================================
    def trigger_comparison(self):
        selected = self.tree.selection()
        if len(selected) < 2 or len(selected) > 3:
            messagebox.showwarning("對比提示", "請在下方列表中選取或勾選 2 到 3 台車輛進行橫向規格對比！")
            return
            
        compare_items = []
        for s in selected:
            vals = self.tree.item(s, "values")
            # 依 URL 對照找出完整產品資訊
            url = self.tree.item(s, "tags")[0]
            prod = next((p for p in self.all_products if p["url"] == url), None)
            if prod:
                compare_items.append(prod)

        # 彈出對比 Toplevel 視窗
        win = tk.Toplevel(self.root)
        win.title("⚖️ 二手機車橫向規格對比")
        win.geometry("850x550")
        win.configure(bg=self.bg_color)
        win.transient(self.root)
        win.grab_set()
        
        # 標題
        tk.Label(win, text="📊 選定車款多維度橫向規格對比", bg=self.bg_color, fg=self.accent_color, font=('Microsoft JhengHei', 13, 'bold'), pady=10).pack()

        main_grid = tk.Frame(win, bg=self.panel_color, padx=10, pady=10)
        main_grid.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 列標題定義
        rows = [
            ("品名", "title"),
            ("廠牌", "brand"),
            ("排氣量", "displacement"),
            ("製造年份", "year"),
            ("里程數", "mileage"),
            ("存放分店", "location"),
            ("售價", "current_price"),
            ("CP指數", "cp_index"),
            ("CP標籤", "cp_label")
        ]

        # 找出最優值指標
        best_price = min([p["current_price"] for p in compare_items])
        best_mileage = min([p["mileage"] for p in compare_items])
        best_year = max([p["year"] for p in compare_items])
        best_cp = max([p["cp_index"] for p in compare_items])

        # 繪製 Grid
        # 欄位 0 為屬性名稱
        tk.Label(main_grid, text="規格項目", bg="#2d2d38", fg=self.text_color, font=('Microsoft JhengHei', 10, 'bold'), width=12, relief="flat", bd=1, pady=6).grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        for col_idx, item in enumerate(compare_items):
            tk.Label(main_grid, text=f"車款 {col_idx + 1}", bg="#2d2d38", fg=self.accent_color, font=('Microsoft JhengHei', 10, 'bold'), relief="flat", bd=1, pady=6).grid(row=0, column=col_idx+1, sticky="nsew", padx=1, pady=1)

        for row_idx, (label, key) in enumerate(rows):
            # 屬性列名稱
            tk.Label(main_grid, text=label, bg="#25252c", fg=self.sec_text_color, font=('Microsoft JhengHei', 9, 'bold'), width=12, pady=5).grid(row=row_idx+1, column=0, sticky="nsew", padx=1, pady=1)
            
            for col_idx, item in enumerate(compare_items):
                val = item.get(key, "")
                bg_col = self.panel_color
                fg_col = self.text_color
                font_style = ('Microsoft JhengHei', 9)
                
                # 數值文字格式化
                text_val = str(val)
                if key == "current_price":
                    text_val = f"NT$ {int(val):,}"
                    if val == best_price:
                        bg_col = "#27ae60"  # 最便宜高亮綠色
                        fg_col = "#ffffff"
                        font_style = ('Microsoft JhengHei', 9, 'bold')
                elif key == "mileage":
                    text_val = f"{int(val):,} km"
                    if val == best_mileage:
                        bg_col = "#27ae60"  # 里程最低高亮
                        fg_col = "#ffffff"
                        font_style = ('Microsoft JhengHei', 9, 'bold')
                elif key == "year":
                    text_val = f"{val} 年"
                    if val == best_year:
                        bg_col = "#27ae60"
                        fg_col = "#ffffff"
                        font_style = ('Microsoft JhengHei', 9, 'bold')
                elif key == "cp_index":
                    text_val = f"{val}"
                    if val == best_cp:
                        bg_col = "#27ae60"
                        fg_col = "#ffffff"
                        font_style = ('Microsoft JhengHei', 9, 'bold')
                elif key == "displacement":
                    text_val = f"{val} cc"
                elif key == "title":
                    text_val = val[:24] + "..." if len(val) > 24 else val

                lbl = tk.Label(main_grid, text=text_val, bg=bg_col, fg=fg_col, font=font_style, wraplength=200, pady=5)
                lbl.grid(row=row_idx+1, column=col_idx+1, sticky="nsew", padx=1, pady=1)

        # 列寬均分
        main_grid.grid_columnconfigure(0, weight=1)
        for col_idx in range(len(compare_items)):
            main_grid.grid_columnconfigure(col_idx + 1, weight=2)
            
        # 底部按鈕
        btn_frame = tk.Frame(win, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=10)
        
        for col_idx, item in enumerate(compare_items):
            url = item["url"]
            btn = tk.Button(btn_frame, text=f"複製車款 {col_idx+1} 網址", bg=self.btn_bg, fg="#ffffff", bd=0, font=('Microsoft JhengHei', 9), command=lambda u=url: self.copy_url_to_clipboard(u))
            btn.pack(side=tk.LEFT, expand=True, padx=10, ipady=4)

    def copy_url_to_clipboard(self, url):
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        messagebox.showinfo("複製成功", f"商品網址已複製至剪貼簿：\n{url}")

    # =====================================================================
    # STORE NAVIGATOR & O2O EXPORTS (TAB 3)
    # =====================================================================
    def on_branch_select(self, event):
        sel = self.branch_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        branch = BRANCHES[idx]
        
        # 篩選出該店車輛
        branch_products = []
        # 以分店名字局部匹配
        b_short_name = clean_loc_name(branch["name"])
        for p in self.all_products:
            loc = clean_loc_name(p["location"] or "")
            if b_short_name in loc:
                branch_products.append(p)
                
        # 計算統計資訊
        total_count = len(branch_products)
        avg_price = int(sum([p["current_price"] for p in branch_products]) / total_count) if total_count > 0 else 0
        
        # 更新文字
        self.lbl_branch_name.configure(text=f"📍 {branch['name']}")
        self.lbl_branch_detail.configure(text=
            f"地址：{branch['address']}\n"
            f"電話：{branch['phone']}\n"
            f"營業時間：{branch['hours']}\n"
            f"在庫統計：共 {total_count} 輛車，平均價格 NT$ {avg_price:,} 元\n"
            f"官方 LINE 通道：{branch['line']}"
        )

        # 填寫分店库存 Treeview
        for item in self.tree_branch_inv.get_children():
            self.tree_branch_inv.delete(item)
            
        for p in branch_products:
            self.tree_branch_inv.insert("", tk.END, values=(
                p["title"], p["year"], f"{int(p['mileage']):,}", f"{int(p['current_price']):,}", p["cp_label"]
            ), tags=(p["url"],))

    def export_appointment_guide(self):
        # 獲取所選門市在庫車輛
        selected_item = self.tree_branch_inv.selection()
        if not selected_item:
            # 檢查是否在 Tab 2 Search 裡有選中
            selected_item = self.tree.selection()
            if not selected_item:
                messagebox.showwarning("匯出提示", "請在「實體門市庫存清單」或「全台車源篩選」中選取一台車輛以匯出預約規劃書！")
                return
            else:
                tree_source = self.tree
        else:
            tree_source = self.tree_branch_inv

        url = tree_source.item(selected_item[0], "tags")[0]
        prod = next((p for p in self.all_products if p["url"] == url), None)
        if not prod:
            messagebox.showerror("錯誤", "找不到該車輛的詳細資訊！")
            return

        # 找出關聯門市資訊
        branch_info = None
        for b in BRANCHES:
            b_short = clean_loc_name(b["name"])
            p_loc = clean_loc_name(prod["location"] or "")
            if b_short in p_loc:
                branch_info = b
                break
        if not branch_info:
            branch_info = {
                "name": prod["location"] or "貳輪嶼實體門市",
                "address": "全台各實體門市皆可配合預約，詳見官網",
                "phone": "0987-654-321 (預約專線)",
                "hours": "10:00 - 21:00",
                "line": "https://line.me/ti/p/2motor"
            }

        # 產生 markdown 內容
        now_str = datetime.datetime.now().strftime("%Y-%m-%d")
        md_content = f"""# 貳輪嶼二手機車預約看車規劃書 (O2O Appointment Guide)
Generated on: {now_str}

感謝您使用貳輪嶼大數據選購決策系統。以下是您所選定車款的看車與現場驗車清單：

## 1. 預約看車型號與規格
*   **車款名稱**：{prod['title']}
*   **廠牌品牌**：{prod['brand'] or '其他'}
*   **排氣量**：{prod['displacement']} cc
*   **製造年份**：{prod['year']} 年
*   **里程數**：{int(prod['mileage']):,} 公里
*   **網路售價**：NT$ {int(prod['current_price']):,} 元
*   **大數據評估**：CP 值相對指數 {prod['cp_index']} (評級為 **{prod['cp_label']}**)
*   **商品網址**：{prod['url']}

## 2. 存放實體分店資訊
*   **看車門市**：{branch_info['name']}
*   **門市地址**：{branch_info['address']}
*   **聯絡電話**：{branch_info['phone']}
*   **營業時間**：{branch_info['hours']}
*   **LINE 聯絡**：{branch_info['line']}

## 3. 二手機車現場驗車 10 大防呆檢查表 (驗車照表操課，防範事故調表車)

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
"""

        # 寫入專案根目錄
        filename = f"預約看車規劃書_{prod['title'].replace(' ', '_').replace('【', '').replace('】', '')}_{now_str}.md"
        # 過濾不合法檔案字元
        filename = re.sub(r'[\/:*?"<>|]', '', filename)
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            
            messagebox.showinfo("規劃書匯出成功", f"看車規劃書已成功匯出至：\n{file_path}\n\n已包含專屬『二手機車現場驗車 10 大防呆檢查表』，建議列印或傳至手機看車時使用！")
        except Exception as write_err:
            messagebox.showerror("匯出失敗", f"寫入規劃書檔案失敗: {write_err}")

    # =====================================================================
    # DOUBLE CLICK TABLE EVENT
    # =====================================================================
    def on_double_click_item(self, tree_elem):
        selected_item = tree_elem.selection()
        if not selected_item:
            return
        item_data = tree_elem.item(selected_item[0], "values")
        if item_data:
            url = tree_elem.item(selected_item[0], "tags")[0]
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("複製成功", f"商品網址已複製至剪貼簿：\n{url}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MotorAnalysisApp(root)
    root.mainloop()
