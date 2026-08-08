#!/usr/bin/env python3
"""检查 ext_indicators.js 数据质量"""
import re, json

src = open('vendor/ext_indicators.js', encoding='utf-8').read()
m = re.search(r'window\.EXT\s*=\s*(\{[\s\S]*\})', src)
EXT = json.loads(m.group(1))

print(f"国家数: {len(EXT)}")
for iso, mets in list(EXT.items())[:5]:
    print(f"  {iso}: { {k: len(v) for k, v in mets.items()} }")

# 覆盖统计
metrics = ['trade', 'health', 'edu', 'life', 'gdpcap']
for met in metrics:
    n = sum(1 for iso, mets in EXT.items() if met in mets and mets[met])
    yrs = set()
    for iso, mets in EXT.items():
        if met in mets:
            yrs.update(int(y) for y in mets[met])
    print(f"{met}: {n} 国有数据, 年份 {min(yrs) if yrs else '-'}-{max(yrs) if yrs else '-'}")

# 中国数据示例
print("\n中国 CN:", json.dumps({k: {y: v for y, v in v.items() if y in ('2000','2010','2020','2023')} for k, v in EXT.get('CN', {}).items()}, ensure_ascii=False)[:500])
print("\n美国 US:", {k: v.get('2023') for k, v in EXT.get('US', {}).items()})
