import requests
from bs4 import BeautifulSoup
import re

def get_cleaned_title(title: str) -> str:
    if not title:
        return ""
    clean = title
    
    # 1. 移除門市，如 【新北樹林店】 或 [台北大同店]
    clean = re.sub(r'[【\[](.*?)[】\]]', '', clean)
    
    # 2. 移除出廠年份，如 2019, 2020
    clean = re.sub(r'\b(20\d\d|19\d\d)\b', '', clean)
    
    # 3. 移除車號編碼，如 #8929 或 # 1234
    clean = re.sub(r'#\s*\d+', '', clean)
    
    # 4. 移除所有括號及其內容，例如 (碟煞)、（皮帶版）
    clean = re.sub(r'[\(（].*?[\)）]', '', clean)
    
    # 5. 移除常見品牌詞（不分大小寫、中文與英文）
    brand_words = ["山葉", "yamaha", "三陽", "sym", "光陽", "kymco", "摩特動力", "pgo", "鈴木", "suzuki", "台鈴", "本田", "honda", "偉士牌", "vespa", "宏佳騰", "aeon", "睿能", "gogoro", "川崎", "kawasaki"]
    for word in brand_words:
        clean = re.sub(r'\b' + re.escape(word) + r'\b', '', clean, flags=re.IGNORECASE)
        clean = clean.replace(word, '')

    # 6. 循環移除尾部的規格修飾詞與排氣量數字（因為多個修飾詞可能會並存，如 125雙碟ABS）
    spec_regex = re.compile(r'\s*(?:ABS|TCS|KEYLESS|CBS|UBS|雙碟|單碟|碟煞|鼓煞|特仕|精裝|跑車|皮帶|鍊條|鑰匙|仕樣|化油|噴射)+(?:版|款|型|版本)?\s*$', re.IGNORECASE)
    cc_regex = re.compile(r'\s*\b(?:125|158|110|150|100|115|120|180|200|250|300|350|400)\s*(?:cc|CC)?\b\s*$', re.IGNORECASE)
    
    while True:
        original_len = len(clean)
        clean = spec_regex.sub('', clean)
        clean = cc_regex.sub('', clean)
        if len(clean) == original_len:
            break

    # 7. 清理多餘空格
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

url = "https://shop.2motor.tw/collections/all?page=1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}
resp = requests.get(url, headers=headers, timeout=20)
if resp.status_code == 200:
    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select(".grid__item, .product-card, .grid-view-item, .product-item, .card")
    if not cards:
        cards = soup.select("a[href*='/products/']")
    
    print(f"Found {len(cards)} items.")
    for card in cards:
        title_elem = card.select_one(".card-information__text, .card__heading, .grid-view-item__title, .product-card__title, .title, h3")
        title = ""
        if title_elem:
            title = title_elem.get_text().strip()
        else:
            # Fallback if card is the anchor itself
            title = card.get_text().strip()
        
        # Clean title if non-empty
        title = re.sub(r'\s+', ' ', title)
        if title and len(title) > 5:
            print(f"Original: {title}")
            print(f"Cleaned : {get_cleaned_title(title)}")
            print("-" * 50)
else:
    print(f"Failed to fetch site, status code: {resp.status_code}")
