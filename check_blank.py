#!/usr/bin/env python3
"""排查：world.json 有边界但无数据（空白）的区域
   匹配链：world.json name → enToWb(别名) → WB[iso2]
"""
import re, json

def main():
    # 1. world.json 边界
    gj = json.load(open('vendor/world.json', encoding='utf-8'))
    features = gj['features']
    print(f"world.json 边界区域数: {len(features)}")

    # 2. WB 数据（JS 字面量，用 eval 解析）
    src = open('vendor/countries_wb.js', encoding='utf-8').read()
    WB = eval(re.search(r'window\.WB\s*=\s*(\{[\s\S]*\})', src).group(1).replace('null', 'None'))
    # en → iso2
    by_en = {}
    for iso2, o in WB.items():
        by_en[o['en']] = iso2
        if o.get('cn'):
            by_en.setdefault(o['cn'], iso2)
    print(f"WB 国家数: {len(WB)}")

    # 3. EN_ALIAS 别名表（从 HTML 提取）
    html = open('global-data-atlas.html', encoding='utf-8').read()
    m = re.search(r'const EN_ALIAS = \{(.*?)\};', html, re.S)
    aliases = {}
    if m:
        for k, v in re.findall(r'"([^"]+)":"([^"]+)"', m.group(1)):
            aliases[k] = v
    print(f"EN_ALIAS 别名数: {len(aliases)}")

    # 4. 逐个边界匹配
    matched, unmatched = [], []
    for f in features:
        nm = f['properties']['name']
        en = aliases.get(nm, nm)
        iso2 = by_en.get(en)
        if iso2:
            matched.append((nm, iso2))
        else:
            unmatched.append(nm)

    print(f"\n可着色(有数据): {len(matched)}")
    print(f"空白(无数据): {len(unmatched)}")
    print("\n=== 空白区域明细 ===")
    for nm in unmatched:
        # 尝试模糊匹配提示
        hint = fuzzy(nm, list(by_en.keys()))
        print(f"  {nm}" + (f"  → 疑似 {hint}" if hint else ""))

def fuzzy(nm, candidates):
    """简单相似度：小写包含/首词匹配"""
    nm_l = nm.lower()
    for c in candidates:
        c_l = c.lower()
        if nm_l in c_l or c_l in nm_l:
            return c
        # 去括号/去修饰
        if nm_l.split('(')[0].strip() == c_l.split('(')[0].strip():
            return c
    return None

if __name__ == "__main__":
    main()
