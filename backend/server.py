# =====================================================================
# 1. 基礎引用模組
# =====================================================================
import os
import sys
import asyncio
import re
import datetime
import logging
from typing import List, Dict, Any, Optional
import requests
from concurrent.futures import ThreadPoolExecutor

import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import pandas as pd
import matplotlib
# 重要：設定 Matplotlib 使用 Agg 無頭後端，避免在雲端 (Render/Docker) 執行時因 GUI 崩潰
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設定日誌
logger = logging.getLogger("server")
logging.basicConfig(level=logging.INFO)

# =====================================================================
# 2. 資料庫與路徑設定 (DATABASE & CONFIG)
# =====================================================================
# 靜態與圖表目錄設定與專案根目錄定義
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# 支援 Vercel 唯讀環境下的靜態資源目錄
if os.getenv("VERCEL") == "1":
    STATIC_DIR = "/tmp/static"
else:
    STATIC_DIR = os.path.join(BASE_DIR, "static")

CHARTS_DIR = os.path.join(STATIC_DIR, "charts")

RAW_DATABASE_URL = os.getenv("DATABASE_URL")
if RAW_DATABASE_URL:
    # 自動相容 Render PostgreSQL 連線字串 (postgres:// -> postgresql+psycopg2://)
    if RAW_DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = RAW_DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    elif RAW_DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)
    else:
        DATABASE_URL = RAW_DATABASE_URL
else:
    # 支援 Vercel 唯讀環境下的 SQLite 寫入
    if os.getenv("VERCEL") == "1":
        db_path = "/tmp/local_dev.db"
        DATABASE_URL = f"sqlite:///{db_path}"
    else:
        # 本地端預設 SQLite，移至專案根目錄的 db/ 資料夾中，避免檔案散落
        DB_DIR = os.path.join(PROJECT_ROOT, "db")
        os.makedirs(DB_DIR, exist_ok=True)
        db_path = os.path.join(DB_DIR, "local_dev.db")
        DATABASE_URL = f"sqlite:///{db_path.replace(os.sep, '/')}"

# 初始化 SQLAlchemy
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 全局爬蟲狀態
CRAWL_STATUS = {
    "is_running": False,
    "current_page": 0,
    "total_pages": 16,
    "scraped_count": 0,
    "status": "idle",
    "message": ""
}

