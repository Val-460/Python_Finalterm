# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Callable, Dict

import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "SimHei", "Arial Unicode MS"]
matplotlib.rcParams["axes.unicode_minus"] = False

import matplotlib.pyplot as plt
import pandas as pd


def analyze_and_plot(data_list: list[dict], outputs: Dict[str, str], log_callback: Callable[[str], None] = print) -> pd.DataFrame:
    if not callable(log_callback):
        log_callback = print

    try:
        df = pd.DataFrame(data_list)
    except Exception as e:
        log_callback(f"[Error] 無法將資料轉為 DataFrame：{e}")
        df = pd.DataFrame(columns=["title", "price", "url", "mileage", "year", "cc", "store"])

    if df.empty:
        log_callback("[Warning] 沒抓取到任何有效的二手機車數據。")
        empty_df = pd.DataFrame(columns=["title", "brand", "model", "item_id", "price", "url", "mileage", "year", "cc", "store", "raw_text"])
        try:
            empty_df.to_csv(outputs.get("csv", "output_listings.csv"), index=False, encoding="utf-8-sig")
            log_callback(f"[Data] 已儲存空 CSV：{outputs.get('csv', 'output_listings.csv')}")
        except Exception as e:
            log_callback(f"[Error] 儲存空 CSV 失敗：{e}")
        return empty_df

    for col in ["title", "brand", "model", "item_id", "price", "url", "mileage", "year", "cc", "store", "raw_text"]:
        if col not in df.columns:
            df[col] = None

    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["mileage"] = pd.to_numeric(df["mileage"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["cc"] = pd.to_numeric(df["cc"], errors="coerce")

    df = df.drop_duplicates(subset=["url"]).reset_index(drop=True)

    csv_path = outputs.get("csv", "output_listings.csv")
    try:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        log_callback(f"[Data] 已成功儲存 {len(df)} 筆不重複的機車資料至 CSV：{csv_path}")
    except Exception as e:
        log_callback(f"[Error] 儲存 CSV 失敗：{e}")

    create_excel_report(df, outputs.get("excel", "report.xlsx"), log_callback)
    create_html_report(df, outputs.get("html", "report.html"), log_callback)
    create_analysis_chart(df, outputs.get("main_png", "analysis.png"), log_callback)
    return df


def create_excel_report(df, excel_path: str, log_callback: Callable[[str], None]) -> None:
    try:
        df.to_excel(excel_path, index=False, engine="openpyxl")
        log_callback(f"[Data] 已成功匯出 Excel 試算表：{excel_path}")
    except Exception as e:
        log_callback(f"[Error] 匯出 Excel 失敗：{e}")


def create_html_report(df, html_path: str, log_callback: Callable[[str], None]) -> None:
    try:
        style = """
            <style>
                body { font-family: 'Microsoft JhengHei', Arial, sans-serif; background: #f7f7f7; color: #333; }
                h1, h2 { margin: 0.3em 0; }
                .container { width: 100%; max-width: 1280px; margin: 20px auto; padding: 20px; background: #fff; box-shadow: 0 0 20px rgba(0,0,0,0.06); }
                table.spreadsheet-table { border-collapse: collapse; width: 100%; font-size: 13px; }
                table.spreadsheet-table th, table.spreadsheet-table td { border: 1px solid #d6d6d6; padding: 8px 10px; }
                table.spreadsheet-table th { background: #f0f4f8; color: #111; }
                table.spreadsheet-table tr:nth-child(even) { background: #fcfcfc; }
                .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 18px; }
                .summary-card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px; }
                .summary-card strong { display: block; font-size: 16px; margin-bottom: 6px; }
            </style>
        """
        summary_html = df.describe(include='all').round(2).to_html(classes='summary-table')
        data_html = df.to_html(classes='spreadsheet-table', index=False, escape=False)
        html = f"""
            <html lang='zh-Hant'>
            <head>
                <meta charset='utf-8'>
                <title>2Motor 二手機車試算表報表</title>
                {style}
            </head>
            <body>
                <div class='container'>
                    <h1>2Motor 二手機車試算表報表</h1>
                    <p>總筆數：{len(df)}</p>
                    <div class='summary'>
                        <div class='summary-card'><strong>資料筆數</strong>{len(df)}</div>
                        <div class='summary-card'><strong>價格最小</strong>{int(df['price'].min()) if not df['price'].dropna().empty else 'N/A'}</div>
                        <div class='summary-card'><strong>價格最大</strong>{int(df['price'].max()) if not df['price'].dropna().empty else 'N/A'}</div>
                        <div class='summary-card'><strong>平均價格</strong>{int(df['price'].mean()) if not df['price'].dropna().empty else 'N/A'}</div>
                    </div>
                    {summary_html}
                    {data_html}
                </div>
            </body>
            </html>
        """
        Path(html_path).write_text(html, encoding='utf-8')
        log_callback(f"[Data] 已成功匯出 HTML 試算表瀏覽檔：{html_path}")
    except Exception as e:
        log_callback(f"[Error] 匯出 HTML 失敗：{e}")


def create_analysis_chart(df: pd.DataFrame, png_path: str, log_callback: Callable[[str], None]) -> None:
    try:
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))

        ax = axes[0, 0]
        price_vals = df["price"].dropna()
        if price_vals.empty:
            ax.text(0.5, 0.5, "暫無數據", ha="center", va="center")
        else:
            ax.hist(price_vals, bins=30, color="#3b82f6", edgecolor="black")
            ax.set_title("機車售價分布")
            ax.set_xlabel("售價 (元)")
            ax.set_ylabel("筆數")

        ax = axes[0, 1]
        mileage_vals = df["mileage"].dropna()
        if mileage_vals.empty:
            ax.text(0.5, 0.5, "暫無數據", ha="center", va="center")
        else:
            ax.hist(mileage_vals, bins=30, color="#10b981", edgecolor="black")
            ax.set_title("行駛里程數分布")
            ax.set_xlabel("里程 (km)")
            ax.set_ylabel("筆數")

        ax = axes[0, 2]
        year_vals = df["year"].dropna()
        if year_vals.empty:
            ax.text(0.5, 0.5, "暫無數據", ha="center", va="center")
        else:
            ax.hist(year_vals, bins=20, color="#f59e0b", edgecolor="black")
            ax.set_title("出廠年份分布")
            ax.set_xlabel("年份")
            ax.set_ylabel("筆數")

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
