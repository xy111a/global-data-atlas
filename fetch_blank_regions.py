#!/usr/bin/env python3
"""拉取 9 个缺失区域（WB 有数据但 countries_wb.js 没有）的核心指标
   区域: Aland(芬兰奥兰群岛)、Curaçao、Jersey、Palestine、Saint Helena、
         Montserrat、Niue、Falkland Is.、St. Pierre and Miquelon
   输出: 生成 ext_blank_regions.json 供后续合并
"""
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

# WB 国家列表找这些区域的 iso2/en 名
def find_regions():
    d = fetch("https://api.worldbank.org/v2/country?format=json&per_page=400")
    regions = {}
    for c in d[1]:
        nm = c.get('name', '')
        if any(k in nm.lower() for k in ['aland', 'curacao', 'jersey', 'palestine',
                                          'saint helena', 'montserrat', 'niue',
                                          'falkland', 'pierre and miquelon', 'west bank']):
            regions[c.get('iso2Code')] = c.get('name')
    return regions

# 指标
IND = {
    "gdp":   "NY.GDP.MKTP.CD",     # GDP 现价 USD
    "pop":   "SP.POP.TOTL",        # 人口
    "area":  "AG.SRF.TOTL.K2",     # 面积 km²
    "trade": "NE.TRD.GNFS.ZS",
    "health":"SH.XPD.CHEX.GD.ZS",
    "edu":   "SE.XPD.TOTL.GD.ZS",
    "life":  "SP.DYN.LE00.IN",
    "gdpcap":"NY.GDP.PCAP.KD",
}

def main():
    regions = find_regions()
    print("找到区域:", json.dumps(regions, ensure_ascii=False))
    iso2s = list(regions.keys())
    out = {}
    for iso2 in iso2s:
        out[iso2] = {"name": regions[iso2], "years": {}}
        # 先取 GDP/人口/面积（现价 USD GDP）
        cc = iso2.lower()
        for mi, (name, code) in enumerate(IND.items()):
            url = f"https://api.worldbank.org/v2/country/{cc}/indicator/{code}?format=json&per_page=1000&date=2000:2024"
            try:
                d = fetch(url)
                rows = d[1] if isinstance(d, list) and len(d) > 1 else []
            except Exception as e:
                print(f"  {iso2} {name} 失败: {e}")
                continue
            for r in rows:
                y = r['date']
                v = r.get('value')
                if v is None:
                    continue
                if name in ("gdp","pop","area"):
                    out[iso2]["years"].setdefault(y, {})[name] = v
                else:
                    out[iso2].setdefault(name, {})[y] = v
            time.sleep(0.5)
        print(f"  {iso2} {regions[iso2]}: {len(out[iso2]['years'])} 年 GDP/人口/面积, 扩展指标 {[k for k in out[iso2] if k not in ('name','years')]}")
    json.dump(out, open('ext_blank_regions.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print("已写 ext_blank_regions.json")

if __name__ == "__main__":
    main()
