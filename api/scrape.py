import json
import asyncio
import tempfile
import base64
import io
from pathlib import Path

from src.config import ScrapeConfig
from src.scraper import fetch_all_data
from src.analyzer import analyze_and_plot


def read_request_json(request):
    if hasattr(request, 'json'):
        return request.json()
    if hasattr(request, 'get_json'):
        return request.get_json()
    try:
        body = request.body
        if isinstance(body, bytes):
            body = body.decode('utf-8')
        return json.loads(body or '{}')
    except Exception:
        return {}


def handler(request):
    payload = read_request_json(request) or {}
    keywords = payload.get('keywords', '')
    max_pages = int(payload.get('max_pages', 5) or 5)

    cfg = ScrapeConfig(
        keywords=keywords,
        max_pages=max_pages,
        headless=True,
        output_prefix='2wheel',
    )

    logs = []

    def log_callback(msg: str):
        logs.append(msg)

    try:
        data_list = asyncio.run(fetch_all_data(cfg, log_callback))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            outputs = {
                'csv': str(tmpdir_path / 'listings.csv'),
                'main_png': str(tmpdir_path / 'analysis.png'),
                'excel': str(tmpdir_path / 'report.xlsx'),
                'html': str(tmpdir_path / 'report.html'),
            }

            df = analyze_and_plot(data_list, outputs, log_callback)

            csv_text = None
            try:
                csv_path = outputs['csv']
                if Path(csv_path).exists():
                    csv_text = Path(csv_path).read_text(encoding='utf-8-sig')
            except Exception as exc:
                logs.append(f'[Error] 讀取 CSV 失敗：{exc}')

            html_text = None
            try:
                html_path = outputs['html']
                if Path(html_path).exists():
                    html_text = Path(html_path).read_text(encoding='utf-8')
            except Exception as exc:
                logs.append(f'[Error] 讀取 HTML 失敗：{exc}')

            png_b64 = None
            try:
                png_path = outputs['main_png']
                if Path(png_path).exists():
                    png_b64 = base64.b64encode(Path(png_path).read_bytes()).decode('ascii')
            except Exception as exc:
                logs.append(f'[Error] 讀取 PNG 失敗：{exc}')

            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'rows': len(df),
                    'csv': csv_text,
                    'csv_filename': 'listings.csv',
                    'html': html_text,
                    'html_filename': 'report.html',
                    'png': png_b64,
                    'logs': logs,
                })
            }

    except Exception as exc:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': str(exc), 'logs': logs})
        }
