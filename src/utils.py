# -*- coding: utf-8 -*-
import re
from typing import Optional


def safe_int(value) -> Optional[int]:
    if value is None:
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        try:
            return int(value)
        except Exception:
            return None

    try:
        text = str(value).replace(",", "")
        m = re.search(r"\d+", text)
        if m:
            return int(m.group(0))
    except Exception:
        return None

    return None


def safe_float(value) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, float):
        return value

    if isinstance(value, int):
        return float(value)

    try:
        text = str(value).replace(",", "")
        m = re.search(r"\d+(?:\.\d+)?", text)
        if m:
            return float(m.group(0))
    except Exception:
        return None

    return None
