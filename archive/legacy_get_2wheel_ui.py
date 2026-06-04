# -*- coding: utf-8 -*-
# 模組與套件匯入
# 以下匯入包含題目要求的標準庫與第三方套件，並以繁體中文註解說明用途。

import asyncio  # 非同步處理
import json  # JSON 編碼/解碼
import math  # 數學運算
import queue  # 線程間或非同步佇列
import random  # 隨機數
import re  # 正規表達式
import sys  # 系統相關操作（包含 stdout 重新配置）
import threading  # 多執行緒
import traceback  # 追蹤例外資訊

from pathlib import Path  # 路徑處理
from datetime import datetime  # 時間處理

from dataclasses import dataclass  # 建立資料類別
from typing import Dict  # 型別提示：回傳字典

import pandas as pd  # 資料處理
import matplotlib  # 圖表設定與後端選擇
# 強制使用非互動式後端，避免在背景執行緒或 headless 環境中發生 GUI 衝突
matplotlib.use("Agg")
# 設定字體與負號顯示，確保中文與負號正常顯示
matplotlib.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "SimHei", "Arial Unicode MS"]
matplotlib.rcParams["axes.unicode_minus"] = False

# GUI 相關（若需在未來加入設定介面）
import tkinter as tk  # 主套件命名為 tk
from tkinter import messagebox  # 彈跳訊息方塊
from tkinter import ttk  # 主題化小工具
from tkinter.scrolledtext import ScrolledText  # 可捲動文字區塊


# 標準輸出重新配置（避免 Windows 主控台因特殊字元或 emoji 崩潰）
try:
    # 在某些 Python 版本/環境中，stdout 可能支援 reconfigure()
    sys.stdout.reconfigure(errors="replace")
except Exception:
    # 若無法重新配置（例如不同的 stdout 類型），則抓取例外但不中斷程序
    pass


# ---------------------------------------------------------------------------
# 核心資料結構：ScrapeConfig
# 使用 dataclass 管理使用者輸入的篩選條件與執行設定
# ---------------------------------------------------------------------------
@dataclass
class ScrapeConfig:
    """
    爬蟲設定資料類別，用以儲存使用者的篩選條件與執行參數。
    所有數值型的輸入（如價格、排氣量）暫以字串儲存，便於保留原始輸入格式與後續解析。
    """
    brand: str = ""           # 廠牌
    cc_min: str = ""          # 最低排氣量（字串）
    cc_max: str = ""          # 最高排氣量（字串）
    price_min: str = ""       # 最低售價（字串）
    price_max: str = ""       # 最高售價（字串）
    keywords: str = ""        # 關鍵字搜尋
    max_pages: int = 10       # 允許抓取的最大頁數（預設 10）
    headless: bool = True     # Playwright / 瀏覽器是否以無頭模式執行（預設 True）
    output_prefix: str = "2wheel"  # 輸出檔案前綴（預設 "2wheel"）


# ---------------------------------------------------------------------------
# 基礎輔助函式
# 1) now_text(): 回傳目前時間字串（%H:%M:%S）
# 2) output_paths(): 依 prefix 與時間戳記產生檔名（CSV 與分析圖）
# ---------------------------------------------------------------------------
def now_text() -> str:
    """
    回傳當前系統時間（小時:分鐘:秒），格式為 %H:%M:%S。
    此函式主要用於日誌或即時顯示時間。
    """
    return datetime.now().strftime("%H:%M:%S")


