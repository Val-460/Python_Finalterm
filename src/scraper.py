# -*- coding: utf-8 -*-
import asyncio
import random
import re
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
        from playwright.async_api import async_playwright
    except Exception as e:
        log_callback(f"[Error] 無法匯入 playwright: {e}")
        return []

    try:
        from playwright_stealth import stealth_async
        have_stealth = True
    except Exception:
        stealth_async = None
        have_stealth = False

    results: List[dict] = []
    debug_html_dir = Path("debug/html_pages")
    debug_link_dir = Path("debug/link_logs")
    debug_html_dir.mkdir(parents=True, exist_ok=True)
    debug_link_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=config.headless)
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

                    try:
                        await page.goto(page_url, timeout=90000, wait_until="domcontentloaded")
                        try:
                            await page.wait_for_load_state("networkidle", timeout=15000)
                        except Exception:
                            pass
                    except Exception as e:
                        log_callback(f"[Page {page_num}] 導航失敗：{e}")
                        break

                    try:
                        await page.wait_for_selector('body', timeout=60000)
                    except Exception:
                        pass
                    try:
                        await page.wait_for_selector('a[href*="/collections/allmotor/products/"]', timeout=15000)
                    except Exception:
                        log_callback(f"[Page {page_num}] 尚未偵測到 product link，將進行後續備援掃描。")

                    try:
                        page_title = await page.title()
                        log_callback(f"[Page {page_num}] Page title: {page_title}")
                        debug_file = debug_html_dir / f"page_{page_num}.html"
                        html_content = await page.content()
                        debug_file.write_text(html_content, encoding="utf-8")
                        log_callback(f"[Page {page_num}] 已儲存觀察 HTML：{debug_file}")
                    except Exception as e:
                        log_callback(f"[Page {page_num}] 儲存觀察 HTML 失敗：{e}")

                    all_cards = await page.query_selector_all("li.grid__item")
                    cards = []
                    for card in all_cards:
                        if await card.query_selector('a[href*="/collections/allmotor/products/"]'):
                            cards.append(card)

                    if not cards:
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
                            link_debug_file = debug_link_dir / f"links_{page_num}.txt"
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

                    for card in cards:
                        try:
                            card_text = await card.text_content()
                            card_text = card_text or ""
                            log_callback(f"--- [Raw Text 偵測] ---\n{card_text.strip()}\n----------------------")

                            raw_text = card_text
                            title_el = await card.query_selector('.card-information__text, a.grid-link__title, .card__heading, .product-card__title, h2, h3')
                            if not title_el:
                                title_el = await card.query_selector('a')
                            title = (await title_el.text_content()).strip() if title_el else None

                            price_el = await card.query_selector('.price, .amount, .woocommerce-Price-amount, .price-item, .price-item--regular, .price-item--sale, .product-card__price')
                            price_text = (await price_el.text_content()).strip() if price_el else None
                            if not price_text:
                                price_match = re.search(r"NT\$\s*([\d,]+)", raw_text)
                                price_text = price_match.group(0) if price_match else None
                            price = safe_int(price_text) if price_text else None

                            link_el = await card.query_selector('a[href]')
                            url = await link_el.get_attribute('href') if link_el else None
                            if url:
                                url = urllib.parse.urljoin(SITE_ROOT, url)

                            m = re.search(r"(\d{1,3}(?:,\d{3})*)\s*(?:km|公里)", raw_text, re.IGNORECASE)
                            mileage = int(m.group(1).replace(",", "")) if m else None

                            y = re.search(r"\b(19\d{2}|20\d{2})\b", raw_text)
                            year = int(y.group(0)) if y else None

                            c = re.search(r"(\d{2,4})\s*(?:cc|c\.c\.|c\.c|c.c)", raw_text, re.IGNORECASE)
                            cc = int(c.group(1)) if c else None

                            store = None
                            store_el = await card.query_selector('.store, .shop, .seller')
                            if store_el:
                                store_text = (await store_el.text_content()).strip()
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
            finally:
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

    return results
