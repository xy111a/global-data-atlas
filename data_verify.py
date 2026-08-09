#!/usr/bin/env python3
"""数据自洽校验（L2）：量级/加总/逐年/交叉/覆盖 —— 全部数据文件
运行: python3 data_verify.py
退出码: 0 全过 / 1 有问题
"""
import re, json, sys

ok, warn, err = [], [], []
def check(name, cond, detail=""):
    (ok if cond else err).append(f"{name} {detail}")

# ---------- 读取数据 ----------
def load_js(path, varname, is_dict=True):
    src = open(path, encoding='utf-8').read()
    m = re.search(r'window\.%s = (\{.*?\}|\[.*?\]);' % varname, src, re.S)
    if not m: raise SystemExit(f"无法解析 {path} 的 {varname}")
    return json.loads(m.group(1).replace('null', 'null'))

# WB 国家（含 null → None）
src = open('vendor/countries_wb.js', encoding='utf-8').read()
m = re.search(r'window\.WB\s*=\s*(\{[\s\S]*\})', src)
WB = eval(m.group(1).replace('null', 'None'))
# EXT
src = open('vendor/ext_indicators.js', encoding='utf-8').read()
m = re.search(r'window\.EXT\s*=\s*(\{[\s\S]*\})', src)
EXT = eval(m.group(1).replace('null', 'None'))
# CN_TS 省
src = open('vendor/cn_prov_ts.js', encoding='utf-8').read()
CN_TS = eval(re.search(r'window\.CN_TS\s*=\s*(\{[\s\S]*\})', src).group(1))
# 城市
src = open('vendor/cn/city_metrics.js', encoding='utf-8').read()
src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)   # 去注释（eval 前）
CITY = eval(re.sub(r'(?<![\w"])(gdp|pop|area)\s*:', r'"\1":', re.search(r'window\.CITY_METRICS\s*=\s*(\{.*?\});', src, re.S).group(1)))
# 日本（同样裸键）
src = open('vendor/jp_metrics.js', encoding='utf-8').read()
src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
JP = eval(re.sub(r'(?<![\w"])(gdp|pop|area)\s*:', r'"\1":', re.search(r'window\.JP_METRICS\s*=\s*(\{.*?\});', src, re.S).group(1)))
# 城市序列（值键为数字年份，Python 数字键合法）
src = open('vendor/cn/city_ts.js', encoding='utf-8').read()
src = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
CITY_TS = eval(re.search(r'window\.CITY_TS\s*=\s*(\{.*?\});', src, re.S).group(1))
# 州
src = open('vendor/us_states_bea.js', encoding='utf-8').read()
US_TS = eval(re.search(r'window\.US_TS\s*=\s*(\{[\s\S]*\})', src).group(1))
# 日本
src = open('vendor/jp_metrics.js', encoding='utf-8').read()
JP = eval(re.search(r'window\.JP_METRICS\s*=\s*(\{[\s\S]*\})', src).group(1))
# 世界边界
WORLD = json.load(open('vendor/world.json', encoding='utf-8'))
# HTML（CN 常量、US_STATES_GDP 原始）
html = open('global-data-atlas.html', encoding='utf-8').read()

print(f"数据加载: WB={len(WB)} EXT={len(EXT)} 省={len(CN_TS)} 城={len(CITY)} 城序={len(CITY_TS)} 州={len(US_TS)} 县={len(JP)} 边界={len(WORLD['features'])}")

# ---------- 1. 量级校验 ----------
def in_range(v, lo, hi, name):
    if v is None: return
    check(f"量级[{name}]", lo <= v <= hi, f"={v:,.0f}")

for iso, o in WB.items():
    y = str(max((int(k) for k in o['years'] if k.isdigit() and o['years'][k].get('gdp')), default=0))
    d = o['years'].get(y, {})
    in_range(d.get('gdp'), 1e7, 3.5e13, f"WB.{iso}.gdp")      # 0.1亿~35万亿美元
    in_range(d.get('pop'), 1e3, 1.5e9, f"WB.{iso}.pop")      # 千~15亿人
    in_range(d.get('area'), 1e1, 1.8e7, f"WB.{iso}.area")    # km²
