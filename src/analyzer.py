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


def get_model_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[
            "車款名稱", "廠牌", "上架數量", "平均價格", "最低價格", "最高價格", "平均里程", "出廠年份區間", "排氣量(cc)", "上架店家"
        ])

    df_temp = df.copy()
    df_temp["model"] = df_temp["model"].fillna("未知車款").astype(str).str.strip()
    df_temp["brand"] = df_temp["brand"].fillna("未知廠牌").astype(str).str.strip()
    df_temp["store"] = df_temp["store"].fillna("未知店家").astype(str).str.strip()

    summary_data = []
    for model_name, group in df_temp.groupby("model"):
        brand = group["brand"].iloc[0] if not group["brand"].empty else "未知廠牌"
        cc = group["cc"].iloc[0] if not group["cc"].empty and not pd.isna(group["cc"].iloc[0]) else "未知"
        count = len(group)

        # Prices
        prices = pd.to_numeric(group["price"], errors="coerce").dropna()
        avg_price = int(prices.mean()) if not prices.empty else "N/A"
        min_price = int(prices.min()) if not prices.empty else "N/A"
        max_price = int(prices.max()) if not prices.empty else "N/A"

        # Mileages
        mileages = pd.to_numeric(group["mileage"], errors="coerce").dropna()
        avg_mileage = int(mileages.mean()) if not mileages.empty else "N/A"

        # Stores
        stores = sorted(list(set(group["store"].dropna().astype(str))))
        stores_str = ", ".join(stores)

        # Years
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
            "上架店家": stores_str
        })

    summary_df = pd.DataFrame(summary_data)
    if not summary_df.empty:
        summary_df = summary_df.sort_values(by="上架數量", ascending=False).reset_index(drop=True)
    return summary_df


def create_excel_report(df: pd.DataFrame, excel_path: str, log_callback: Callable[[str], None]) -> None:
    try:
        summary_df = get_model_summary(df)
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            summary_df.to_excel(writer, sheet_name="車款彙整分析", index=False)
            df.to_excel(writer, sheet_name="所有車輛清單", index=False)
        log_callback(f"[Data] 已成功匯出 Excel 試算表：{excel_path}")
    except Exception as e:
        log_callback(f"[Error] 匯出 Excel 失敗：{e}")


def create_html_report(df: pd.DataFrame, html_path: str, log_callback: Callable[[str], None]) -> None:
    try:
        summary_df = get_model_summary(df)
        
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
        
        summary_html = summary_df.to_html(classes='spreadsheet-table', index=False, escape=False)
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
                    
                    <div class='summary-grid'>
                        <div class='summary-card'><strong>總上架車輛數</strong><span>{len(df)}</span></div>
                        <div class='summary-card'><strong>不重複車款數</strong><span>{len(summary_df)}</span></div>
                        <div class='summary-card'><strong>平均價格 (元)</strong><span>{int(df['price'].mean()) if not df['price'].dropna().empty else 'N/A'}</span></div>
                        <div class='summary-card'><strong>最低價格 (元)</strong><span>{int(df['price'].min()) if not df['price'].dropna().empty else 'N/A'}</span></div>
                    </div>
                    
                    <div class='tab-bar'>
                        <button id='btn-tab-summary' class='tab-btn active' onclick="switchTab('tab-summary')">車款彙整分析 ({len(summary_df)} 款)</button>
                        <button id='btn-tab-raw' class='tab-btn' onclick="switchTab('tab-raw')">所有車輛清單 ({len(df)} 筆)</button>
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