def output_paths(prefix: str) -> Dict[str, str]:
    """
    根據輸入的前綴字串產生輸出檔案名稱字典。
    範例輸出：
      {
        "csv": "prefix_20250604_143502_listings.csv",
        "main_png": "prefix_20250604_143502_analysis.png"
      }
    使用時間格式：%Y%m%d_%H%M%S
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_name = f"{prefix}_{timestamp}_listings.csv"
    png_name = f"{prefix}_{timestamp}_analysis.png"
    return {"csv": csv_name, "main_png": png_name}


# ---------------------------------------------------------------------------
# 步驟二：防反爬蟲與網址建構邏輯
# 在此區段宣告基礎常數與實作相關輔助函式，用於建構目標網站的查詢網址
# 以及提供安全的數字解析（輸入清理）功能。
# ---------------------------------------------------------------------------

import urllib.parse  # 用於安全地產生查詢字串
from typing import Optional  # 型別提示：可能回傳 None

# 網站基礎搜尋網址（改為 2motor shop 的 allmotor 集合頁面）
BASE_URL = "https://shop.2motor.tw/collections/allmotor/"
SITE_ROOT = "https://shop.2motor.tw"

# 常見的 User-Agent 清單，爬蟲請求時可隨機選擇以降低被封鎖風險
# 包含 Windows 與 macOS 上較新的 Chrome 範例字串
USER_AGENTS = [
    # Windows 10 / Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    # macOS / Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
]


def build_target_url(config: ScrapeConfig, page_num: int) -> str:
    """
    根據傳入的 ScrapeConfig 與頁碼建構目標搜尋 URL。

    主要邏輯：
    1. 使用 2motor shop allmotor collection 路由。
    2. 分頁改用 query 參數 page，避免使用舊版 /page/{page_num}/ 路徑。
    3. 若有 keywords，則一併加上 q 參數。
    4. 這樣可同時支援關鍵字搜尋與分頁。
    """

    try:
        page_val = int(page_num)
    except Exception:
        page_val = 1

    query_params = {}
    if page_val > 1:
        query_params["page"] = page_val
    # 使用 limit 50 取得較多商品卡片；若網站不支援也通常不會有錯誤
    query_params["limit"] = 50

    if getattr(config, "keywords", None):
        query_params["q"] = config.keywords

    query_string = urllib.parse.urlencode(query_params, doseq=True)
    return f"{BASE_URL}?{query_string}" if query_string else BASE_URL


def safe_int(value) -> Optional[int]:
    """
    嘗試將任意輸入轉換為整數。

    規則：
    - 若輸入為 int 或 float，直接轉為 int 並回傳。
    - 若為字串，先移除逗號，然後用正規表達式提取第一組數字，回傳 int。
    - 失敗時回傳 None。
    """
    if value is None:
        return None

    # 整數或浮點數直接處理
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        try:
            return int(value)
        except Exception:
            return None

    # 處理字串型態
    try:
        text = str(value).replace(",", "")
        m = re.search(r"\d+", text)
        if m:
            return int(m.group(0))
    except Exception:
        return None

    return None


def safe_float(value) -> Optional[float]:
    """
    嘗試將任意輸入轉換為浮點數。

    規則：
    - 若輸入為 int 或 float，直接轉為 float 並回傳。
    - 若為字串，先移除逗號，然後用正規表達式提取第一組可能含小數點的數字，回傳 float。
    - 失敗時回傳 None。
    """
    if value is None:
        return None

    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return float(value)

    try:
        text = str(value).replace(",", "")
        m = re.search(r"\d+(?:\.\d+)?", text)
        if m:
            return float(m.group(0))
    except Exception:
        return None

    return None


# ---------------------------------------------------------------------------
# 步驟三：實作 Playwright 核心爬蟲與網頁解析
# 主要函式：fetch_all_data
# - 使用 Playwright 的非同步 API 執行瀏覽器操作
# - 支援偽裝 User-Agent、stealth（若可用）、分頁迴圈、商品卡片解析
# - 透過 log_callback 將進度回報給 GUI
# ---------------------------------------------------------------------------

from typing import Callable, List


async def fetch_all_data(config: ScrapeConfig, log_callback: Callable[[str], None]) -> List[dict]:
    """
    使用 Playwright 非同步驅動抓取貳輪嶼網站上的二手機車資料。

    參數：
      - config: ScrapeConfig 物件，包含篩選條件與爬取選項
      - log_callback: 一個接收字串並顯示於 GUI 的回呼，用於回報進度與錯誤

    回傳：
      - 包含解析後車輛資料的清單（List[dict]），僅回傳價格不為 None 的項目

    注意：此函式為非同步函式，呼叫時請在事件循環中 await 它，或在執行緒中使用 asyncio.run
    """

    # 延遲匯入 Playwright 與 stealth，避免模組在不需要時造成導入錯誤
    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        log_callback(f"[Error] 無法匯入 playwright: {e}")
        return []

    # 嘗試匯入 stealth 工具（非必要，若不存在則繼續但會記錄）
    try:
        from playwright_stealth import stealth_async
        have_stealth = True
    except Exception:
        stealth_async = None
        have_stealth = False

    results: List[dict] = []

    # 啟動 Playwright 並建立 chromium 瀏覽器
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=config.headless)

            # 建立單一 context 與 page，整個流程使用同一個分頁
            ua = random.choice(USER_AGENTS) if USER_AGENTS else None
            context = await browser.new_context(user_agent=ua, ignore_https_errors=True) if ua else await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            if have_stealth and stealth_async is not None:
                try:
                    await stealth_async(page)
                except Exception:
                    log_callback("[Stealth] stealth 初始化失敗，繼續抓取。")

            page_num = 1
            try:
                while page_num <= max(1, int(config.max_pages)):
                    page_url = build_target_url(config, page_num)
                    log_callback(f"[Page {page_num}] 正在導航至: {page_url}")

                    # 導頁（使用更穩定的 domcontentloaded/載入完成等待，而不是 networkidle）
                    try:
                        await page.goto(page_url, timeout=90000, wait_until="domcontentloaded")
                        # 若頁面本身仍在載入資源，可再補一個短暫的 networkidle 嘗試，但不強制失敗
                        try:
                            await page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception:
                            pass
                    except Exception as e:
                        log_callback(f"[Page {page_num}] 導航失敗：{e}")
                        break

                    # 等待最少 DOM 與產品連結出現，避免只抓到 head 但尚未渲染 body 的情況
                    try:
                        await page.wait_for_selector('body', timeout=60000)
                    except Exception:
                        pass
                    try:
                        await page.wait_for_selector('a[href*="/collections/allmotor/products/"]', timeout=15000)
                    except Exception:
                        # 仍然繼續，若沒有產品連結再由備援掃描處理
                        log_callback(f"[Page {page_num}] 尚未偵測到 product link，將進行後續備援掃描。")

                    # 觀察模式：儲存頁面 HTML 與頁面標題，方便分析真實結構
                    try:
                        page_title = await page.title()
                        log_callback(f"[Page {page_num}] Page title: {page_title}")
                        debug_dir = Path("debug_pages")
                        debug_dir.mkdir(parents=True, exist_ok=True)
                        debug_file = debug_dir / f"page_{page_num}.html"
                        html_content = await page.content()
                        debug_file.write_text(html_content, encoding="utf-8")
                        log_callback(f"[Page {page_num}] 已儲存觀察 HTML：{debug_file}")
                    except Exception as e:
                        log_callback(f"[Page {page_num}] 儲存觀察 HTML 失敗：{e}")

                    # 取得商品卡片元素列表，針對 2motor allmotor collection 的產品區塊擴充選取器
                    all_cards = await page.query_selector_all("li.grid__item")
                    cards = []
                    for card in all_cards:
                        if await card.query_selector('a[href*="/collections/allmotor/products/"]'):
                            cards.append(card)
                    if not cards:
                        # fallback: 嘗試用全站 a 標籤連結掃描，找出可能的 product 詳細頁
                        log_callback(f"[Page {page_num}] 未直接找到商品卡片，啟動備援連結掃描。")
                        link_tags = await page.query_selector_all("a[href]")
                        fallback_items = []
                        all_href_entries = []
                        for link in link_tags:
                            try:
                                href = await link.get_attribute("href")
                                if not href:
                                    continue
                                text = (await link.text_content() or "").strip()
                                all_href_entries.append(f"{href}\t{text}")
                                href_lower = href.lower()
                                if ("/collections/allmotor/products/" in href_lower
                                        or "/products/" in href_lower
                                        or "/product/" in href_lower
                                        or "?p=" in href_lower
                                        or "moto" in href_lower
                                        or "scooter" in href_lower
                                        or "機車" in href_lower
                                        or "車款" in href_lower):
                                    title = text or href
                                    url = urllib.parse.urljoin(SITE_ROOT, href)
                                    fallback_items.append({
                                        "title": title,
                                        "price_text": None,
                                        "price": None,
                                        "url": url,
                                        "mileage": None,
                                        "year": None,
                                        "cc": None,
                                        "store": None,
                                        "raw_text": f"fallback link: {title}",
                                    })
                            except Exception:
                                continue

                        try:
                            debug_dir = Path("debug_pages")
                            debug_dir.mkdir(parents=True, exist_ok=True)
                            link_debug_file = debug_dir / f"links_{page_num}.txt"
                            link_debug_file.write_text("\n".join(all_href_entries), encoding="utf-8")
                            log_callback(f"[Page {page_num}] 已儲存所有連結供觀察：{link_debug_file}")
                        except Exception as e:
                            log_callback(f"[Page {page_num}] 儲存連結觀察檔案失敗：{e}")

                        if fallback_items:
                            log_callback(f"[Page {page_num}] 備援連結掃描找到 {len(fallback_items)} 個可能商品項目。")
                            results.extend(fallback_items)
                            break
                        else:
                            log_callback(f"[Page {page_num}] 找不到商品，結束抓取。")
                            break

                    # 逐張卡片解析資料
                    for card in cards:
                        try:
                            # 先抓取卡片內部所有純文字，方便觀察原始內容
                            card_text = await card.text_content()
                            card_text = card_text or ""
                            log_callback(f"--- [Raw Text 偵測] ---\n{card_text.strip()}\n----------------------")

                            # 其他內文抓取（里程、年份、排氣量、店家）
                            raw_text = card_text

                            # Title：先嘗試常見的商品標題 selector，再退回到卡片內第一個連結文字
                            title_el = await card.query_selector('.card-information__text, a.grid-link__title, .card__heading, .product-card__title, h2, h3')
                            if not title_el:
                                title_el = await card.query_selector('a')
                            title = (await title_el.text_content()).strip() if title_el else None

                            # Price text：嘗試多種常見價格欄位，再從 raw_text 解析
                            price_el = await card.query_selector('.price, .amount, .woocommerce-Price-amount, .price-item, .price-item--regular, .price-item--sale, .product-card__price')
                            price_text = (await price_el.text_content()).strip() if price_el else None
                            if not price_text:
                                price_match = re.search(r"NT\$\s*([\d,]+)", raw_text)
                                price_text = price_match.group(0) if price_match else None
                            price = safe_int(price_text) if price_text else None

                            # URL：卡片內第一個 href 連結，轉成完整絕對 URL
                            link_el = await card.query_selector('a[href]')
                            url = await link_el.get_attribute('href') if link_el else None
                            if url:
                                url = urllib.parse.urljoin(SITE_ROOT, url)

                            # 里程：偵測像是 12,345km 或 12345 公里 等格式
                            m = re.search(r"(\d{1,3}(?:,\d{3})*)\s*(?:km|公里)", raw_text, re.IGNORECASE)
                            mileage = int(m.group(1).replace(",", "")) if m else None

                            # 年份：偵測 4 位數年份或"2021年"格式
                            y = re.search(r"\b(19\d{2}|20\d{2})\b", raw_text)
                            year = int(y.group(0)) if y else None

                            # 排氣量：偵測像是 125cc 或 150 c.c. 等格式
                            c = re.search(r"(\d{2,4})\s*(?:cc|c\.c\.|c\.c|c.c)", raw_text, re.IGNORECASE)
                            cc = int(c.group(1)) if c else None

                            # 店家：先嘗試 selector，再從 raw_text 推測
                            store = None
                            store_el = await card.query_selector('.store, .shop, .seller')
                            if store_el:
                                store_text = (await store_el.text_content()).strip()
                                store = store_text or None

                            if not store and "店" in raw_text:
                                # 簡易從 raw_text 裡尋找店家關鍵詞附近的文字
                                store_match = re.search(r"([\u4e00-\u9fff\w\-]{2,10})店", raw_text)
                                if store_match:
                                    store = store_match.group(1)

                            item = {
                                'title': title or "未知",
                                'price_text': price_text,
                                'price': price,
                                'url': url,
                                'mileage': mileage,
                                'year': year,
                                'cc': cc,
                                'store': store,
                                'raw_text': raw_text,
                            }

                            results.append(item)
                            log_callback(f"[Page {page_num}] 解析：{item['title']} / 價格: {item['price']}")
                        except Exception as e:
                            # 單一卡片解析失敗，不中斷整體流程
                            log_callback(f"[Page {page_num}] 卡片解析錯誤：{e}")

                    # 隨機延遲以降低被檢測機率
                    await asyncio.sleep(random.uniform(1.0, 2.5))

                    page_num += 1
            finally:
                # 關閉 context 及瀏覽器
                try:
                    await context.close()
                except Exception:
                    pass
                try:
                    await browser.close()
                except Exception:
                    pass

    except Exception as e:
        log_callback(f"[Error] 爬蟲啟動失敗：{e}\n{traceback.format_exc()}")

    # 回傳原始抓取結果，不過濾缺少價格的項目
    return results


# (先前的簡易測試區塊已移除；執行時請使用下方的 main() 入口以啟動 GUI)


# ---------------------------------------------------------------------------
# 步驟四：實作 Pandas 清理與 6 子圖 Matplotlib 視覺化圖表產出
# 函式：analyze_and_plot
# - 將 data_list 轉為 DataFrame，清理、匯出 CSV，繪製 2x3 子圖並儲存 PNG
# - 支援空資料防錯、欄位檢查、記憶體釋放與回報
# ---------------------------------------------------------------------------

import matplotlib.pyplot as plt


def analyze_and_plot(data_list: List[dict], outputs: Dict[str, str], log_callback: Callable[[str], None]) -> pd.DataFrame:
    """
    解析並視覺化抓取到的二手機車資料。

    參數：
      - data_list: 從爬蟲回傳的字典清單
      - outputs: 包含輸出路徑的字典，需包含 keys: 'csv' 與 'main_png'
      - log_callback: 用於回報日誌給 GUI 的回呼函式

    回傳：
      - Pandas DataFrame（清理後的資料）
    """

    # 先嘗試將 list 轉為 DataFrame
    try:
        df = pd.DataFrame(data_list)
    except Exception as e:
        log_callback(f"[Error] 無法將資料轉為 DataFrame：{e}")
        # 建立空的 DataFrame，確保欄位一致
        df = pd.DataFrame(columns=["title", "price", "url", "mileage", "year", "cc", "store"])

    # 如果沒有任何有效資料，輸出空檔並回傳空 DataFrame
    if df.empty:
        log_callback("[Warning] 沒抓取到任何有效的二手機車數據。")
        # 建立具有預定欄位的空表格（確保欄位存在）
        empty_df = pd.DataFrame(columns=["title", "price", "url", "mileage", "year", "cc", "store"])
        try:
            empty_df.to_csv(outputs.get("csv", "output_listings.csv"), index=False, encoding="utf-8-sig")
            log_callback(f"[Data] 已儲存空 CSV：{outputs.get('csv', 'output_listings.csv')}")
        except Exception as e:
            log_callback(f"[Error] 儲存空 CSV 失敗：{e}")
        return empty_df

    # 確保必要欄位存在，若缺少則補上預設值
    for col in ["title", "price", "url", "mileage", "year", "cc", "store"]:
        if col not in df.columns:
            df[col] = None

    # 轉換型態：price 與 mileage 與 year 與 cc 嘗試轉為數值型
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["mileage"] = pd.to_numeric(df["mileage"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["cc"] = pd.to_numeric(df["cc"], errors="coerce")

    # 依 URL 去除重複項目並重排索引
    df = df.drop_duplicates(subset=["url"]).reset_index(drop=True)

    # 匯出 CSV 檔案（UTF-8 with BOM / utf-8-sig）
    csv_path = outputs.get("csv", "output_listings.csv")
    try:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        log_callback(f"[Data] 已成功儲存 {len(df)} 筆不重複的機車資料至 CSV：{csv_path}")
    except Exception as e:
        log_callback(f"[Error] 儲存 CSV 失敗：{e}")

    # 建立圖表，並將分析結果輸出成 PNG
    create_analysis_chart(df, outputs.get("main_png", "analysis.png"), log_callback)

    return df


def create_analysis_chart(df: pd.DataFrame, png_path: str, log_callback: Callable[[str], None]) -> None:
    """
    依據清理後的 DataFrame 產生 2x3 分析圖表。
    """
    try:
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))

        # 1) 售價分布
        ax = axes[0, 0]
        price_vals = df["price"].dropna()
        if price_vals.empty:
            ax.text(0.5, 0.5, "暫無數據", ha="center", va="center")
        else:
            ax.hist(price_vals, bins=30, color="#3b82f6", edgecolor="black")
            ax.set_title("機車售價分布")
            ax.set_xlabel("售價 (元)")
            ax.set_ylabel("筆數")

        # 2) 里程數分布
        ax = axes[0, 1]
        mileage_vals = df["mileage"].dropna()
        if mileage_vals.empty:
            ax.text(0.5, 0.5, "暫無數據", ha="center", va="center")
        else:
            ax.hist(mileage_vals, bins=30, color="#10b981", edgecolor="black")
            ax.set_title("行駛里程數分布")
            ax.set_xlabel("里程 (km)")
            ax.set_ylabel("筆數")

        # 3) 出廠年份分布
        ax = axes[0, 2]
        year_vals = df["year"].dropna()
        if year_vals.empty:
            ax.text(0.5, 0.5, "暫無數據", ha="center", va="center")
        else:
            ax.hist(year_vals, bins=20, color="#f59e0b", edgecolor="black")
            ax.set_title("出廠年份分布")
            ax.set_xlabel("年份")
            ax.set_ylabel("筆數")

        # 4) 里程數 vs 售價
        ax = axes[1, 0]
        xy = df[["mileage", "price"]].dropna()
        if xy.empty:
            ax.text(0.5, 0.5, "暫無數據", ha="center", va="center")
        else:
            ax.scatter(xy["mileage"], xy["price"], color="#6366f1", alpha=0.6)
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.set_title("里程數 vs 售價")
            ax.set_xlabel("里程 (km)")
            ax.set_ylabel("售價 (元)")

        # 5) 出廠年份 vs 售價
        ax = axes[1, 1]
        xy2 = df[["year", "price"]].dropna()
        if xy2.empty:
            ax.text(0.5, 0.5, "暫無數據", ha="center", va="center")
        else:
            ax.scatter(xy2["year"], xy2["price"], color="#14b8a6", alpha=0.6)
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.set_title("出廠年份 vs 售價")
            ax.set_xlabel("年份")
            ax.set_ylabel("售價 (元)")

        # 6) 店家或車款排行 Top 10
        ax = axes[1, 2]
        store_counts = df["store"].dropna().astype(str)
        store_counts = store_counts[store_counts.str.strip() != ""] if not store_counts.empty else store_counts
        if not store_counts.empty:
            counts = store_counts.value_counts().head(10)
        else:
            title_keys = df["title"].fillna("未知").astype(str).apply(lambda t: t.split()[0] if t.strip() else "未知")
            counts = title_keys.value_counts().head(10)

        if counts.empty:
            ax.text(0.5, 0.5, "暫無數據", ha="center", va="center")
        else:
            counts = counts[::-1]
            ax.barh(counts.index, counts.values, color="#ef4444")
            ax.set_title("店家或車款排行 Top 10")
            ax.set_xlabel("筆數")

        plt.tight_layout()
        fig.savefig(png_path, dpi=180)
        log_callback(f"[Data] 已成功產出分析圖表：{png_path}")
    except Exception as e:
        log_callback(f"[Error] 圖表產生失敗：{e}")
    finally:
        try:
            plt.close('all')
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 步驟五：實作 Threading 與 Queue 異步管線 (Pipeline)
# 函式：run_pipeline
# - 將爬蟲與分析串接為一個可在獨立執行緒中執行的管線
# - 透過傳入的 queue 發送進度、錯誤與完成訊號
# ---------------------------------------------------------------------------


def run_pipeline(config: ScrapeConfig, log_queue: queue.Queue) -> dict:
    """
    在獨立執行緒中執行的同步入口函式，用於啟動非同步爬蟲並接續資料分析。

    流程：
      1. 建立將 log 內容放入 queue 的代理函式 `queue_log`。
      2. 產生 outputs 路徑。
      3. 使用 `asyncio.run` 執行 `fetch_all_data` 取得 data_list。
      4. 呼叫 `analyze_and_plot` 產生 CSV 與圖表。
      5. 成功時向 queue 放入 DONE 訊號；失敗時放入 ERROR 與詳細 traceback。

    傳入：
      - config: 爬蟲設定
      - log_queue: queue.Queue 物件，用於與主執行緒（GUI）溝通

    回傳：
      - dict 包含 outputs 路徑與處理筆數，範例：{"outputs": outputs, "rows": rows}
    """

    # 代理函式：將日誌訊息放入 queue，標記為 LOG
    def queue_log(msg: str):
        try:
            log_queue.put(("LOG", msg))
        except Exception:
            # 無法放入 queue 時，嘗試直接列印作為 fallback
            try:
                print(msg)
            except Exception:
                pass

    outputs = output_paths(config.output_prefix)

    try:
        queue_log(f"管線啟動，輸出路徑：{outputs}")

        # 執行非同步爬蟲並取得資料清單
        data_list = asyncio.run(fetch_all_data(config, queue_log))

        # 呼叫資料分析與繪圖（同步函式）
        df = analyze_and_plot(data_list, outputs, queue_log)

        rows = len(df)

        # 成功完成：放入 DONE 訊號
        log_queue.put(("DONE", f"完成！成功抓取並分析共 {rows} 筆不重複資料。"))

        return {"outputs": outputs, "rows": rows}

    except Exception:
        # 發生致命錯誤：將錯誤資訊放入 queue
        tb = traceback.format_exc()
        try:
            log_queue.put(("ERROR", "執行管線時發生致命錯誤。"))
            log_queue.put(("TRACE", tb))
        except Exception:
            # 仍無法傳送時，至少列印 traceback
            print(tb)
        return {"outputs": outputs, "rows": 0}


# ---------------------------------------------------------------------------
# 步驟六：建立 Tkinter 介面與主程式入口
# - App 類別負責建立 GUI、啟動執行緒並輪詢 log queue
# - main() 負責鎖定工作目錄並啟動 Tkinter 主迴圈
# ---------------------------------------------------------------------------


class App:
    """Tkinter 應用程式主類別，負責建立 UI 與啟動管線執行緒。"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("貳輪嶼二手機車抓取與分析工具")
        self.root.geometry("1100x780")

        # 建立內部 queue 與執行狀態
        self.log_queue: queue.Queue = queue.Queue()
        self.running = False

        # 建立 UI
        self._build_ui()

        # 開始輪詢日誌
        self._poll_logs()

    def _build_ui(self):
        # 上方篩選條件區
        lf = ttk.LabelFrame(self.root, text="篩選條件")
        lf.pack(fill="x", padx=8, pady=6)

        # 廠牌
        ttk.Label(lf, text="廠牌:").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        self.brand_cb = ttk.Combobox(lf, values=["不限", "Kymco 光陽", "SYM 三陽", "Yamaha 山葉", "Honda 本田", "Gogoro", "Suzuki 台鈴"], state="readonly")
        self.brand_cb.current(0)
        self.brand_cb.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        # 排氣量範圍
        ttk.Label(lf, text="最低排氣量 (cc):").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        self.cc_min_entry = ttk.Entry(lf, width=10)
        self.cc_min_entry.grid(row=0, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(lf, text="最高排氣量 (cc):").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        self.cc_max_entry = ttk.Entry(lf, width=10)
        self.cc_max_entry.grid(row=0, column=5, padx=6, pady=6, sticky="w")

        # 價格範圍
        ttk.Label(lf, text="最低預算 (元):").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        self.price_min_entry = ttk.Entry(lf, width=12)
        self.price_min_entry.grid(row=1, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(lf, text="最高預算 (元):").grid(row=1, column=2, padx=6, pady=6, sticky="w")
        self.price_max_entry = ttk.Entry(lf, width=12)
        self.price_max_entry.grid(row=1, column=3, padx=6, pady=6, sticky="w")

        # 關鍵字
        ttk.Label(lf, text="關鍵字搜尋:").grid(row=1, column=4, padx=6, pady=6, sticky="w")
        self.keywords_entry = ttk.Entry(lf, width=20)
        self.keywords_entry.grid(row=1, column=5, padx=6, pady=6, sticky="w")

        # 最大頁數與輸出前綴
        ttk.Label(lf, text="最大允許頁數:").grid(row=2, column=0, padx=6, pady=6, sticky="w")
        self.max_pages_entry = ttk.Entry(lf, width=8)
        self.max_pages_entry.insert(0, "10")
        self.max_pages_entry.grid(row=2, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(lf, text="輸出檔案前綴:").grid(row=2, column=2, padx=6, pady=6, sticky="w")
        self.output_prefix_entry = ttk.Entry(lf, width=16)
        self.output_prefix_entry.insert(0, "2wheel")
        self.output_prefix_entry.grid(row=2, column=3, padx=6, pady=6, sticky="w")

        # 中間控制按鈕區
        ctrl = ttk.Frame(self.root)
        ctrl.pack(fill="x", padx=8, pady=6)

        self.bg_var = tk.BooleanVar(value=True)
        self.bg_check = ttk.Checkbutton(ctrl, text="背景執行", variable=self.bg_var)
        self.bg_check.pack(side="left", padx=6)

        # 開始與清除按鈕
        self.start_btn = ttk.Button(ctrl, text="開始抓取", command=self.start)
        self.start_btn.pack(side="right", padx=6)

        self.clear_btn = ttk.Button(ctrl, text="清除紀錄", command=self._clear_logs)
        self.clear_btn.pack(side="right", padx=6)

        # 下方執行紀錄區
        lf2 = ttk.LabelFrame(self.root, text="執行紀錄")
        lf2.pack(fill="both", expand=True, padx=8, pady=6)

        self.log_text = ScrolledText(lf2, font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True)

    def _clear_logs(self):
        self.log_text.delete("1.0", "end")

    def start(self):
        # 讀取 UI 欄位並建立 ScrapeConfig
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

        # 禁用按鈕並標記為運行中
        self.start_btn.config(state="disabled")
        self.running = True

        # 啟動背景執行緒運行 run_pipeline
        t = threading.Thread(target=run_pipeline, args=(cfg, self.log_queue), daemon=True)
        t.start()

    def _poll_logs(self):
        # 週期性輪詢 queue，並更新 UI
        try:
            while not self.log_queue.empty():
                tag, msg = self.log_queue.get_nowait()
                ts = now_text()
                if tag in ("LOG", "TRACE"):
                    self.log_text.insert("end", f"[{ts}] {msg}\n")
                    self.log_text.see("end")
                elif tag in ("DONE", "ERROR"):
                    self.log_text.insert("end", f"[{ts}] {tag}: {msg}\n")
                    self.log_text.see("end")
                    # 結束運行後恢復按鈕
                    self.running = False
                    self.start_btn.config(state="normal")
                else:
                    # 其他訊號也一併印出
                    self.log_text.insert("end", f"[{ts}] {tag}: {msg}\n")
                    self.log_text.see("end")
        except Exception:
            pass
        finally:
            # 每 120ms 再次輪詢
            self.root.after(120, self._poll_logs)


def main():
    import os

    target_dir = r"C:\Users\LINia\Desktop\二手機車期中報告"
    os.makedirs(target_dir, exist_ok=True)
    os.chdir(target_dir)
    print(f"當前工作目錄已切換至: {os.getcwd()}")

    try:
        print("[DEBUG] 正在建立 Tk 根視窗...")
        root = tk.Tk()
        print("[DEBUG] Tk 根視窗已建立")
        
        print("[DEBUG] 正在建立 App 實例...")
        app = App(root)
        print("[DEBUG] App 實例已建立")
        
        # 強制視窗顯示在前景
        print("[DEBUG] 強制視窗顯示在前景...")
        root.deiconify()
        root.lift()
        root.focus_force()
        root.update()
        print("[DEBUG] 視窗已顯示")
        
        print("[DEBUG] 正在進入 mainloop...")
        root.mainloop()
        print("[DEBUG] mainloop 已退出")
    except KeyboardInterrupt:
        print("KeyboardInterrupt 已接收，正在關閉 GUI...")
    except Exception as e:
        print(f"[ERROR] 執行過程中出現異常：{e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    main()


