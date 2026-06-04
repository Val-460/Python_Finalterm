# -*- coding: utf-8 -*-
import os
import threading
import queue
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import webbrowser

from .config import ScrapeConfig, now_text
from .pipeline import run_pipeline


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("貳輪嶼二手機車抓取與分析工具")
        self.root.geometry("1100x780")
        self.log_queue: queue.Queue = queue.Queue()
        self.running = False
        self.last_html_report: str | None = None
        self._build_ui()
        self._poll_logs()

    def _build_ui(self):
        lf = ttk.LabelFrame(self.root, text="篩選條件")
        lf.pack(fill="x", padx=8, pady=6)

        ttk.Label(lf, text="廠牌:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.brand_cb = ttk.Combobox(lf, values=["不限", "Kymco 光陽", "SYM 三陽", "Yamaha 山葉", "Honda 本田", "Gogoro", "Suzuki 台鈴"], state="readonly")
        self.brand_cb.current(0)
        self.brand_cb.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(lf, text="最低排氣量 (cc):").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        self.cc_min_entry = ttk.Entry(lf, width=10)
        self.cc_min_entry.grid(row=0, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(lf, text="最高排氣量 (cc):").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        self.cc_max_entry = ttk.Entry(lf, width=10)
        self.cc_max_entry.grid(row=0, column=5, padx=6, pady=6, sticky="w")

        ttk.Label(lf, text="最低預算 (元):").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        self.price_min_entry = ttk.Entry(lf, width=12)
        self.price_min_entry.grid(row=1, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(lf, text="最高預算 (元):").grid(row=1, column=2, padx=6, pady=6, sticky="w")
        self.price_max_entry = ttk.Entry(lf, width=12)
        self.price_max_entry.grid(row=1, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(lf, text="關鍵字搜尋:").grid(row=1, column=4, padx=6, pady=6, sticky="w")
        self.keywords_entry = ttk.Entry(lf, width=20)
        self.keywords_entry.grid(row=1, column=5, padx=6, pady=6, sticky="w")

        ttk.Label(lf, text="最大允許頁數:").grid(row=2, column=0, padx=6, pady=6, sticky="w")
        self.max_pages_entry = ttk.Entry(lf, width=8)
        self.max_pages_entry.insert(0, "10")
        self.max_pages_entry.grid(row=2, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(lf, text="輸出檔案前綴:").grid(row=2, column=2, padx=6, pady=6, sticky="w")
        self.output_prefix_entry = ttk.Entry(lf, width=16)
        self.output_prefix_entry.insert(0, "2wheel")
        self.output_prefix_entry.grid(row=2, column=3, padx=6, pady=6, sticky="w")

        ctrl = ttk.Frame(self.root)
        ctrl.pack(fill="x", padx=8, pady=6)

        self.bg_var = tk.BooleanVar(value=True)
        self.bg_check = ttk.Checkbutton(ctrl, text="背景執行", variable=self.bg_var)
        self.bg_check.pack(side="left", padx=6)

        self.start_btn = ttk.Button(ctrl, text="開始抓取", command=self.start)
        self.start_btn.pack(side="right", padx=6)

        self.open_html_btn = ttk.Button(ctrl, text="開啟 HTML 報表", command=self.open_html_report, state="disabled")
        self.open_html_btn.pack(side="right", padx=6)

        self.clear_btn = ttk.Button(ctrl, text="清除紀錄", command=self._clear_logs)
        self.clear_btn.pack(side="right", padx=6)

        lf2 = ttk.LabelFrame(self.root, text="執行紀錄")
        lf2.pack(fill="both", expand=True, padx=8, pady=6)

        self.log_text = ScrolledText(lf2, font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True)

    def _clear_logs(self):
        self.log_text.delete("1.0", "end")
        self.last_html_report = None
        self.open_html_btn.config(state="disabled")

    def start(self):
        brand_val = self.brand_cb.get()
        brand = "" if brand_val == "不限" else brand_val

        cfg = ScrapeConfig(
            brand=brand,
            cc_min=self.cc_min_entry.get().strip(),
            cc_max=self.cc_max_entry.get().strip(),
            price_min=self.price_min_entry.get().strip(),
            price_max=self.price_max_entry.get().strip(),
            keywords=self.keywords_entry.get().strip(),
            max_pages=int(self.max_pages_entry.get().strip() or 10),
            headless=bool(self.bg_var.get()),
            output_prefix=self.output_prefix_entry.get().strip() or "2wheel",
        )

        self.start_btn.config(state="disabled")
        self.open_html_btn.config(state="disabled")
        self.last_html_report = None
        self.running = True

        t = threading.Thread(target=run_pipeline, args=(cfg, self.log_queue), daemon=True)
        t.start()

    def _poll_logs(self):
        try:
            while not self.log_queue.empty():
                tag, msg = self.log_queue.get_nowait()
                ts = now_text()
                if tag == "HTML_REPORT":
                    self.last_html_report = msg
                    self.open_html_btn.config(state="normal")
                    self.log_text.insert("end", f"[{ts}] HTML 報表已生成：{msg}\n")
                    self.log_text.see("end")
                elif tag in ("LOG", "TRACE"):
                    self.log_text.insert("end", f"[{ts}] {msg}\n")
                    self.log_text.see("end")
                elif tag in ("DONE", "ERROR"):
                    self.log_text.insert("end", f"[{ts}] {tag}: {msg}\n")
                    self.log_text.see("end")
                    self.running = False
                    self.start_btn.config(state="normal")
                else:
                    self.log_text.insert("end", f"[{ts}] {tag}: {msg}\n")
                    self.log_text.see("end")
        except Exception:
            pass
        finally:
            self.root.after(120, self._poll_logs)

    def open_html_report(self):
        if not self.last_html_report:
            self.log_text.insert("end", f"[{now_text()}] ERROR: 尚未生成 HTML 報表。\n")
            self.log_text.see("end")
            return

        if not os.path.exists(self.last_html_report):
            self.log_text.insert("end", f"[{now_text()}] ERROR: HTML 報表不存在：{self.last_html_report}\n")
            self.log_text.see("end")
            return

        try:
            webbrowser.open_new_tab(f"file:///{os.path.abspath(self.last_html_report)}")
            self.log_text.insert("end", f"[{now_text()}] 已開啟 HTML 報表：{self.last_html_report}\n")
            self.log_text.see("end")
        except Exception as e:
            self.log_text.insert("end", f"[{now_text()}] 開啟 HTML 報表失敗：{e}\n")
            self.log_text.see("end")


def main():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    target_dir = project_root
    target_dir.mkdir(parents=True, exist_ok=True)
    os.chdir(target_dir)
    print(f"當前工作目錄已切換至: {os.getcwd()}")

    root = tk.Tk()
    app = App(root)
    
    # 強制視窗顯示在前景
    root.deiconify()
    root.lift()
    root.focus_force()
    root.update()
    
    root.mainloop()
