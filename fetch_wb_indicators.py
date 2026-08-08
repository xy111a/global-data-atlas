#!/usr/bin/env python3
"""查询 World Bank 可用指标（贸易/医疗/教育/预期寿命），确认新维度数据可接入"""
import json, urllib.request

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'curl/8.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

def main():
    d = fetch("https://api.worldbank.org/v2/indicator?format=json&per_page=300")
    items = d[1] if isinstance(d, list) and len(d) > 1 else []
    print(f"总指标数(前300): {len(items)}")
    keys = ['trade', 'Trade', 'health', 'Health', 'education', 'Education',
            'Life expectancy', 'life expectancy', 'export', 'Export', 'import', 'Import',
            'GDP per capita', 'Unemployment', 'unemployment', 'CO2', 'Internet',
            'Renewable', 'renewable']
    seen = set()
    for it in items:
        n = it.get('name', '')
        if any(k in n for k in keys) and it['id'] not in seen:
            seen.add(it['id'])
            print(f"{it['id']} | {n[:75]}")
    print(f"\n命中 {len(seen)} 个指标")

if __name__ == "__main__":
    main()
