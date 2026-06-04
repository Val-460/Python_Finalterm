# -*- coding: utf-8 -*-
import asyncio
import queue
import traceback
from typing import Dict

from .analyzer import analyze_and_plot
from .config import output_paths
from .scraper import fetch_all_data


def run_pipeline(config, log_queue: queue.Queue) -> dict:
    def queue_log(msg: str):
        try:
            log_queue.put(("LOG", msg))
        except Exception:
            try:
                print(msg)
            except Exception:
                pass

    outputs = output_paths(config.output_prefix)

    try:
        queue_log(f"管線啟動，輸出路徑：{outputs}")
        data_list = asyncio.run(fetch_all_data(config, queue_log))
        df = analyze_and_plot(data_list, outputs, queue_log)
        rows = len(df)
        html_path = outputs.get("html")
        if html_path:
            log_queue.put(("HTML_REPORT", html_path))
        log_queue.put(("DONE", f"完成！成功抓取並分析共 {rows} 筆不重複資料。"))
        return {"outputs": outputs, "rows": rows}

    except Exception:
        tb = traceback.format_exc()
        try:
            log_queue.put(("ERROR", "執行管線時發生致命錯誤。"))
            log_queue.put(("TRACE", tb))
        except Exception:
            print(tb)
        return {"outputs": outputs, "rows": 0}
