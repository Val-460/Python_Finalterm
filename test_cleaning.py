import re
import sys

# Set stdout encoding to utf-8 to print Chinese characters correctly in the log
sys.stdout.reconfigure(encoding='utf-8')

test_titles = [
    "【新北樹林店】2019 山葉 YAMAHA 勁戰四代 (碟煞) #8929",
    "山葉YAMAHA 勁戰四代(碟煞)",
    "山葉YAMAHA 勁戰三代 (碟煞)",
    "睿能 GOGORO VIVA MIX BELT(皮帶版)",
    "睿能 GOGORO VIVA MIX BELT",
    "【台中一中店】2021 三陽 SYM JET SL 125雙碟ABS",
    "三陽 SYM JET SL ABS",
    "三陽 SYM JET SL+ 158 TCS",
    "光陽 MANY 110 鼓煞版",
    "【高雄三民店】2020 宏佳騰 Ai-1 Sport Keyless",
]

def clean_model_name(title: str) -> str:
    if not title:
        return ""
    clean = title
    
    # 1. 移除門市，如 【新北樹林店】 或 [台北大同店]
    clean = re.sub(r'[【\[](.*?)[】\]]', ' ', clean)
    
    # 2. 移除出廠年份，如 2019, 2020
    clean = re.sub(r'\b(20\d\d|19\d\d)\b', ' ', clean)
    
    # 3. 移除車號編碼，如 #8929
    clean = re.sub(r'#\s*\d+', ' ', clean)
    
    # 4. 移除所有括號及其內容，例如 (碟煞)、（皮帶版）
    clean = re.sub(r'[\(（].*?[\)）]', ' ', clean)
    
    # 5. 移除常見品牌詞（不分大小寫、中文與英文）
    brand_words = [
        "山葉", "yamaha", "yamah", 
        "三陽", "sym", 
        "光陽", "kymco", 
        "摩特動力", "pgo", 
        "鈴木", "suzuki", "台鈴", 
        "本田", "honda", 
        "偉士牌", "vespa", 
        "宏佳騰", "aeon", 
        "睿能", "gogoro", 
        "川崎", "kawasaki"
    ]
    for word in brand_words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        clean = pattern.sub(' ', clean)

    # 6. 循環移除尾部的規格修飾詞與排氣量數字（因為多個修飾詞可能會並存，如 125雙碟ABS）
    spec_regex = re.compile(r'\s*(?:ABS|TCS|KEYLESS|CBS|UBS|雙碟|單碟|碟煞|鼓煞|特仕|精裝|跑車|皮帶|鍊條|鑰匙|仕樣|化油|噴射)+(?:版|款|型|版本)?\s*$', re.IGNORECASE)
    cc_regex = re.compile(r'\s*\b(?:125|158|110|150|100|115|120|180|200|250|300|350|400)\s*(?:cc|CC)?\b\s*$', re.IGNORECASE)
    
    while True:
        clean = re.sub(r'\s+', ' ', clean).strip()
        original_len = len(clean)
        clean = spec_regex.sub(' ', clean)
        clean = cc_regex.sub(' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if len(clean) == original_len:
            break

    # 7. 清理多餘空格
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

for t in test_titles:
    print(f"Original: {t}")
    print(f"Cleaned : {clean_model_name(t)}")
    print("-" * 40)

