# -*- coding: utf-8 -*-
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict

BASE_URL = "https://shop.2motor.tw/collections/allmotor/"
SITE_ROOT = "https://shop.2motor.tw"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
]


@dataclass
class ScrapeConfig:
    brand: str = ""
    cc_min: str = ""
    cc_max: str = ""
    price_min: str = ""
    price_max: str = ""
    keywords: str = ""
    max_pages: int = 10
    headless: bool = True
    output_prefix: str = "2wheel"


def now_text() -> str:
    return datetime.now().strftime("%H:%M:%S")


def output_paths(prefix: str) -> Dict[str, str]:
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prefix = (prefix or "2wheel").strip() or "2wheel"
    csv_name = output_dir / f"{safe_prefix}_{timestamp}_listings.csv"
    png_name = output_dir / f"{safe_prefix}_{timestamp}_analysis.png"
    excel_name = output_dir / f"{safe_prefix}_{timestamp}_report.xlsx"
    html_name = output_dir / f"{safe_prefix}_{timestamp}_report.html"
    return {
        "csv": str(csv_name),
        "main_png": str(png_name),
        "excel": str(excel_name),
        "html": str(html_name),
    }
