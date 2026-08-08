#!/usr/bin/env python3
"""合并 ext_blank_regions.json 进 countries_wb.js（CW/PS/JG）
   1. 三个区域生成 WB 结构条目：{cn, en, iso2, lat, lng, years:{yyyy:{gdp,pop,area}}}
   2. 追加进 window.WB
   3. 扩展指标并入 window.EXT（trade/health/edu/life/gdpcap）
"""
import re, json, math

def main():
    # 读现有 WB
    src = open('vendor/countries_wb.js', encoding='utf-8').read()
    m = re.search(r'window\.WB\s*=\s*(\{[\s\S]*\})', src)
    WB = eval(m.group(1).replace('null', 'None'))
    before = len(WB)

    # 读新区域
    regions = json.load(open('ext_blank_regions.json', encoding='utf-8'))

    # 元数据：cn 名、en 名、坐标（近似）
    META = {
        "CW": {"cn": "库拉索", "en": "Curacao", "lat": 12.17, "lng": -68.99},
        "PS": {"cn": "巴勒斯坦", "en": "West Bank and Gaza", "lat": 31.95, "lng": 35.23},
        "JG": {"cn": "海峡群岛", "en": "Channel Islands", "lat": 49.37, "lng": -2.36},
    }

    # EXT 结构（trade/health/edu/life/gdpcap）
    ext_src = open('vendor/ext_indicators.js', encoding='utf-8').read()
    ext_m = re.search(r'window\.EXT\s*=\s*(\{[\s\S]*\})', ext_src)
    EXT = json.loads(ext_m.group(1))

    for iso, reg in regions.items():
        if iso not in META:
            continue
        meta = META[iso]
        years = {}
        for y, vals in reg.get('years', {}).items():
            years[y] = {
                "gdp": vals.get('gdp'),
                "pop": vals.get('pop'),
                "area": vals.get('area'),
            }
        WB[iso] = {
            "cn": meta["cn"], "en": meta["en"], "iso2": iso,
            "lat": meta["lat"], "lng": meta["lng"],
            "years": years,
        }
        # 扩展指标
        ext_entry = {}
        for k in ("trade", "health", "edu", "life", "gdpcap"):
            if k in reg and reg[k]:
                ext_entry[k] = {y: v for y, v in reg[k].items() if v is not None}
        if ext_entry:
            EXT[iso] = ext_entry
        print(f"  合并 {iso} {meta['cn']}: {len(years)} 年, 扩展 {list(ext_entry.keys())}")

    # 写回 countries_wb.js（保持 JSON 结构，与原来格式一致）
    def dump_js(obj):
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))

    new_src = ("/* 国家年度数据（World Bank, 211+3 国 2000-2024）：gdp现价USD / "
               "gdpKd不变价(2015USD) / gdpPpKd不变价PPP(2017国际元) / pop / area */\n"
               "window.WB = " + dump_js(WB) + ";\n")
    open('vendor/countries_wb.js', 'w', encoding='utf-8').write(new_src)

    # 写回 EXT
    ext_src = "/* 扩展指标（World Bank）：trade贸易占GDP% / health医疗支出占GDP% / edu教育支出占GDP% / life预期寿命 / gdpcap人均GDP(2015不变价USD) */\n"
    ext_src += "window.EXT = " + json.dumps(EXT, ensure_ascii=False, separators=(',', ':')) + ";\n"
    open('vendor/ext_indicators.js', 'w', encoding='utf-8').write(ext_src)

    print(f"\nWB: {before} → {len(WB)} 国; EXT: {len(EXT)} 国")

if __name__ == "__main__":
    main()
