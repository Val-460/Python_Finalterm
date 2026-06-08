import os
import sys
import asyncio
import re
import datetime
import logging
from typing import List, Dict, Any, Optional

# =====================================================================
# 1. 異步事件迴圈設定 (Windows 相容性修正)
# =====================================================================
import threading

def run_async_in_new_loop(coro):
    """
    在獨立的背景執行緒中建立並執行一個全新的 ProactorEventLoop，
    這能徹底防止 Uvicorn 與 Playwright 之間因 SelectorEventLoop 導致的 NotImplementedError。
    """
    result = None
    exception = None

    def worker():
        nonlocal result, exception
        try:
            # Windows 強制選用 ProactorEventLoop
            loop = asyncio.ProactorEventLoop() if sys.platform == 'win32' else asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(coro)
        except Exception as e:
            exception = e
        finally:
            loop.close()

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    if exception:
        raise exception
    return result

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
from playwright.async_api import async_playwright
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

async def scrape_products(max_pages: int = 3) -> List[Dict[str, Any]]:
    """以 Playwright 爬取貳輪部品電商前 max_pages 頁數據"""
    products = []
    base_url = "https://shop.2motor.tw"
    
    async with async_playwright() as p:
        logger.info("正在啟動 Playwright 瀏覽器...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        page.set_default_timeout(30000)

        for page_num in range(1, max_pages + 1):
            url = f"{base_url}/collections/all?page={page_num}"
            logger.info(f"正在爬取第 {page_num} 頁: {url}")
            try:
                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                # Shopify 商品卡片選取器
                cards = await page.query_selector_all(
                    ".grid__item, .product-card, .grid-view-item, .product-item, .card, div[class*='product-grid'] div"
                )
                if not cards:
                    cards = await page.query_selector_all("a[href*='/products/']")
                
                seen_urls = set()
                for card in cards:
                    link_elem = await card.query_selector("a[href*='/products/']")
                    if not link_elem:
                        href = await card.get_attribute("href")
                        if href and "/products/" in href:
                            link_elem = card
                        else:
                            continue
                            
                    href = await link_elem.get_attribute("href")
                    if not href:
                        continue
                    full_url = href if href.startswith("http") else f"{base_url}{href}"
                    
                    if full_url in seen_urls or full_url in [p['url'] for p in products]:
                        continue
                        
                    # 解析商品名稱 (新增 .card-information__text 與 .card__heading 相容)
                    title = ""
                    title_elem = await card.query_selector(
                        ".card-information__text, .card__heading, .grid-view-item__title, .product-card__title, .title, h3"
                    )
                    if title_elem:
                        title = await title_elem.inner_text()
                    if not title or title.strip() == "":
                        title = await link_elem.inner_text()
                    title = title.strip()
                    if not title:
                        continue
                        
                    # 解析商品圖片
                    img_elem = await card.query_selector("img")
                    img_url = ""
                    if img_elem:
                        img_url = await img_elem.get_attribute("src")
                        if not img_url or img_url.startswith("data:"):
                            img_url = await img_elem.get_attribute("data-src")
                        if not img_url or img_url.startswith("data:"):
                            img_url = await img_elem.get_attribute("srcset")
                            if img_url:
                                img_url = img_url.split(",")[0].split(" ")[0]
                    if img_url and img_url.startswith("//"):
                        img_url = f"https:{img_url}"

                    # 解析價格
                    price_elements = await card.query_selector_all(".price-item, [class*='price'], .price")
                    prices_found = []
                    for pe in price_elements:
                        text = await pe.inner_text()
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
                        card_text = await card.inner_text()
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

                    products.append({
                        "title": title,
                        "url": full_url,
                        "img_url": img_url if img_url else None,
                        "original_price": original_price,
                        "current_price": current_price,
                        "discount_rate": round(discount_rate, 4)
                    })
                    seen_urls.add(full_url)
            except Exception as e:
                logger.error(f"爬取第 {page_num} 頁時發生錯誤: {str(e)}")
        await browser.close()
    return products

# =====================================================================
# 6. Pandas 統計分析與數據清洗 (SERVICES: ANALYSIS)
# =====================================================================
def analyze_products(db_products: List[Product]) -> Dict[str, Any]:
    """使用 Pandas 進行資料清洗與數值分析統計"""
    if not db_products:
        return {
            "total_count": 0, "avg_original_price": 0.0, "avg_current_price": 0.0,
            "avg_discount_rate": 0.0, "max_discount_rate": 0.0, "min_price": 0.0,
            "max_price": 0.0, "price_distribution": {}
        }
    
    data = [{
        "original_price": p.original_price,
        "current_price": p.current_price,
        "discount_rate": p.discount_rate
    } for p in db_products]
    df = pd.DataFrame(data)
    
    # 清洗掉異常值
    df = df[(df["original_price"] > 0) & (df["current_price"] > 0)]
    if df.empty:
        return {
            "total_count": 0, "avg_original_price": 0.0, "avg_current_price": 0.0,
            "avg_discount_rate": 0.0, "max_discount_rate": 0.0, "min_price": 0.0,
            "max_price": 0.0, "price_distribution": {}
        }

    total_count = len(df)
    avg_orig = float(df["original_price"].mean())
    avg_curr = float(df["current_price"].mean())
    avg_disc = float(df["discount_rate"].mean())
    max_disc = float(df["discount_rate"].max())
    min_price = float(df["current_price"].min())
    max_price = float(df["current_price"].max())

    # 價格分組
    bins = [0, 1000, 3000, 5000, 10000, float('inf')]
    labels = ["$1000以下", "$1001-3000", "$3001-5000", "$5001-10000", "$10000以上"]
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
        "price_distribution": price_dist
    }