# 取得資料庫 Session 依賴注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================================
# 3. 資料庫 ORM 模型 (MODELS)
# =====================================================================
class Product(Base):
    """商品資料表"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False, index=True)
    url = Column(String, unique=True, nullable=False)
    img_url = Column(String, nullable=True)
    original_price = Column(Float, nullable=False, default=0.0)
    current_price = Column(Float, nullable=False, default=0.0)
    discount_rate = Column(Float, nullable=False, default=0.0)
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # 新增欄位
    year = Column(Integer, nullable=False, default=0)
    mileage = Column(Float, nullable=False, default=0.0)
    location = Column(String, nullable=True)
    displacement = Column(Integer, nullable=False, default=0)
    brand = Column(String, nullable=True)
    cp_index = Column(Float, nullable=False, default=1.0)
    cp_label = Column(String, nullable=True, default="合理")

class ScrapeLog(Base):
    """爬蟲歷史日誌表"""
    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, nullable=False)  # "SUCCESS" 或 "FAILED"
    products_count = Column(Integer, default=0)
    message = Column(String, nullable=True)

# =====================================================================
# 4. Pydantic 資料驗證 Schema (SCHEMAS)
# =====================================================================
class ProductResponse(BaseModel):
    id: int
    title: str
    url: str
    img_url: Optional[str] = None
    original_price: float
    current_price: float
    discount_rate: float
    scraped_at: datetime.datetime
    year: int
    mileage: float
    location: Optional[str] = None
    displacement: int
    brand: Optional[str] = None
    cp_index: float
    cp_label: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ScrapeLogResponse(BaseModel):
    id: int
    timestamp: datetime.datetime
    status: str
    products_count: int
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AnalysisSummary(BaseModel):
    total_count: int
    avg_original_price: float
    avg_current_price: float
    avg_discount_rate: float
    max_discount_rate: float
    min_price: float
    max_price: float
    price_distribution: Dict[str, int]
    avg_mileage: float
    value_choices_count: int

class ChartResponse(BaseModel):
    histogram_url: str
    scatter_url: str
    brand_pie_url: str

class CrawlTriggerResponse(BaseModel):
    status: str
    scraped_count: int
    message: str

# =====================================================================
# 5. Playwright 異步爬蟲邏輯 (CRAWLER)
# =====================================================================
def parse_price(price_str: str) -> float:
    """從價格字串中提取數字金額"""
    if not price_str:
        return 0.0
    cleaned = price_str.replace(",", "").strip()
    match = re.search(r'\d+', cleaned)
    return float(match.group()) if match else 0.0

def parse_info_from_title(title: str) -> dict:
    """
    從商品標題中提取門市、年份、品牌與排氣量 (CC數)
    範例：【新北樹林店】2019 山葉 JOG SWEET 115 #8929
    """
    res = {
        "location": "其他",
        "year": 0,
        "brand": "其他",
        "displacement": 0
    }
    if not title:
        return res

    # 1. 門市解析
    loc_match = re.search(r'[【\[](.*?)[】\]]', title)
    if loc_match:
        res["location"] = loc_match.group(1).strip()
        clean_title = title.replace(loc_match.group(0), "")
    else:
        clean_title = title

    # 2. 年份解析
    year_match = re.search(r'\b(20\d\d|19\d\d)\b', clean_title)
    if year_match:
        res["year"] = int(year_match.group(1))
        clean_title = clean_title.replace(year_match.group(0), "")

    # 3. 品牌解析
    brand_map = {
        "山葉": ["山葉", "YAMAHA", "yamaha", "yamah"],
        "三陽": ["三陽", "SYM", "sym"],
        "光陽": ["光陽", "KYMCO", "kymco"],
        "摩特動力": ["PGO", "pgo", "摩特動力"],
        "鈴木": ["SUZUKI", "suzuki", "鈴木", "台鈴"],
        "本田": ["HONDA", "honda", "本田"],
        "偉士牌": ["VESPA", "vespa", "偉士牌"],
        "宏佳騰": ["宏佳騰", "AEON", "aeon"],
        "睿能": ["GOGORO", "gogoro", "睿能"],
        "川崎": ["KAWASAKI", "kawasaki", "川崎"]
    }
    for b_name, aliases in brand_map.items():
        for alias in aliases:
            if alias.lower() in title.lower():
                res["brand"] = b_name
                break
        if res["brand"] != "其他":
            break

    # 4. 排氣量 (displacement) 解析
    clean_title = re.sub(r'#\d+', '', clean_title)  # 移除車號
    cc_matches = re.findall(r'\b(\d{2,4})\s*(?:cc|CC)?\b', clean_title)
    for cc_str in cc_matches:
        cc_val = int(cc_str)
        if 50 <= cc_val <= 1800 and cc_val != res["year"]:
            res["displacement"] = cc_val
            break

    return res

def clean_mileage_val(mileage_str: str) -> float:
    """
    清洗里程數字串，支援 "35,XXX"、"1.2萬"、"2.5W" 等各式格式，統一轉換為 float。
    """
    if not mileage_str:
        return 0.0
    
    mileage_str = mileage_str.upper().strip()
    
    # 1. 偵測是否含有萬或 W 單位
    has_wan = False
    if "萬" in mileage_str or "W" in mileage_str:
        has_wan = True
        # 移除非數字、小數點和 X 以外的字元
        cleaned = re.sub(r'[^\d.X-]', '', mileage_str)
    else:
        # 移除非數字和 X 以外的字元
        cleaned = re.sub(r'[^\dX-]', '', mileage_str)
        
    if not cleaned:
        return 0.0
        
    # 2. 將 X 替換為 0
    cleaned = cleaned.replace("X", "0")
    
    try:
        val = float(cleaned)
        if has_wan:
            val *= 10000.0
        return val
    except ValueError:
        return 0.0


def fetch_detail_mileage(url: str) -> float:
    """透過 Requests 抓取機車詳情頁並正則解析里程數"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            # 尋找 HTML 原始碼中如 ◉ 里程數：約 35,XXX 公里 之特徵
            match = re.search(r'里程數[：:][約]?\s*([\d,X+]+)\s*公里', resp.text)
            if match:
                return clean_mileage_val(match.group(1))
    except Exception as e:
        logger.error(f"抓取里程數失敗 {url}: {e}")
    return 0.0

