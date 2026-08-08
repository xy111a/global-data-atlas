#!/usr/bin/env python3
"""增量拉取 3 个新指标（unemp/internet/military）并入 vendor/ext_indicators.js
   不动已有 5 指标数据，只追加新键。"""
import json, urllib.request, time, re

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(3)

NEW = {
    "unemp":    "SL.UEM.TOTL.ZS",     # 失业率%
    "internet": "IT.NET.USER.ZS",     # 互联网普及率%
    "military": "MS.MIL.XPND.GD.ZS",  # 军费占GDP%
}

def main():
    # 读现有 EXT
    src = open('vendor/ext_indicators.js', encoding='utf-8').read()
    m = re.search(r'window\.EXT\s*=\s*(\{[\s\S]*\})', src)
    EXT = json.loads(m.group(1))
    print(f"现有 EXT: {len(EXT)} 国")

    # 从 countries_wb.js 拿 iso2 列表（214 国）
    wb_src = open('vendor/countries_wb.js', encoding='utf-8').read()
    WB = eval(re.search(r'window\.WB\s*=\s*(\{[\s\S]*\})', wb_src).group(1).replace('null', 'None'))
    iso2s = sorted(WB.keys())
    print(f"国家数: {len(iso2s)}")

    for mi, (name, code) in enumerate(NEW.items(), 1):
        batches = [iso2s[i:i+32] for i in range(0, len(iso2s), 32)]
        got = 0
        for bi, batch in enumerate(batches):
            cc = ";".join(batch)
            url = f"https://api.worldbank.org/v2/country/{cc}/indicator/{code}?format=json&per_page=1000&date=2000:2024"
            try:
                d = fetch(url)
                rows = d[1] if isinstance(d, list) and len(d) > 1 else []
            except Exception as e:
                print(f"  {name} 批次{bi} 失败: {e}")
                continue
            for r in rows:
                iso3 = r.get('countryiso3code') or (r.get('country') or {}).get('id')
                if not iso3 or r.get('value') is None:
                    continue
                # iso3→iso2：从 WB 列表构建
                EXT.setdefault(iso3, {}).setdefault(name, {})[r['date']] = r['value']
            got += len(rows)
        print(f"[{mi}/{len(NEW)}] {name}: {got} 条")
        time.sleep(2)

    # iso3→iso2 映射
    print("构建 iso3→iso2 映射...")
    cc_map = {}
    try:
        d = fetch("https://api.worldbank.org/v2/country?format=json&per_page=400")
        for c in d[1]:
            if c.get('iso2Code') and c.get('id') and len(c['id']) == 3:
                cc_map[c['id']] = c['iso2Code']
    except Exception as e:
        print("映射失败:", e)

    # 重组为 iso2 键 + 清理 None
    final = {}
    for iso3, mets in EXT.items():
        iso2 = cc_map.get(iso3, iso3)
        final[iso2] = {k: {y: v for y, v in mv.items() if v is not None}
                       for k, mv in mets.items() if mv}
    final = {k: v for k, v in final.items() if v}

    js = "/* 扩展指标（World Bank）：trade贸易占GDP% / health医疗支出占GDP% / edu教育支出占GDP% / life预期寿命 / gdpcap人均GDP(2015不变价USD) / unemp失业率% / internet互联网普及率% / military军费占GDP% */\n"
    js += "window.EXT = " + json.dumps(final, ensure_ascii=False, separators=(',', ':')) + ";\n"
    with open('vendor/ext_indicators.js', 'w', encoding='utf-8') as f:
        f.write(js)
    print(f"已写 vendor/ext_indicators.js ({len(js)} bytes, {len(final)} 国)")

if __name__ == "__main__":
    main()
