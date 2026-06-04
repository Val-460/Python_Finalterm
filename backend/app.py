# Minimal FastAPI wrapper around existing scraper + analyzer
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio
import base64
import io

from src.config import ScrapeConfig
from src.scraper import fetch_all_data
from src.analyzer import analyze_and_plot

app = FastAPI(title="2Motor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapeRequest(BaseModel):
    keywords: Optional[str] = None
    max_pages: Optional[int] = 5
    headless: Optional[bool] = True
    output_prefix: Optional[str] = "2wheel"


@app.post('/scrape')
async def scrape(req: ScrapeRequest):
    cfg = ScrapeConfig(
        keywords=req.keywords or "",
        max_pages=int(req.max_pages or 5),
        headless=bool(req.headless),
        output_prefix=req.output_prefix or "2wheel",
    )

    logs = []
    def log_callback(msg: str):
        logs.append(msg)

    try:
        # Run the async scraper
        data_list = await fetch_all_data(cfg, log_callback)

        # Prepare outputs in-memory
        outputs = {
            'csv': None,
            'main_png': None,
            'excel': None,
            'html': None,
        }

        # Use analyzer to process and write files to disk; but capture CSV/HTML/png in-memory
        df = analyze_and_plot(data_list, outputs, log_callback)

        # CSV as string
        try:
            csv_buf = io.StringIO()
            df.to_csv(csv_buf, index=False, encoding='utf-8-sig')
            csv_text = csv_buf.getvalue()
        except Exception as e:
            csv_text = None
            logs.append(f"[Error] 產生 CSV 失敗: {e}")

        # HTML report
        html_text = None
        try:
            # analyzer already wrote an HTML file if outputs['html'] set; if not, recreate HTML
            if outputs.get('html') and io.open(outputs['html'], 'r', encoding='utf-8'):
                try:
                    with open(outputs['html'], 'r', encoding='utf-8') as f:
                        html_text = f.read()
                except Exception:
                    html_text = None
        except Exception:
            html_text = None

        # PNG: recreate chart to an in-memory buffer
        png_b64 = None
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            buf = io.BytesIO()
            # re-create chart using analyzer.create_analysis_chart is not exported; use analyze_and_plot to have created png at outputs['main_png'] if present
            if outputs.get('main_png'):
                with open(outputs['main_png'], 'rb') as f:
                    png_b64 = base64.b64encode(f.read()).decode('ascii')
            else:
                # fallback: try to create a simple PNG from current df
                fig = plt.figure(figsize=(6,4))
                plt.text(0.5,0.5,'No Image',ha='center',va='center')
                plt.tight_layout()
                fig.savefig(buf, format='png')
                png_b64 = base64.b64encode(buf.getvalue()).decode('ascii')
                plt.close(fig)
        except Exception as e:
            logs.append(f"[Error] 產生 PNG 失敗: {e}")
            png_b64 = None

        return {
            'rows': len(df),
            'csv': csv_text,
            'csv_filename': f"{cfg.output_prefix}_listings.csv",
            'html': html_text,
            'html_filename': f"{cfg.output_prefix}_report.html",
            'png': png_b64,
            'logs': logs,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
