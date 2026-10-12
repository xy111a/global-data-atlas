#!/usr/bin/env python3
"""增量新增 World Bank 扩展指标并合并进 vendor/ext_indicators.js（B4, 2026-10-12）。
   与 fetch_ext_data.py 的区别：只抓 NEW 里列出的指标、并【合并】进现有 window.EXT，
   不重抓/不覆盖既有 8 指标数值 → 避免扰动 data_verify 已校验的旧指标。
   已确认 WB 现在有效、语义各异的两个码：
     urban     SP.URB.TOTL.IN.ZS   城镇人口占总人口 %
     inflation FP.CPI.TOTL.ZG      消费价格通胀（年 %，可为负）
   安全：分批(32国)+每批间隔+重试；写前 atomic_write 备份到 /tmp。
"""
import json, urllib.request, time, os
from fetch_ext_data import fetch, parse_wb, atomic_write

NEW = {
    "urban":     "SP.URB.TOTL.IN.ZS",
    "inflation": "FP.CPI.TOTL.ZG",
}
PATH = "vendor/ext_indicators.js"

def iso3_to_iso2():
    d = fetch("https://api.worldbank.org/v2/country?format=json&per_page=400")
    m = {}
    for c in d[1]:
        if c.get("iso2Code") and c.get("id") and len(c["id"]) == 3:
            m[c["id"]] = c["iso2Code"]
    return m

def load_ext():
    src = open(PATH, encoding="utf-8").read()
    import re
    mo = re.search(r"window\.EXT\s*=\s*(\{[\s\S]*\});", src)
    if not mo:
        raise RuntimeError("ext_indicators.js 未找到 window.EXT")
    return json.loads(mo.group(1))

def main():
    # 国家 iso2 列表来自 countries_wb.js（与 fetch_ext_data 一致）
    WB = parse_wb(open("vendor/countries_wb.js", encoding="utf-8").read())
    iso2s = sorted(WB.keys())
    cc_map = iso3_to_iso2()
    ext = load_ext()
    print(f"现有 EXT 国家数: {len(ext)} | 待新增指标: {list(NEW)}")

    for name, code in NEW.items():
        batches = [iso2s[i:i+32] for i in range(0, len(iso2s), 32)]
        got = 0
        for bi, batch in enumerate(batches):
            cc = ";".join(batch)
            url = f"https://api.worldbank.org/v2/country/{cc}/indicator/{code}?format=json&per_page=1000&date=2000:2024"
            for attempt in range(3):
                try:
                    d = fetch(url)
                    rows = d[1] if isinstance(d, list) and len(d) > 1 and d[1] else []
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"  {name} 批次{bi} 最终失败: {e}"); rows = []
                    else:
                        time.sleep(4)
            for r in rows:
                iso3 = r.get("countryiso3code") or (r.get("country") or {}).get("id")
                if not iso3:
                    continue
                iso2 = cc_map.get(iso3, iso3)
                y = r.get("date"); v = r.get("value")
                if not y or v is None:
                    continue
                ext.setdefault(iso2, {}).setdefault(name, {})[y] = v
                got += 1
            time.sleep(1.5)
        cover = sum(1 for k in ext if ext[k].get(name))
        print(f"[+{name}] ({code}): 取回 {got} 条, 覆盖 {cover} 国")

    # 仅保留每个指标的非空年份
    for k in ext:
        for name in NEW:
            if name in ext[k]:
                ext[k][name] = {y: v for y, v in ext[k][name].items() if v is not None}

    js = ("/* 扩展指标（World Bank）：trade/health/edu/life/gdpcap/unemp/internet/military"
          " + urban城镇人口%/inflation通胀CPI%（2026-10-12 B4 增量新增） */\n")
    js += "window.EXT = " + json.dumps(ext, ensure_ascii=False, separators=(',', ':')) + ";\n"
    bak = atomic_write(PATH, js)
    print(f"已合并写入 {PATH} ({os.path.getsize(PATH)} bytes)")
    if bak:
        print(f"自动备份: {bak}")

if __name__ == "__main__":
    main()