def scrape_products(max_pages: Optional[int] = None, cached_items: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    """以 Requests + BeautifulSoup 爬取貳輪部品電商所有頁面的商品數據，並以多線程抓取新上架車輛的里程"""
    from bs4 import BeautifulSoup
    import time
    import random
    products = []
    base_url = "https://shop.2motor.tw"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    page_num = 1
    while True:
        if max_pages and page_num > max_pages:
            logger.info(f"已達到設定的最大頁面限制 ({max_pages})，停止爬取。")
            break
            
        # 更新全局爬蟲狀態
        CRAWL_STATUS["is_running"] = True
        CRAWL_STATUS["current_page"] = page_num
        CRAWL_STATUS["scraped_count"] = len(products)
        CRAWL_STATUS["status"] = f"正在掃描列表第 {page_num} 頁"

        url = f"{base_url}/collections/all?page={page_num}"
        logger.info(f"正在爬取第 {page_num} 頁: {url}")
        try:
            resp = session.get(url, timeout=20)
            if resp.status_code != 200:
                logger.info(f"在第 {page_num} 頁請求返回 {resp.status_code}，可能已達末頁，結束爬取。")
                break
                
            soup = BeautifulSoup(resp.text, "html.parser")
            # Shopify 商品卡片選取器
            cards = soup.select(".grid__item, .product-card, .grid-view-item, .product-item, .card")
            if not cards:
                cards = soup.select("a[href*='/products/']")
            
            if not cards:
                logger.info(f"在第 {page_num} 頁未找到商品卡片，可能已達末頁，結束爬取。")
                break

            added_before = len(products)
            seen_urls = set()
            
            for card in cards:
                link_elem = card.select_one("a[href*='/products/']")
                if not link_elem:
                    href = card.get("href")
                    if href and "/products/" in href:
                        link_elem = card
                    else:
                        continue
                        
                href = link_elem.get("href")
                if not href:
                    continue
                full_url = href if href.startswith("http") else f"{base_url}{href}"
                
                if full_url in seen_urls or full_url in [p['url'] for p in products]:
                    continue
                    
                # 解析商品名稱
                title = ""
                title_elem = card.select_one(".card-information__text, .card__heading, .grid-view-item__title, .product-card__title, .title, h3")
                if title_elem:
                    title = title_elem.get_text()
                if not title or title.strip() == "":
                    title = link_elem.get_text()
                title = title.strip()
                if not title:
                    continue
                    
                # 解析商品圖片
                img_elem = card.select_one("img")
                img_url = ""
                if img_elem:
                    img_url = img_elem.get("src")
                    if not img_url or img_url.startswith("data:"):
                        img_url = img_elem.get("data-src")
                    if not img_url or img_url.startswith("data:"):
                        img_url = img_elem.get("srcset")
                        if img_url:
                            img_url = img_url.split(",")[0].split(" ")[0]
                if img_url and img_url.startswith("//"):
                    img_url = f"https:{img_url}"

                # 解析價格
                price_elements = card.select(".price-item, [class*='price'], .price")
                prices_found = []
                for pe in price_elements:
                    text = pe.get_text()
                    p_val = parse_price(text)
                    if p_val > 0:
                        prices_found.append(p_val)
                prices_found = sorted(list(set(prices_found)))
                
                original_price = 0.0
                current_price = 0.0
                if len(prices_found) >= 2:
                    original_price = max(prices_found)
                    current_price = min(prices_found)
                elif len(prices_found) == 1:
                    original_price = prices_found[0]
                    current_price = prices_found[0]
                else:
                    card_text = card.get_text()
                    matches = re.findall(r'NT\$\s*[\d,]+|\$\s*[\d,]+|\d[\d,]*(?=\s*元)', card_text)
                    for m in matches:
                        p_val = parse_price(m)
                        if p_val > 0:
                            prices_found.append(p_val)
                    prices_found = sorted(list(set(prices_found)))
                    if len(prices_found) >= 2:
                        original_price = max(prices_found)
                        current_price = min(prices_found)
                    elif len(prices_found) == 1:
                        original_price = prices_found[0]
                        current_price = prices_found[0]

                discount_rate = 0.0
                if original_price > 0:
                    discount_rate = (original_price - current_price) / original_price

                # 從標題解析屬性
                parsed_info = parse_info_from_title(title)

                products.append({
                    "title": title,
                    "url": full_url,
                    "img_url": img_url if img_url else None,
                    "original_price": original_price,
                    "current_price": current_price,
                    "discount_rate": round(discount_rate, 4),
                    "year": parsed_info["year"],
                    "location": parsed_info["location"],
                    "brand": parsed_info["brand"],
                    "displacement": parsed_info["displacement"]
                })
                seen_urls.add(full_url)
            
            added_after = len(products)
            if added_after == added_before:
                logger.info(f"在第 {page_num} 頁沒有成功新增任何商品，可能已達末頁，結束爬取。")
                break
                
            page_num += 1
            time.sleep(random.uniform(0.5, 1.2))
        except Exception as e:
            logger.error(f"爬取第 {page_num} 頁時發生錯誤: {str(e)}")
            break

    # 第二層：多線程抓取全新商品里程數
    to_fetch_indices = []
    for idx, item in enumerate(products):
        url = item["url"]
        if cached_items and url in cached_items:
            item["mileage"] = cached_items[url]
        else:
            item["mileage"] = 0.0
            to_fetch_indices.append(idx)
            
    total_to_fetch = len(to_fetch_indices)
    if total_to_fetch > 0:
        logger.info(f"偵測到 {total_to_fetch} 筆全新上架商品，啟動多線程爬取里程...")
        
        def worker(idx):
            url = products[idx]["url"]
            mileage = fetch_detail_mileage(url)
            products[idx]["mileage"] = mileage
            
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, idx) for idx in to_fetch_indices]
            completed_count = 0
            for fut in futures:
                fut.result()
                completed_count += 1
                CRAWL_STATUS["status"] = f"爬取里程數: {completed_count}/{total_to_fetch}"
                CRAWL_STATUS["scraped_count"] = len(products)

    return products

