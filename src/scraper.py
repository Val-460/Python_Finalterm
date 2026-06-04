# -*- coding: utf-8 -*-
import asyncio
import random
import re
import tempfile
import traceback
import urllib.parse
from pathlib import Path
from typing import Callable, List

from .config import BASE_URL, SITE_ROOT, USER_AGENTS, ScrapeConfig
from .utils import safe_int


def build_target_url(config: ScrapeConfig, page_num: int) -> str:
    try:
        page_val = int(page_num)
    except Exception:
        page_val = 1

    query_params = {}
    if page_val > 1:
        query_params["page"] = page_val
    query_params["limit"] = 50

    if getattr(config, "keywords", None):
        query_params["q"] = config.keywords

    query_string = urllib.parse.urlencode(query_params, doseq=True)
    return f"{BASE_URL}?{query_string}" if query_string else BASE_URL


async def fetch_all_data(config: ScrapeConfig, log_callback: Callable[[str], None] = print) -> List[dict]:
    if not callable(log_callback):
        log_callback = print

    try:
        import requests
        from bs4 import BeautifulSoup
    except Exception as e:
        log_callback(f"[Error] 無法匯入 requests 或 beautifulsoup4: {e}")
        return []

    results: List[dict] = []
    temp_dir = Path(tempfile.gettempdir()) / "2motor_debug"
    debug_html_dir = temp_dir / "html_pages"
    debug_link_dir = temp_dir / "link_logs"
    try:
        debug_html_dir.mkdir(parents=True, exist_ok=True)
        debug_link_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        debug_html_dir = None
        debug_link_dir = None

    session = requests.Session()
    if USER_AGENTS:
        session.headers["User-Agent"] = random.choice(USER_AGENTS)

    page_num = 1
    while page_num <= max(1, int(config.max_pages)):
        page_url = build_target_url(config, page_num)
        log_callback(f"[Page {page_num}] 正在請求: {page_url}")

        try:
            response = await asyncio.to_thread(session.get, page_url, timeout=30)
            response.raise_for_status()
            html_content = response.text
        except Exception as e:
            log_callback(f"[Page {page_num}] 請求失敗：{e}")
            break

        if debug_html_dir is not None:
            try:
                debug_file = debug_html_dir / f"page_{page_num}.html"
                debug_file.write_text(html_content, encoding="utf-8")
                log_callback(f"[Page {page_num}] 已儲存觀察 HTML：{debug_file}")
            except Exception as e:
                log_callback(f"[Page {page_num}] 儲存觀察 HTML 失敗：{e}")
        else:
            log_callback(f"[Page {page_num}] 跳過儲存觀察 HTML（debug 目錄不可用）")

        try:
            soup = BeautifulSoup(html_content, "html.parser")
        except Exception as e:
            log_callback(f"[Page {page_num}] 解析 HTML 失敗：{e}")
            break

        cards = [card for card in soup.select("li.grid__item") if card.select_one('a[href*="/collections/allmotor/products/"]')]

        if not cards:
            log_callback(f"[Page {page_num}] 未直接找到商品卡片，啟動備援連結掃描。")
            link_tags = soup.select("a[href]")
            fallback_items = []
            all_href_entries = []
            for link in link_tags:
                href = link.get("href")
                if not href:
                    continue
                text = (link.get_text(separator=" ", strip=True) or "").strip()
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

            if debug_link_dir is not None:
                try:
                    link_debug_file = debug_link_dir / f"links_{page_num}.txt"
                    link_debug_file.write_text("\n".join(all_href_entries), encoding="utf-8")
                    log_callback(f"[Page {page_num}] 已儲存所有連結供觀察：{link_debug_file}")
                except Exception as e:
                    log_callback(f"[Page {page_num}] 儲存連結觀察檔案失敗：{e}")
            else:
                log_callback(f"[Page {page_num}] 跳過儲存連結觀察檔案（debug 目錄不可用）")

            if fallback_items:
                log_callback(f"[Page {page_num}] 備援連結掃描找到 {len(fallback_items)} 個可能商品項目。")
                results.extend(fallback_items)
                break
            else:
                log_callback(f"[Page {page_num}] 找不到商品，結束抓取。")
                break

        for card in cards:
            try:
                card_text = card.get_text(separator=" ", strip=True) or ""
                log_callback(f"--- [Raw Text 偵測] ---\n{card_text.strip()}\n----------------------")

                raw_text = card_text
                title_el = card.select_one('.card-information__text, a.grid-link__title, .card__heading, .product-card__title, h2, h3')
                if not title_el:
                    title_el = card.select_one('a')
                title = title_el.get_text(separator=" ", strip=True).strip() if title_el else None

                price_el = card.select_one('.price, .amount, .woocommerce-Price-amount, .price-item, .price-item--regular, .price-item--sale, .product-card__price')
                price_text = price_el.get_text(separator=" ", strip=True) if price_el else None
                if not price_text:
                    price_match = re.search(r"NT\$\s*([\d,]+)", raw_text)
                    price_text = price_match.group(0) if price_match else None
                price = safe_int(price_text) if price_text else None

                link_el = card.select_one('a[href]')
                url = link_el.get('href') if link_el else None
                if url:
                    url = urllib.parse.urljoin(SITE_ROOT, url)

                m = re.search(r"(\d{1,3}(?:,\d{3})*)\s*(?:km|公里)", raw_text, re.IGNORECASE)
                mileage = int(m.group(1).replace(",", "")) if m else None

                y = re.search(r"\b(19\d{2}|20\d{2})\b", raw_text)
                year = int(y.group(0)) if y else None

                c = re.search(r"(\d{2,4})\s*(?:cc|c\.c\.|c\.c|c.c)", raw_text, re.IGNORECASE)
                cc = int(c.group(1)) if c else None

                store = None
                store_el = card.select_one('.store, .shop, .seller')
                if store_el:
                    store_text = store_el.get_text(separator=" ", strip=True)
                    store = store_text or None
                if not store and "店" in raw_text:
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
                log_callback(f"[Page {page_num}] 卡片解析錯誤：{e}")

        await asyncio.sleep(random.uniform(1.0, 2.5))
        page_num += 1

    return results
