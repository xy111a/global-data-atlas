#!/usr/bin/env python3
"""测试 WB 经典指标代码的数据可用性（国家层，2000-2024）"""
import json, urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'curl/8.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode())

INDICATORS = {
    "trade":   "NE.TRD.GNFS.ZS",   # 贸易占 GDP %（出口+进口）
    "health":  "SH.XPD.CHEX.GD.ZS",# 医疗支出占 GDP %
    "edu":     "SE.XPD.TOTL.GD.ZS",# 教育支出占 GDP %
    "life":    "SP.DYN.LE00.IN",   # 预期寿命（岁）
    "gdpcap":  "NY.GDP.PCAP.KD",   # 人均 GDP 不变价
}

for name, code in INDICATORS.items():
    try:
        d = fetch(f"https://api.worldbank.org/v2/country/CN;US;JP;DE/indicator/{code}?format=json&per_page=200&date=2000:2024")
        if isinstance(d, list) and len(d) > 1:
            rows = d[1]
            sample = [r for r in rows if r.get('value') is not None][:2]
            print(f"{name:8} ({code}): {len(rows)} 条数据")
            for r in sample:
                print(f"           {r['country']['value']} {r['date']} = {r['value']}")
        else:
            print(f"{name:8} ({code}): 无数据")
    except Exception as e:
        print(f"{name:8} ({code}): 请求失败 {e}")