# =====================================================================
# 6. Pandas 統計分析與數據清洗 (SERVICES: ANALYSIS & CP MODEL)
# =====================================================================
def calculate_cp_values(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    使用 Pandas 進行品牌、排氣量、年份分組，
    計算組內中位數價格與里程，並套用相對性性價比 CP 指數模型，
    最後分配 "超值"、"合理"、"偏高" 標籤。
    """
    if not items:
        return []
    
    df = pd.DataFrame(items)
    df["mileage"] = df["mileage"].fillna(0.0)
    df["current_price"] = df["current_price"].fillna(0.0)
    
    # 分組鍵：品牌、排氣量、年份
    group_cols = ["brand", "displacement", "year"]
    
    # 計算組內中位數價格與中位數里程
    # 使用 transform 可產生與原 dataframe 等長之 Series
    grouped = df.groupby(group_cols)
    df["median_price"] = grouped["current_price"].transform("median")
    df["median_mileage"] = grouped["mileage"].transform("median")
    
    # 計算相對價格比率（防止價格為 0）
    price_ratio = df["median_price"] / df["current_price"].replace(0, 1.0)
    price_ratio = price_ratio.fillna(1.0)
    
    # 計算相對里程比率（加入 5000 公里平滑常數防止除以 0，並平抑極低里程車權重）
    mileage_ratio = (df["median_mileage"] + 5000.0) / (df["mileage"] + 5000.0)
    
    # 計算 CP 值指數
    df["cp_index"] = price_ratio * mileage_ratio
    
    # 分配 CP 值標籤
    df["cp_label"] = "合理"
    df.loc[df["cp_index"] >= 1.10, "cp_label"] = "超值"
    df.loc[df["cp_index"] < 0.90, "cp_label"] = "偏高"
    
    # 四捨五入 CP 指數
    df["cp_index"] = df["cp_index"].round(4)
    
    # 轉回 Dict list
    return df.to_dict(orient="records")

def analyze_products(db_products: List[Product]) -> Dict[str, Any]:
    """使用 Pandas 進行資料清洗與數值分析統計，提供二手機車特有指標"""
    if not db_products:
        return {
            "total_count": 0, "avg_original_price": 0.0, "avg_current_price": 0.0,
            "avg_discount_rate": 0.0, "max_discount_rate": 0.0, "min_price": 0.0,
            "max_price": 0.0, "price_distribution": {},
            "avg_mileage": 0.0, "value_choices_count": 0
        }
    
    data = [{
        "original_price": p.original_price,
        "current_price": p.current_price,
        "discount_rate": p.discount_rate,
        "mileage": p.mileage,
        "cp_label": p.cp_label
    } for p in db_products]
    df = pd.DataFrame(data)
    
    # 清洗掉異常價格
    df = df[(df["original_price"] > 0) & (df["current_price"] > 0)]
    if df.empty:
        return {
            "total_count": 0, "avg_original_price": 0.0, "avg_current_price": 0.0,
            "avg_discount_rate": 0.0, "max_discount_rate": 0.0, "min_price": 0.0,
            "max_price": 0.0, "price_distribution": {},
            "avg_mileage": 0.0, "value_choices_count": 0
        }

    total_count = len(df)
    avg_orig = float(df["original_price"].mean())
    avg_curr = float(df["current_price"].mean())
    avg_disc = float(df["discount_rate"].mean())
    max_disc = float(df["discount_rate"].max())
    min_price = float(df["current_price"].min())
    max_price = float(df["current_price"].max())
    avg_mileage = float(df["mileage"].mean())
    value_choices_count = int((df["cp_label"] == "超值").sum())

    # 二手機車專用價格區間分組
    bins = [0, 30000, 50000, 70000, 100000, float('inf')]
    labels = ["$3萬以下", "$3-5萬", "$5-7萬", "$7-10萬", "$10萬以上"]
    df["price_group"] = pd.cut(df["current_price"], bins=bins, labels=labels)
    group_counts = df["price_group"].value_counts().to_dict()
    price_dist = {str(k): int(v) for k, v in group_counts.items()}

    return {
        "total_count": total_count,
        "avg_original_price": round(avg_orig, 2),
        "avg_current_price": round(avg_curr, 2),
        "avg_discount_rate": round(avg_disc, 4),
        "max_discount_rate": round(max_disc, 4),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "price_distribution": price_dist,
        "avg_mileage": round(avg_mileage, 1),
        "value_choices_count": value_choices_count
    }

# =====================================================================
# 7. Matplotlib 圖表可視化生成 (SERVICES: CHART)
# =====================================================================
def generate_charts(db_products: List[Product]) -> Dict[str, str]:
    """生成價格直方圖、里程與價格散佈圖、熱門品牌圓餅圖"""
    os.makedirs(CHARTS_DIR, exist_ok=True)
    
    hist_filename = "price_histogram.png"
    scatter_filename = "discount_scatter.png"
    brand_pie_filename = "brand_pie.png"
    
    hist_path = os.path.join(CHARTS_DIR, hist_filename)
    scatter_path = os.path.join(CHARTS_DIR, scatter_filename)
    brand_pie_path = os.path.join(CHARTS_DIR, brand_pie_filename)

    if not db_products:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, "No Data", ha="center", va="center", fontsize=14)
        plt.savefig(hist_path)
        plt.savefig(scatter_path)
        plt.savefig(brand_pie_path)
        plt.close('all')
        return {"histogram": hist_filename, "scatter": scatter_filename, "brand_pie": brand_pie_filename}

    # 擷取繪圖資料
    data = [{
        "current_price": p.current_price,
        "original_price": p.original_price,
        "discount_rate": p.discount_rate,
        "brand": p.brand if p.brand else "其他",
        "mileage": p.mileage,
        "cp_label": p.cp_label
    } for p in db_products]
    df = pd.DataFrame(data)

    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Arial', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False

    # 1. 二手機車價格分布直方圖
    plt.figure(figsize=(10, 6))
    prices_in_ten_thousand = df["current_price"] / 10000.0
    plt.hist(prices_in_ten_thousand, bins=15, color="#00adb5", edgecolor="white", alpha=0.8)
    plt.title("二手機車價格分布直方圖", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("現價 (萬元 NT$)", fontsize=12)
    plt.ylabel("車輛數量 (台)", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(hist_path, dpi=150)
    plt.close()

    # 2. 里程與價格分佈散佈圖 (按 CP 值分類標色)
    plt.figure(figsize=(10, 6))
    colors_map = {"超值": "#2ecc71", "合理": "#3498db", "偏高": "#e74c3c"}
    
    for label, color in colors_map.items():
        subset = df[df["cp_label"] == label]
        if not subset.empty:
            plt.scatter(
                subset["mileage"], 
                subset["current_price"] / 10000.0, 
                color=color, 
                label=f"CP值: {label}", 
                alpha=0.7, 
                s=40
            )
            
    plt.title("機車里程與價格分佈散佈圖 (性價比分類)", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("里程數 (公里)", fontsize=12)
    plt.ylabel("價格 (萬元 NT$)", fontsize=12)
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig(scatter_path, dpi=150)
    plt.close()

    # 3. 品牌圓餅圖
    plt.figure(figsize=(10, 6))
    brand_counts = df["brand"].value_counts()
    if len(brand_counts) > 5:
        top5 = brand_counts.head(5)
        others_count = brand_counts.iloc[5:].sum()
        top5_with_others = pd.concat([top5, pd.Series({"其他": others_count})])
    else:
        top5_with_others = brand_counts
    colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99','#c2c2f0','#ffb3e6']
    plt.pie(
        top5_with_others, labels=top5_with_others.index, autopct='%1.1f%%',
        startangle=140, colors=colors[:len(top5_with_others)], textprops={'fontsize': 11}
    )
    plt.title("在售二手機車品牌市佔率 (Top 5)", fontsize=14, fontweight="bold", pad=15)
    plt.tight_layout()
    plt.savefig(brand_pie_path, dpi=150)
    plt.close()

    return {"histogram": hist_filename, "scatter": scatter_filename, "brand_pie": brand_pie_filename}

def get_model_summary(db_products: List[Any]) -> pd.DataFrame:
    if not db_products:
        return pd.DataFrame(columns=[
            "車款名稱", "廠牌", "上架數量", "平均價格", "最低價格", "最高價格", "平均里程", "出廠年份區間", "排氣量(cc)", "上架店家"
        ])

    data = []
    for p in db_products:
        clean_title = p.title
        clean_title = re.sub(r'[【\[](.*?)[】\]]', '', clean_title).strip()
        clean_title = re.sub(r'#\s*\d+', '', clean_title).strip()
        
        data.append({
            "title": clean_title,
            "brand": p.brand or "未知廠牌",
            "price": p.current_price,
            "mileage": p.mileage,
            "year": p.year,
            "displacement": p.displacement,
            "location": p.location or "未知店家"
        })
    df = pd.DataFrame(data)

    summary_data = []
    for model_name, group in df.groupby("title"):
        brand = group["brand"].iloc[0] if not group["brand"].empty else "未知廠牌"
        cc = group["displacement"].iloc[0] if not group["displacement"].empty else "未知"
        count = len(group)

        prices = pd.to_numeric(group["price"], errors="coerce").dropna()
        avg_price = int(prices.mean()) if not prices.empty else "N/A"
        min_price = int(prices.min()) if not prices.empty else "N/A"
        max_price = int(prices.max()) if not prices.empty else "N/A"

        mileages = pd.to_numeric(group["mileage"], errors="coerce").dropna()
        avg_mileage = int(mileages.mean()) if not mileages.empty else "N/A"

        locs = sorted(list(set(group["location"].dropna().astype(str))))
        locs_str = ", ".join(locs)

        years = pd.to_numeric(group["year"], errors="coerce").dropna()
        if not years.empty:
            min_y = int(years.min())
            max_y = int(years.max())
            year_range = f"{min_y}" if min_y == max_y else f"{min_y} ~ {max_y}"
        else:
            year_range = "N/A"

        summary_data.append({
            "車款名稱": model_name,
            "廠牌": brand,
            "上架數量": count,
            "平均價格": avg_price,
            "最低價格": min_price,
            "最高價格": max_price,
            "平均里程": avg_mileage,
            "出廠年份區間": year_range,
            "排氣量(cc)": cc,
            "上架店家": locs_str
        })

    summary_df = pd.DataFrame(summary_data)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(by="上架數量", ascending=False).reset_index(drop=True)
    return summary_df

def generate_excel_report_data(db_products: List[Any]) -> bytes:
    import io
    df_raw = pd.DataFrame([{
        "機車名稱": p.title,
        "來源網址": p.url,
        "廠牌": p.brand,
        "年份": p.year,
        "排氣量(cc)": p.displacement,
        "行駛里程(km)": p.mileage,
        "原價": p.original_price,
        "現價": p.current_price,
        "折價幅度": p.discount_rate,
        "實體門市": p.location,
        "CP值指數": p.cp_index,
        "CP值評級": p.cp_label,
        "更新時間": p.scraped_at
    } for p in db_products])
    
    summary_df = get_model_summary(db_products)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="車款彙整分析", index=False)
        df_raw.to_excel(writer, sheet_name="所有車輛清單", index=False)
    
    return output.getvalue()

def generate_html_report_data(db_products: List[Any]) -> str:
    summary_df = get_model_summary(db_products)
    
    df_raw = pd.DataFrame([{
        "機車名稱": f'<a href="{p.url}" target="_blank" style="color: #58a6ff; text-decoration: none;">{p.title}</a>',
        "廠牌": p.brand,
        "年份": p.year,
        "排氣量(cc)": p.displacement,
        "行駛里程(km)": f"{int(p.mileage):,}" if p.mileage else "0",
        "原價(元)": f"{int(p.original_price):,}" if p.original_price else "0",
        "現價(元)": f"{int(p.current_price):,}" if p.current_price else "0",
        "折價率": f"{p.discount_rate*100:.1f}%" if p.discount_rate else "0.0%",
        "實體門市": p.location,
        "CP值指數": f"{p.cp_index:.2f}",
        "CP值評級": f'<span style="padding: 2px 6px; border-radius: 4px; font-weight: bold; background: {"#2ecc71" if p.cp_label == "超值" else "#3498db" if p.cp_label == "合理" else "#e74c3c"}; color: #ffffff;">{p.cp_label}</span>'
    } for p in db_products])

    summary_html = summary_df.to_html(classes='spreadsheet-table', index=False, escape=False)
    data_html = df_raw.to_html(classes='spreadsheet-table', index=False, escape=False)
    
    total_count = len(db_products)
    total_models = len(summary_df)
    avg_price = int(sum(p.current_price for p in db_products) / total_count) if total_count else 0
    min_price = int(min(p.current_price for p in db_products)) if total_count else 0
    value_count = sum(1 for p in db_products if p.cp_label == '超值')
    value_pct = f"{value_count / total_count * 100:.1f}%" if total_count else "0.0%"
    
    style = """
        <style>
            body { font-family: 'Microsoft JhengHei', Arial, sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }
            h1, h2 { color: #58a6ff; margin: 0.5em 0; }
            .container { width: 100%; max-width: 1280px; margin: 20px auto; padding: 25px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
            .tab-bar { display: flex; border-bottom: 2px solid #30363d; margin-bottom: 20px; }
            .tab-btn { background: none; border: none; color: #8b949e; padding: 10px 20px; font-size: 16px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.2s ease; }
            .tab-btn:hover { color: #c9d1d9; }
            .tab-btn.active { color: #58a6ff; border-bottom: 2px solid #58a6ff; font-weight: bold; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            table.spreadsheet-table { border-collapse: collapse; width: 100%; font-size: 13px; color: #c9d1d9; margin-top: 10px; }
            table.spreadsheet-table th, table.spreadsheet-table td { border: 1px solid #30363d; padding: 10px 12px; text-align: left; }
            table.spreadsheet-table th { background: #21262d; color: #58a6ff; font-weight: 600; }
            table.spreadsheet-table tr:nth-child(even) { background: #161b22; }
            table.spreadsheet-table tr:hover { background: #21262d; }
            .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
            .summary-card { background: #21262d; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
            .summary-card strong { display: block; font-size: 14px; color: #8b949e; margin-bottom: 6px; }
            .summary-card span { font-size: 24px; font-weight: bold; color: #58a6ff; }
        </style>
        <script>
            function switchTab(tabId) {
                document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
                document.getElementById('btn-' + tabId).classList.add('active');
                document.getElementById(tabId).classList.add('active');
            }
        </script>
    """
    
    html = f"""<!DOCTYPE html>
        <html lang='zh-Hant'>
        <head>
            <meta charset='utf-8'>
            <title>2Motor 二手機車大數據 CP 值分析報表</title>
            {style}
        </head>
        <body>
            <div class='container'>
                <h1>🏍️ 二手機車大數據 CP 值智能選購分析報表</h1>
                <p style="color: #8b949e;">產出時間：{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                
                <div class='summary-grid'>
                    <div class='summary-card'><strong>總上架車輛數</strong><span>{total_count} 輛</span></div>
                    <div class='summary-card'><strong>不重複車款數</strong><span>{total_models} 款</span></div>
                    <div class='summary-card'><strong>平均價格 (元)</strong><span>{avg_price:,} 元</span></div>
                    <div class='summary-card'><strong>最低價格 (元)</strong><span>{min_price:,} 元</span></div>
                    <div class='summary-card'><strong>超值車源比例</strong><span style="color: #2ecc71;">{value_pct}</span></div>
                </div>
                
                <div class='tab-bar'>
                    <button id='btn-tab-summary' class='tab-btn active' onclick="switchTab('tab-summary')">車款彙整分析 ({total_models} 款)</button>
                    <button id='btn-tab-raw' class='tab-btn' onclick="switchTab('tab-raw')">所有車輛清單 ({total_count} 筆)</button>
                </div>
                
                <div id='tab-summary' class='tab-content active'>
                    {summary_html}
                </div>
                
                <div id='tab-raw' class='tab-content'>
                    {data_html}
                </div>
            </div>
        </body>
        </html>
    """
    return html

# =====================================================================
# 8. FastAPI 主伺服器 API 端點 (ROUTING & MIDDLEWARE)
# =====================================================================
app = FastAPI(title="貳輪部品分析 API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def home():
    return {"status": "healthy", "swagger": "/docs"}

@app.post("/api/v1/crawl", response_model=CrawlTriggerResponse)
def trigger_crawl_endpoint(max_pages: Optional[int] = None, db: Session = Depends(get_db)):
    # 初始化全局爬蟲狀態
    CRAWL_STATUS["is_running"] = True
    CRAWL_STATUS["current_page"] = 0
    CRAWL_STATUS["scraped_count"] = 0
    CRAWL_STATUS["status"] = "正在載入緩存紀錄..."
    CRAWL_STATUS["message"] = ""
    
    try:
        # 讀取資料庫中已有的 URL 與里程緩存
        cached_items = {}
        try:
            existing = db.query(Product.url, Product.mileage).all()
            cached_items = {p.url: p.mileage for p in existing if p.mileage is not None}
            logger.info(f"成功讀取 {len(cached_items)} 筆本地 URL 與里程緩存。")
        except Exception as cache_err:
            logger.warning(f"未能載入本地緩存 (可能是首次啟動或資料表為空): {cache_err}")

        # 直連同步 Requests 爬蟲 (不會阻塞 FastAPI 的背景執行緒池)
        scraped_data = scrape_products(max_pages=max_pages, cached_items=cached_items)
        if not scraped_data:
            raise Exception("未爬到商品資料")
            
        CRAWL_STATUS["status"] = "正在計算大數據 CP 值指數..."
        processed_data = calculate_cp_values(scraped_data)

        # 批次寫入資料庫
        db.query(Product).delete()
        db_products = [
            Product(
                title=item["title"], 
                url=item["url"], 
                img_url=item["img_url"],
                original_price=item["original_price"], 
                current_price=item["current_price"],
                discount_rate=item["discount_rate"],
                year=item.get("year", 0),
                mileage=item.get("mileage", 0.0),
                location=item.get("location", "其他"),
                displacement=item.get("displacement", 0),
                brand=item.get("brand", "其他"),
                cp_index=item.get("cp_index", 1.0),
                cp_label=item.get("cp_label", "合理")
            ) for item in processed_data
        ]
        db.add_all(db_products)
        
        log_entry = ScrapeLog(status="SUCCESS", products_count=len(db_products), message="成功更新資料庫並完成 CP 值分析")
        db.add(log_entry)
        db.commit()
        
        CRAWL_STATUS["status"] = "正在更新可視化圖表..."
        generate_charts(db_products)
        
        CRAWL_STATUS["status"] = "正在生成統計報表文件..."
        reports_dir = os.path.join(STATIC_DIR, "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        excel_data = generate_excel_report_data(db_products)
        with open(os.path.join(reports_dir, "report.xlsx"), "wb") as f:
            f.write(excel_data)
            
        html_data = generate_html_report_data(db_products)
        with open(os.path.join(reports_dir, "report.html"), "w", encoding="utf-8") as f:
            f.write(html_data)
        
        # 更新狀態為成功
        CRAWL_STATUS["is_running"] = False
        CRAWL_STATUS["status"] = "success"
        CRAWL_STATUS["message"] = "更新成功"
        CRAWL_STATUS["scraped_count"] = len(db_products)
        
        return CrawlTriggerResponse(status="success", scraped_count=len(db_products), message="更新成功")
    except Exception as e:
        logger.error(f"爬蟲或 CP 分析異常: {str(e)}")
        log_entry = ScrapeLog(status="FAILED", products_count=0, message=str(e))
        db.add(log_entry)
        db.commit()
        
        # 更新狀態為失敗
        CRAWL_STATUS["is_running"] = False
        CRAWL_STATUS["status"] = "failed"
        CRAWL_STATUS["message"] = str(e)
        
        raise HTTPException(status_code=500, detail=f"執行失敗: {str(e)}")

@app.get("/api/v1/crawl/status")
def get_crawl_status():
    return CRAWL_STATUS

@app.get("/api/v1/products", response_model=List[ProductResponse])
def list_products_endpoint(db: Session = Depends(get_db)):
    return db.query(Product).all()

@app.get("/api/v1/analysis", response_model=AnalysisSummary)
def get_analysis_endpoint(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    if not products:
        raise HTTPException(status_code=404, detail="無商品資料，請先執行爬蟲")
    return analyze_products(products)

@app.post("/api/v1/analysis/charts", response_model=ChartResponse)
def get_charts_endpoint(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    if not products:
        raise HTTPException(status_code=404, detail="無商品資料，無法繪圖")
    charts = generate_charts(products)
    return ChartResponse(
        histogram_url=f"/static/charts/{charts['histogram']}",
        scatter_url=f"/static/charts/{charts['scatter']}",
        brand_pie_url=f"/static/charts/{charts['brand_pie']}"
    )

@app.get("/api/v1/report/excel")
def get_excel_report_endpoint():
    from fastapi.responses import FileResponse
    excel_path = os.path.join(STATIC_DIR, "reports", "report.xlsx")
    if not os.path.exists(excel_path):
        raise HTTPException(status_code=404, detail="Excel 報表未生成，請先執行爬蟲")
    return FileResponse(
        excel_path, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        filename="report.xlsx"
    )

@app.get("/api/v1/report/html")
def get_html_report_endpoint():
    from fastapi.responses import FileResponse
    html_path = os.path.join(STATIC_DIR, "reports", "report.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="HTML 報表未生成，請先執行爬蟲")
    return FileResponse(
        html_path, 
        media_type="text/html", 
        filename="report.html"
    )

@app.get("/api/v1/logs", response_model=List[ScrapeLogResponse])
def get_logs_endpoint(db: Session = Depends(get_db)):
    return db.query(ScrapeLog).order_by(ScrapeLog.timestamp.desc()).limit(20).all()

# =====================================================================
# 9. 啟動進入點 (RUNNER)
# =====================================================================
# 自動在資料庫建立表格 (自癒性 Migration 機制)
from sqlalchemy import inspect
try:
    inspector = inspect(engine)
    if "products" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("products")]
        required_cols = {"year", "mileage", "location", "displacement", "brand", "cp_index", "cp_label"}
        if not required_cols.issubset(set(columns)):
            logger.info("檢測到舊版資料庫 Schema，正在重建資料表以支援完整大數據分析欄位...")
            Base.metadata.drop_all(bind=engine)
except Exception as e:
    logger.error(f"資料庫結構檢查與遷移失敗: {e}")

Base.metadata.create_all(bind=engine)

# 自癒性報表生成 (如果資料庫已有數據，自動預先產出 Excel 與 HTML 報表)
try:
    db = SessionLocal()
    db_products = db.query(Product).all()
    if db_products:
        reports_dir = os.path.join(STATIC_DIR, "reports")
        excel_path = os.path.join(reports_dir, "report.xlsx")
        html_path = os.path.join(reports_dir, "report.html")
        if not os.path.exists(excel_path) or not os.path.exists(html_path):
            os.makedirs(reports_dir, exist_ok=True)
            logger.info("檢測到資料庫有數據但報表檔案缺失，正在自動生成 Excel 與 HTML 報表...")
            excel_data = generate_excel_report_data(db_products)
            with open(excel_path, "wb") as f:
                f.write(excel_data)
            html_data = generate_html_report_data(db_products)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_data)
            logger.info("自動補報表完成！")
except Exception as startup_err:
    logger.error(f"啟動時報表自癒失敗: {startup_err}")
finally:
    db.close()

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
