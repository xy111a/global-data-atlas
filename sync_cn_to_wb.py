#!/usr/bin/env python3
"""把 _enmap.json 的中文名同步进 vendor/countries_wb.js（window.WB 的 cn 字段）。

用法：python3 sync_cn_to_wb.py
"""
import json, re

EMAP = "_enmap.json"
WB_JS = "vendor/countries_wb.js"

def main():
    emap = json.load(open(EMAP, encoding="utf-8"))
    src = open(WB_JS, encoding="utf-8").read()
    m = re.search(r'(window\.WB\s*=\s*)(\{[\s\S]*\})', src)
    body = m.group(2)
    # 逐个替换 "ISO":{"cn":"...", ...} 中的 cn 值（只替换 WB 对象体内该 key 的首个出现）
    replaced, missing = [], []
    for iso, v in emap.items():
        cn = v.get("cn")
        if not cn:
            continue
        # 匹配 "ISO":{"...cn":"旧值"...}
        pat = re.compile(r'("' + re.escape(iso) + r'"\s*:\s*\{[^{}]*?"cn"\s*:\s*")[^"]*(")', re.S)
        n = pat.subn(lambda mo: mo.group(1) + cn + mo.group(2), body, count=1)
        if n[1] == 1:
            body = n[0]
            replaced.append(iso)
        else:
            missing.append(iso)
    new_src = m.group(1) + body
    open(WB_JS, "w", encoding="utf-8").write(new_src)
    print(f"✅ 同步 {len(replaced)} 个 cn 到 countries_wb.js")
    if missing:
        print(f"⚠️ 未找到匹配: {missing}")

if __name__ == "__main__":
    main()