# =====================================================================
# 7. Matplotlib 圖表可視化生成 (SERVICES: CHART)
# =====================================================================
def generate_charts(db_products: List[Product]) -> Dict[str, str]:
    """生成價格直方圖、折扣散佈圖、熱門品牌圓餅圖"""
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

    # 品牌擷取與資料處理
    data = []
    for p in db_products:
        words = p.title.strip().split()
        brand = words[0] if words else "其他"
        if len(brand) > 12 or any(char in brand for char in ["【", "★", "(", "（"]):
            brand = "其他"
        data.append({
            "current_price": p.current_price,
            "original_price": p.original_price,
            "discount_rate": p.discount_rate,
            "brand": brand
        })
    df = pd.DataFrame(data)

    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Arial', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False

    # 1. 價格直方圖
    plt.figure(figsize=(10, 6))
    plt.hist(df["current_price"], bins=15, color="steelblue", edgecolor="white", alpha=0.8)
    plt.title("貳輪部品市場價格分布直方圖", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("現價 (NT$)", fontsize=12)
    plt.ylabel("商品數量 (件)", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(hist_path, dpi=150)
    plt.close()

    # 2. 折扣散佈圖
    plt.figure(figsize=(10, 6))
    disc_df = df[df["discount_rate"] > 0]
    if disc_df.empty:
        plt.scatter(df["current_price"], df["discount_rate"], color="crimson", alpha=0.6, s=50)
    else:
        plt.scatter(disc_df["current_price"], disc_df["discount_rate"] * 100, color="crimson", alpha=0.6, s=50)
    plt.title("商品現價與折扣幅度散佈圖", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("現價 (NT$)", fontsize=12)
    plt.ylabel("折扣折數 (% Off)", fontsize=12)
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
    plt.title("電商熱門品牌商品數量佔比 (Top 5)", fontsize=14, fontweight="bold", pad=15)
    plt.tight_layout()
    plt.savefig(brand_pie_path, dpi=150)
    plt.close()

    return {"histogram": hist_filename, "scatter": scatter_filename, "brand_pie": brand_pie_filename}

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
async def trigger_crawl_endpoint(db: Session = Depends(get_db)):
    try:
        # 使用獨立 thread/loop 執行爬蟲，繞開 Uvicorn 預設事件迴圈對 Playwright 的限制
        scraped_data = run_async_in_new_loop(scrape_products(max_pages=3))
        if not scraped_data:
            raise Exception("未爬到商品資料")
            
        db.query(Product).delete()
        db_products = [
            Product(
                title=item["title"], url=item["url"], img_url=item["img_url"],
                original_price=item["original_price"], current_price=item["current_price"],
                discount_rate=item["discount_rate"]
            ) for item in scraped_data
        ]
        db.add_all(db_products)
        
        log_entry = ScrapeLog(status="SUCCESS", products_count=len(db_products), message="成功更新資料庫")
        db.add(log_entry)
        db.commit()
        
        generate_charts(db_products)
        return CrawlTriggerResponse(status="success", scraped_count=len(db_products), message="更新成功")
    except Exception as e:
        logger.error(f"爬蟲異常: {str(e)}")
        log_entry = ScrapeLog(status="FAILED", products_count=0, message=str(e))
        db.add(log_entry)
        db.commit()
        raise HTTPException(status_code=500, detail=f"執行失敗: {str(e)}")

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

@app.get("/api/v1/logs", response_model=List[ScrapeLogResponse])
def get_logs_endpoint(db: Session = Depends(get_db)):
    return db.query(ScrapeLog).order_by(ScrapeLog.timestamp.desc()).limit(20).all()

# =====================================================================
# 9. 啟動進入點 (RUNNER)
# =====================================================================
# 自動在資料庫建立表格
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