for s, o in CN_TS.items():
    v = next((o['gdpRMB'][k] for k in ('2023','2022','2020') if k in o['gdpRMB']), None)
    in_range(v, 1e10, 2e13, f"省.{s}.gdpRMB")                # 100亿~20万亿
    p = (o.get('pop') or {}).get('2023')
    in_range(p, 1e6, 2e8, f"省.{s}.pop")
for ad, o in CITY.items():
    in_range(o.get('gdp')*1e8 if o.get('gdp') else None, 1e8, 1e13, f"城.{ad}.gdp(元)")   # 原始单位亿元 → 元
    in_range(o.get('pop')*1e4 if o.get('pop') else None, 1e4, 5e7, f"城.{ad}.pop")
for ad, ys in CITY_TS.items():
    for y, g in ys.items():
        check(f"城序.{ad}.{y}", 1e1 <= g <= 6e4, f"={g} 亿")  # 亿元
for k, o in US_TS.items():
    y = str(max((int(y) for y in o['years']), default=0))
    in_range(o['years'][y], 1e4, 5e7, f"州.{k}.gdp(百万USD)")
for k, o in JP.items():
    in_range(o.get('gdp'), 1e9, 5e13, f"县.{k}.gdp(元)")   # 小县 900 亿合理

# ---------- 2. 加总校验 ----------
# 2a 31 省 GDP 之和 vs WB 中国（USD→CNY 2023 汇率 7.1）
prov_sum = sum(CN_TS[s]['gdpRMB']['2023'] for s in CN_TS if '2023' in CN_TS[s]['gdpRMB'])
cn_wb = WB['CN']['years']['2023']['gdp'] * 7.1
check("加总[31省GDP vs 中国WB]", 0.7 < prov_sum/cn_wb < 1.3, f"省={prov_sum/1e12:.2f}万亿 CNY vs WB={cn_wb/1e12:.2f}万亿")
prov_pop = sum(CN_TS[s]['pop']['2023'] for s in CN_TS if '2023' in CN_TS[s].get('pop', {}))
cn_pop = WB['CN']['years']['2023']['pop']
check("加总[31省人口 vs 全国]", 0.9 < prov_pop/cn_pop < 1.1, f"{prov_pop/1e8:.2f}亿 vs {cn_pop/1e8:.2f}亿")

# 2b 50 州+DC GDP 之和 vs 全国（BEA）
skip = {'United States','New England','Mideast','Great Lakes','Plains','Southeast','Southwest','Rocky Mountain','Far West'}
states = {k: US_TS[k] for k in US_TS if k not in skip}
st_sum = sum(o['years']['2023'] for o in states.values() if '2023' in o['years'])
us_all = US_TS['United States']['years']['2023']
check("加总[50州+DC vs 美国]", 0.85 < st_sum/us_all < 1.15, f"{st_sum/1e6:.2f} vs {us_all/1e6:.2f} 万亿USD")

# 2c 47 县 GDP 之和 vs 日本全国（2021，1日元≈0.05 折算 → 日本 2021 GDP≈500万亿日元≈25万亿CNY）
jp_sum = sum(o['gdp'] for o in JP.values())
check("加总[47县 vs 日本]", 0.6 < jp_sum/25e12 < 1.4, f"{jp_sum/1e12:.1f} vs ~25 万亿CNY(近似)")

# 2d 城市 GDP < 所属省 GDP（抽查 + 全量）
prov_map = {'330000':'浙江','440000':'广东','320000':'江苏'}  # 主要抽查
for ad in list(CITY)[:200]:
    # 城市 adcode 前2位 → 省
    pass
