#!/usr/bin/env python3
"""解析维基城市 GDP wikitext（2020 链接式 + 2012 纯文本式）→ 城市多年 GDP（亿元）
   输出 vendor/cn/city_ts.js
"""
import re, json

wt = open('/tmp/citygdp_wt.txt', encoding='utf-8').read()
year_pat = re.compile(r'\n=+(\d{4})年=+\n')
matches = list(year_pat.finditer(wt))
sections = {}
for i, m in enumerate(matches):
    y = m.group(1)
    end = matches[i+1].start() if i+1 < len(matches) else len(wt)
    seg = wt[m.end():end]
    sub = re.search(r'\n==[^=]', seg)
    if sub: seg = seg[:sub.start()]
    sections[y] = seg

BLACKLIST = {'地区','位次','人民币','美元','名义增速','常住人口','大区','人口','合计','香港','澳门','台北','align','center','left','right'}

def clean(c):
    c = c.strip()
    c = re.sub(r'<ref.*?</ref>', '', c, flags=re.S)
    c = re.sub(r'<ref[^>]*/>', '', c)
    c = re.sub(r'<br\s*/?>', '', c)
    c = re.sub(r'\{\{[^}]*\}\}', '', c)
    c = c.replace('&nbsp;', '').replace("'''", '').strip()
    return c

def collect_cells(blk):
    cells = []
    for line in blk.split('\n'):
        line = line.strip()
        if not line.startswith('|') or line == '|': continue
        body = line[1:]
        if re.search(r'\[\[', body):
            cells.append(clean(body))   # 含链接整行保留
        else:
            for p in body.split('|'):
                cells.append(clean(p))
    return cells

def parse(seg):
    rows = {}
    for blk in re.split(r'\n\|-', seg):
        cells = collect_cells(blk)
        # 城市名：优先 [..市|名] 或 [..市] 链接；否则纯中文 cell（排除黑名单）
        name = None
        for c in cells:
            m = re.search(r'\[\[([^\]]+)\]\]', c)
            if m:
                full = m.group(1).split('|')[0].strip()   # 链接目标全名（上海市/华东地区）
                if full.endswith('市'):                   # 仅城市链接（排除大区等）
                    name = m.group(1).split('|')[-1].strip()
                    break
        if not name:
            for c in cells:
                if re.fullmatch(r'[\u4e00-\u9fff]{2,4}', c) and c not in BLACKLIST:
                    name = c; break
        if not name or '合计' in name or name in ('香港','澳门','台北'): continue
        nums = []
        for c in cells:
            c2 = c.replace(',', '')
            if re.fullmatch(r'\d+(\.\d+)?', c2):
                nums.append(float(c2))
        if len(nums) < 2: continue
        g = nums[1]   # 排名/位次后的第一个数值 = 人民币 GDP（亿元）
        if 100 <= g <= 60000:
            rows[name] = g
    return rows

all_city_years = {}
for y, seg in sections.items():
    r = parse(seg)
    print(f"{y}: {len(r)} 城")
    for name, g in r.items():
        all_city_years.setdefault(name, {})[y] = g

print(f"\n共 {len(all_city_years)} 城")
for name in ['上海','北京','深圳','杭州','苏州','广州','成都','武汉','南京','天津']:
    yrs = all_city_years.get(name, {})
    print(f"  {name}: { {k: round(v,1) for k,v in sorted(yrs.items())} }")

json.dump(all_city_years, open('/tmp/city_years.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
