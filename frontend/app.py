import tkinter as tk
from tkinter import ttk, messagebox
import threading
import io
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
        response = requests.post(f"{self.base_url}/api/v1/crawl", timeout=120)
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
            "histogram_url": f"{self.base_url}{data['histogram_url']}",
            "scatter_url": f"{self.base_url}{data['scatter_url']}",
            "brand_pie_url": f"{self.base_url}{data['brand_pie_url']}"
        }

    def download_chart_image(self, full_url: str) -> bytes:
        response = requests.get(full_url, timeout=10)
        if response.status_code != 200:
            raise Exception("下載圖表影像失敗")
        return response.content

# =====================================================================
# 2. 圖片轉換輔助工具 (IMAGE UTILS)
# =====================================================================
def convert_bytes_to_tk_image(img_bytes: bytes, target_width: int = 480, target_height: int = 320) -> ImageTk.PhotoImage:
    """將二進位影像流轉換為 Pillow Tkinter PhotoImage 並等比縮放"""
    image = Image.open(io.BytesIO(img_bytes))
    image_resized = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image_resized)

# =====================================================================
# 3. Tkinter 視窗主應用程式 (UI APP)
# =====================================================================
class MotorAnalysisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("貳輪部品電商市場大數據分析平台 - 單機控制面板")
        self.root.geometry("1100x720")
        self.root.minsize(1000, 650)
        
        self.client = APIClient("http://127.0.0.1:8000")
        
        # 暫存 PhotoImage 防範 Garbage Collection
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
        
        title_label = ttk.Label(top_frame, text="貳輪部品電商市場大數據分析平台", style="Header.TLabel")
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
        sb_title = tk.Label(sidebar, text="控制與設定面板", bg=self.panel_color, fg=self.text_color, font=('Microsoft JhengHei', 12, 'bold'), pady=15)
        sb_title.pack(fill=tk.X)
        
        api_config_frame = tk.LabelFrame(sidebar, text=" API 伺服器設定 ", bg=self.panel_color, fg=self.accent_color, font=('Microsoft JhengHei', 9), padx=10, pady=10, bd=1, relief='solid')
        api_config_frame.pack(fill=tk.X, padx=15, pady=10)
        self.api_url_var = tk.StringVar(value="http://127.0.0.1:8000")
        api_entry = tk.Entry(api_config_frame, textvariable=self.api_url_var, bg=self.bg_color, fg=self.text_color, insertbackground=self.text_color, font=('Consolas', 10), bd=0)
        api_entry.pack(fill=tk.X, ipady=4, pady=5)
        conn_btn = tk.Button(api_config_frame, text="測試並儲存連線", bg=self.btn_bg, fg="#ffffff", activebackground=self.btn_active, activeforeground="#ffffff", font=('Microsoft JhengHei', 9, 'bold'), bd=0, command=self.check_backend_connection)
        conn_btn.pack(fill=tk.X, pady=5)

        action_frame = tk.LabelFrame(sidebar, text=" 大數據分析操作 ", bg=self.panel_color, fg=self.accent_color, font=('Microsoft JhengHei', 9), padx=10, pady=10, bd=1, relief='solid')
        action_frame.pack(fill=tk.X, padx=15, pady=10)
        self.crawl_btn = tk.Button(action_frame, text="🚀 觸發雲端爬蟲 (全部頁面)", bg="#27ae60", fg="#ffffff", activebackground="#2ecc71", activeforeground="#ffffff", font=('Microsoft JhengHei', 10, 'bold'), bd=0, height=2, command=self.start_crawl_thread)
        self.crawl_btn.pack(fill=tk.X, pady=8)
        self.load_btn = tk.Button(action_frame, text="📊 撈取與分析數據", bg="#e67e22", fg="#ffffff", activebackground="#f39c12", activeforeground="#ffffff", font=('Microsoft JhengHei', 10, 'bold'), bd=0, height=2, command=self.load_data_and_charts)
        self.load_btn.pack(fill=tk.X, pady=8)

        self.progress_text = tk.StringVar(value="等待指令...")
        progress_lbl = tk.Label(sidebar, textvariable=self.progress_text, bg=self.panel_color, fg=self.sec_text_color, font=('Microsoft JhengHei', 9), justify=tk.LEFT, wraplength=230)
        progress_lbl.pack(fill=tk.X, padx=15, pady=20)
        
        # Tabs Container
        self.notebook = ttk.Notebook(self.right_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10)
        self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_products = ttk.Frame(self.notebook)
        self.tab_charts = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_dashboard, text=" 數據概覽 ")
        self.notebook.add(self.tab_products, text=" 商品資料庫 ")
        self.notebook.add(self.tab_charts, text=" 市場可視化圖表 ")
        
        self.setup_dashboard_tab()
        self.setup_products_tab()
        self.setup_charts_tab()

    def setup_dashboard_tab(self):
        lbl_intro = ttk.Label(self.tab_dashboard, text="📌 電商市場大數據統計分析面板", font=('Microsoft JhengHei', 13, 'bold'))
        lbl_intro.pack(anchor=tk.W, pady=15, padx=20)
        
        cards_frame = ttk.Frame(self.tab_dashboard)
        cards_frame.pack(fill=tk.X, padx=15)
        self.card_total = self.create_card(cards_frame, "商品抓取總量", "0 件", 0, 0)
        self.card_avg_orig = self.create_card(cards_frame, "市場平均原價", "NT$ 0", 0, 1)
        self.card_avg_curr = self.create_card(cards_frame, "市場平均現價", "NT$ 0", 1, 0)
        self.card_discount = self.create_card(cards_frame, "平均折扣幅度", "0.0%", 1, 1)
        
        group_frame = ttk.LabelFrame(self.tab_dashboard, text=" 各價格區間商品分佈情形 ", padding=15)
        group_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=25)
        self.dist_text_var = tk.StringVar(value="目前無數據。請點擊左側「撈取與分析數據」按鈕載入最新資料。")
        self.lbl_dist = tk.Label(group_frame, textvariable=self.dist_text_var, bg=self.bg_color, fg=self.text_color, font=('Consolas', 11), justify=tk.LEFT, anchor=tk.NW)
        self.lbl_dist.pack(fill=tk.BOTH, expand=True)

    def create_card(self, parent, title, init_val, row, col):
        card = ttk.Frame(parent, style='Card.TFrame', padding=15)
        card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')
        parent.grid_columnconfigure(col, weight=1)
        parent.grid_rowconfigure(row, weight=1)
        lbl_title = ttk.Label(card, text=title, style='CardTitle.TLabel')
        lbl_title.pack(anchor=tk.W, pady=2)
        val_var = tk.StringVar(value=init_val)
        lbl_val = ttk.Label(card, textvariable=val_var, style='CardVal.TLabel')
        lbl_val.pack(anchor=tk.W, pady=5)
        return val_var

    def setup_products_tab(self):
        lbl_title = ttk.Label(self.tab_products, text="📋 商品明細資料庫 (已清洗)", font=('Microsoft JhengHei', 12, 'bold'))
        lbl_title.pack(anchor=tk.W, pady=10, padx=15)
        
        table_frame = ttk.Frame(self.tab_products)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        columns = ("id", "title", "original_price", "current_price", "discount_rate", "url")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        self.tree.heading("id", text="編號")
        self.tree.heading("title", text="商品名稱")
        self.tree.heading("original_price", text="原價 (NT$)")
        self.tree.heading("current_price", text="現價 (NT$)")
        self.tree.heading("discount_rate", text="折數/折扣")
        self.tree.heading("url", text="商品網址")
        
        self.tree.column("id", width=60, minwidth=50, anchor=tk.CENTER)
        self.tree.column("title", width=350, minwidth=200, anchor=tk.W)
        self.tree.column("original_price", width=100, anchor=tk.E)
        self.tree.column("current_price", width=100, anchor=tk.E)
        self.tree.column("discount_rate", width=100, anchor=tk.CENTER)
        self.tree.column("url", width=250, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

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
        
        # 價格直方圖
        hist_frame = tk.LabelFrame(charts_layout, text=" 價格分布直方圖 ", bg=self.panel_color, fg=self.accent_color, font=('Microsoft JhengHei', 9), padx=10, pady=10)
        hist_frame.grid(row=0, column=0, padx=10, pady=10)
        self.lbl_hist_img = tk.Label(hist_frame, text="請先載入數據", bg=self.bg_color, fg=self.sec_text_color, width=65, height=18)
        self.lbl_hist_img.pack()
        
        # 折扣散佈圖
        scatter_frame = tk.LabelFrame(charts_layout, text=" 折扣幅度散佈圖 ", bg=self.panel_color, fg=self.accent_color, font=('Microsoft JhengHei', 9), padx=10, pady=10)
        scatter_frame.grid(row=0, column=1, padx=10, pady=10)
        self.lbl_scatter_img = tk.Label(scatter_frame, text="請先載入數據", bg=self.bg_color, fg=self.sec_text_color, width=65, height=18)
        self.lbl_scatter_img.pack()

        # 品牌圓餅圖
        pie_frame = tk.LabelFrame(charts_layout, text=" 熱門品牌佔比圓餅圖 (Top 5) ", bg=self.panel_color, fg=self.accent_color, font=('Microsoft JhengHei', 9), padx=10, pady=10)
        pie_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        self.lbl_pie_img = tk.Label(pie_frame, text="請先載入數據", bg=self.bg_color, fg=self.sec_text_color, width=65, height=18)
        self.lbl_pie_img.pack()

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

    def start_crawl_thread(self):
        self.crawl_btn.configure(state=tk.DISABLED)
        self.progress_text.set("正在執行爬蟲中...\n(使用 Playwright 爬取所有頁面，約需 1-2 分鐘，請稍候...)")
        thread = threading.Thread(target=self.run_crawl)
        thread.daemon = True
        thread.start()

    def run_crawl(self):
        try:
            result = self.client.trigger_crawl()
            self.root.after(0, self.on_crawl_success, result)
        except Exception as e:
            self.root.after(0, self.on_crawl_failed, str(e))

    def on_crawl_success(self, result):
        self.crawl_btn.configure(state=tk.NORMAL)
        messagebox.showinfo("爬蟲完工", f"資料更新成功！\n共爬取了 {result['scraped_count']} 個商品。")
        self.progress_text.set(f"爬蟲成功！已更新 {result['scraped_count']} 件商品資料。")
        self.load_data_and_charts()

    def on_crawl_failed(self, err_msg):
        self.crawl_btn.configure(state=tk.NORMAL)
        messagebox.showerror("爬蟲錯誤", f"無法完成爬蟲: {err_msg}")
        self.progress_text.set(f"爬蟲失敗。原因: {err_msg}")

    def load_data_and_charts(self):
        self.load_btn.configure(state=tk.DISABLED)
        self.progress_text.set("正在獲取統計數據與影像分析...")
        thread = threading.Thread(target=self.run_load_data)
        thread.daemon = True
        thread.start()

    def run_load_data(self):
        try:
            products = self.client.get_products()
            analysis = self.client.get_analysis()
            charts = self.client.get_charts()
            
            hist_bytes = self.client.download_chart_image(charts["histogram_url"])
            scatter_bytes = self.client.download_chart_image(charts["scatter_url"])
            pie_bytes = self.client.download_chart_image(charts["brand_pie_url"])
            
            self.root.after(0, self.on_load_success, products, analysis, hist_bytes, scatter_bytes, pie_bytes)
        except Exception as e:
            self.root.after(0, self.on_load_failed, str(e))

    def on_load_success(self, products, analysis, hist_bytes, scatter_bytes, pie_bytes):
        self.load_btn.configure(state=tk.NORMAL)
        
        self.card_total.set(f"{analysis['total_count']} 件")
        self.card_avg_orig.set(f"NT$ {int(analysis['avg_original_price']):,}")
        self.card_avg_curr.set(f"NT$ {int(analysis['avg_current_price']):,}")
        
        avg_disc = analysis['avg_discount_rate']
        self.card_discount.set("無折扣" if avg_disc == 0 else f"{round((1 - avg_disc)*10, 1)} 折 (省 {round(avg_disc*100, 1)}%)")

        # 區間分佈
        dist_str = "【市場各價位帶商品數量統計】\n"
        for group, count in sorted(analysis['price_distribution'].items(), key=lambda x: x[0]):
            dist_str += f"● {group:<15}: {count:>4} 件\n"
        dist_str += f"\n最高單價: NT$ {int(analysis['max_price']):,}\n最低單價: NT$ {int(analysis['min_price']):,}\n最大折數: {round((1 - analysis['max_discount_rate'])*10, 1)} 折"
        self.dist_text_var.set(dist_str)

        # 商品明細
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in products:
            disc_rate = p['discount_rate']
            disc_label = "無折扣" if disc_rate == 0 else f"{round((1 - disc_rate)*10, 1)} 折"
            self.tree.insert("", tk.END, values=(
                p['id'], p['title'], f"{int(p['original_price']):,}",
                f"{int(p['current_price']):,}", disc_label, p['url']
            ))

        # 影像載入與快取
        self.hist_image = convert_bytes_to_tk_image(hist_bytes, 480, 320)
        self.lbl_hist_img.configure(image=self.hist_image, text="")
        
        self.scatter_image = convert_bytes_to_tk_image(scatter_bytes, 480, 320)
        self.lbl_scatter_img.configure(image=self.scatter_image, text="")

        self.brand_pie_image = convert_bytes_to_tk_image(pie_bytes, 480, 320)
        self.lbl_pie_img.configure(image=self.brand_pie_image, text="")
        
        self.progress_text.set("數據與圖表同步完成！")
        messagebox.showinfo("載入成功", "數據與圖表載入成功！")

    def on_load_failed(self, err_msg):
        self.load_btn.configure(state=tk.NORMAL)
        messagebox.showerror("載入失敗", f"讀取數據失敗: {err_msg}")
        self.progress_text.set(f"載入失敗: {err_msg}")

    def on_tree_double_click(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return
        item_data = self.tree.item(selected_item[0], "values")
        if item_data:
            url = item_data[5]
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            messagebox.showinfo("複製成功", f"商品網址已複製至剪貼簿：\n{url}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MotorAnalysisApp(root)
    root.mainloop()