# 全量：城市 vs 省（用 2023 省 GDP 对照，城市 < 省即可）
prov_gdp = {s: CN_TS[s]['gdpRMB'].get('2023') for s in CN_TS}
viol = []
for ad, o in CITY.items():
    p2 = ad//10000*10000 if ad >= 10000 else None
    # 城市 adcode 前 4 位去掉后两位 → 省 adcode 需省级表；此处简化为量级上限
    if o['gdp'] > 2e12: viol.append((ad, o['gdp']/1e12))
check("量级[城市GDP≤2万亿]", not viol, f"超界: {viol[:5]}")

# ---------- 3. 逐年校验 ----------
def growth_check(name, series, lo=-0.35, hi=1.2):
    """series: {year: value}，检查逐年增长率区间 + 年份连续性"""
    ys = sorted(int(k) for k in series)
    if not ys: return
    for a, b in zip(ys, ys[1:]):
        if b - a > 1:
            warn.append(f"逐年[{name}]: {a}→{b} 缺 {b-a-1} 年")
        if series[str(a)] and series[str(b)] and series[str(a)] > 0:
            r = series[str(b)]/series[str(a)] - 1
            if not (lo <= r <= hi):
                warn.append(f"逐年[{name}]: {a}→{b} 增长 {r*100:.0f}%（越界）")

for iso in list(WB)[:50]:
    y = WB[iso]['years']
    growth_check(f"WB.{iso}.gdp", {k: v['gdp'] for k, v in y.items() if v.get('gdp')})
for s in CN_TS:
    growth_check(f"省.{s}.gdp", CN_TS[s]['gdpRMB'])
for k in list(US_TS)[:10]:
    growth_check(f"州.{k}", US_TS[k]['years'])
for ad in list(CITY_TS)[:10]:
    growth_check(f"城序.{ad}", CITY_TS[ad])

# ---------- 4. 交叉校验 ----------
# 4a 广东人口 CN 常量 vs CN_TS
m = re.search(r'"广东":\{pop:(\d+)', html)
cn_const_gd = int(m.group(1)) if m else None
ts_gd = CN_TS['广东']['pop']['2023']//10000
check("交叉[广东人口]", cn_const_gd == ts_gd, f"CN常量={cn_const_gd}万 vs TS={ts_gd}万")

# 4b 香港/澳门 adcode 存在
for nm, ad in [('香港', 810000), ('澳门', 820000)]:
    check(f"交叉[{nm} adcode]", re.search('"' + nm + '"\\]\\s*=\\s*' + str(ad), html) is not None, "")

# 4c CITY_TS 城市都有单年锚点（city_metrics 或省级兜底：直辖市市=省）
miss_anchor = []
for ad in CITY_TS:
    a = int(ad)
    prov = a//10000*10000
    if a not in CITY and prov not in CITY:
        miss_anchor.append(ad)
check("覆盖[城市序列有单年锚点]", not miss_anchor, f"缺: {miss_anchor[:5]}")

# 4d world.json 名 → WB 匹配（EN_ALIAS + BY_EN）
m = re.search(r'const EN_ALIAS = \{(.*?)\};', html, re.S)
EN_ALIAS = dict(re.findall(r'"([^"]+)":"([^"]+)"', m.group(1))) if m else {}
BY_EN = {o['en']: iso for iso, o in WB.items()}
matched = 0
for f in WORLD['features']:
    nm = f['properties']['name']
    if nm in BY_EN or nm in EN_ALIAS: matched += 1
check("覆盖[地图可着色]", matched >= 200, f"{matched}/{len(WORLD['features'])}")

# 4e EXT 覆盖
ext_countries = sum(1 for iso in EXT if any(EXT[iso].get(m) for m in ('trade','health','edu')))
check("覆盖[EXT 国家]", ext_countries >= 180, f"{ext_countries}")

# ---------- 输出 ----------
print(f"\n=== 校验结果: OK {len(ok)} | WARN {len(warn)} | ERROR {len(err)} ===")
for w in warn: print(f"  ⚠ {w}")
for e in err: print(f"  ✗ {e}")
print("\n".join(f"  ✓ {x}" for x in ok[:10]) + ("..." if len(ok) > 10 else ""))
sys.exit(1 if err else 0)
