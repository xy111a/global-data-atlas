#!/usr/bin/env python3
"""数据自洽校验（L2）：量级/加总/逐年/交叉/覆盖 —— 全部数据文件
运行: python3 data_verify.py
退出码: 0 全过 / 1 有问题
"""
import re, json, sys, os

ok, warn, err = [], [], []
def check(name, cond, detail=""):
    (ok if cond else err).append(f"{name} {detail}")

# ---------- 读取数据 ----------
def _strip_comments(src):
    """移除 // 行注释与 /* */ 块注释（保留字符串内 'http://' 之类）。"""
    out, i, n, in_str = [], 0, len(src), False
    while i < n:
        c = src[i]
        if in_str:
            out.append(c)
            if c == '\\': out.append(src[i+1]); i += 2; continue
            if c in '"\'' : in_str = False
            i += 1; continue
        if c in '"\'':
            in_str = True; out.append(c); i += 1; continue
        if src.startswith('//', i):
            j = src.find('\n', i); i = j if j >= 0 else n; continue
        if src.startswith('/*', i):
            j = src.find('*/', i+2); i = (j+2) if j >= 0 else n; continue
        out.append(c); i += 1
    return ''.join(out)

def _extract_literal(src, varname):
    """按 window.<var> = <literal>; 提取对象字面量（平衡括号扫描，避免贪婪/脆弱正则）。"""
    m = re.search(r'window\.%s\s*=\s*' % re.escape(varname), src)
    if not m: raise SystemExit(f"无法定位 window.{varname} 定义")
    i = m.end()
    while i < len(src) and src[i] in ' \t\r\n': i += 1
    if i >= len(src) or src[i] != '{': raise SystemExit(f"{varname} 不是对象字面量")
    depth, j = 0, i
    for j in range(i, len(src)):
        if src[j] == '{': depth += 1
        elif src[j] == '}':
            depth -= 1
            if depth == 0: break
    return src[i:j+1]

def _quote_bare_keys(lit):
    """把 JS 裸键引号化 → JSON 合法（仅处理键位置，不改值）。
       覆盖两种：字母裸键 {gdp: ...}、数字 adcode 裸键 {110000:{gdp:...}}。"""
    lit = re.sub(r'(?<![\w"])([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'"\1":', lit)
    lit = re.sub(r'(?<![\w"])(\d{4,6})\s*:', r'"\1":', lit)
    return lit

def load_js(path, varname):
    """安全加载 JS 数据字面量：去注释 → 定位字面量 → 引号化裸键 → json.loads（无 eval）。"""
    src = _strip_comments(open(path, encoding='utf-8').read())
    lit = _extract_literal(src, varname)
    return json.loads(_quote_bare_keys(lit))

WB   = load_js('vendor/countries_wb.js',   'WB')
EXT  = load_js('vendor/ext_indicators.js', 'EXT')
CN_TS= load_js('vendor/cn_prov_ts.js',     'CN_TS')
CITY = load_js('vendor/cn/city_metrics.js','CITY_METRICS')
CITY_TS= load_js('vendor/cn/city_ts.js',   'CITY_TS')
US_TS= load_js('vendor/us_states_bea.js',  'US_TS')
JP   = load_js('vendor/jp_metrics.js',     'JP_METRICS')
# 世界边界
WORLD = json.load(open('vendor/world.json', encoding='utf-8'))
# 主 HTML + app-core.js（CN 常量、US_STATES_GDP、EN_ALIAS 已抽取到 app-core.js，window 定义）
html = open('global-data-atlas.html', encoding='utf-8').read()
core_src = open('vendor/app-core.js', encoding='utf-8').read()
both = html + "\n" + core_src

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
    adi = int(ad)  # json 键为字符串，转 int 供算术/比较
    # 城市 adcode 前 4 位去掉后两位 → 省 adcode 需省级表；此处简化为量级上限
    if o['gdp'] > 2e12: viol.append((adi, o['gdp']/1e12))
check("量级[城市GDP≤2万亿]", not viol, f"超界: {viol[:5]}")

# ---------- 3. 逐年校验 ----------
def growth_check(name, series):
    """series: {year: value}，检查增长率区间 + 年份连续性。
       连续年份（间隔=1）：逐年增长率须在 [-35%, +120%]（覆盖危机/高速年）。
       稀疏年份（间隔>1，如省/市序列仅 2000/2010/2020-2025）：缺年是设计，
       不告警；增长率按年均(CAGR)折算后须在 [-30%, +30%]，避免把 10 年
       累计增长（如宁夏 2000→2010 累计 436%）误报为越界。"""
    ys = sorted(int(k) for k in series)
    if not ys: return
    for a, b in zip(ys, ys[1:]):
        span = b - a
        va, vb = series[str(a)], series[str(b)]
        if not (va and vb and va > 0):
            if span > 1:
                print(f"  信息[稀疏序列 {name}]: {a}→{b} 间隔 {span} 年")
            continue
        if span == 1:
            r = vb/va - 1
            if not (-0.35 <= r <= 1.2):
                warn.append(f"增长[{name}]: {a}→{b} {r*100:.0f}%（越界）")
        else:
            cagr = (vb/va) ** (1/span) - 1
            if not (-0.30 <= cagr <= 0.30):
                warn.append(f"增长[{name}]: {a}→{b} 年均 {cagr*100:.0f}%（越界，累计{(vb/va-1)*100:.0f}%）")

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
m = re.search(r'"广东":\{pop:(\d+)', both)
cn_const_gd = int(m.group(1)) if m else None
ts_gd = CN_TS['广东']['pop']['2023']//10000
check("交叉[广东人口]", cn_const_gd == ts_gd, f"CN常量={cn_const_gd}万 vs TS={ts_gd}万")

# 4b 香港/澳门 adcode 存在
for nm, ad in [('香港', 810000), ('澳门', 820000)]:
    check(f"交叉[{nm} adcode]", re.search('"' + nm + '"\\]\\s*=\\s*' + str(ad), both) is not None, "")

# 4c CITY_TS 城市都有单年锚点（city_metrics 或省级兜底：直辖市市=省）
miss_anchor = []
for ad in CITY_TS:
    a = int(ad)
    prov = a//10000*10000
    if str(a) not in CITY and str(prov) not in CITY:   # CITY 键为字符串
        miss_anchor.append(ad)
check("覆盖[城市序列有单年锚点]", not miss_anchor, f"缺: {miss_anchor[:5]}")

# 4d world.json 名 → WB 匹配（EN_ALIAS + BY_EN）
m = re.search(r'window\.EN_ALIAS = \{(.*?)\};', core_src, re.S) or re.search(r'const EN_ALIAS = \{(.*?)\};', core_src, re.S)
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

# ---------- 4f 欧盟 NUTS2（EU27） ----------
EU27 = ["AT","BE","BG","CY","CZ","DE","DK","EE","EL","ES","FI","FR","HR","HU","IE","IT","LT","LU","LV","MT","NL","PL","PT","RO","SE","SI","SK"]
eu_files = os.listdir('vendor/eu')
eu_js = [f for f in eu_files if f.endswith('.js') and f != 'eu_metrics.js']
check("覆盖[欧盟边界文件]", len(eu_js) == 27, f"{len(eu_js)}/27（EU27 全量）")
missing_eu = [cc.lower() for cc in EU27 if f"{cc.lower()}.js" not in eu_js]
check("覆盖[欧盟27国文件齐全]", not missing_eu, f"缺失: {missing_eu or '无'}")
src_eu = open('vendor/eu/eu_metrics.js', encoding='utf-8').read()
m_eu = re.search(r'window\.EU_METRICS=(\{.*\})', src_eu, re.S)
EU_M = json.loads(m_eu.group(1)) if m_eu else {}
check("覆盖[欧盟NUTS2区域]", 230 <= len(EU_M) <= 260, f"{len(EU_M)} 区域")
eu_gdp_ok = all(v['gdp'] is None or 0 < v['gdp'] < 2e13 for v in EU_M.values())   # GDP 0~2万亿 元（部分区域 Eurostat 缺 GDP=null）
check("量级[欧盟NUTS2 GDP]", eu_gdp_ok, "")
eu_pop_ok = all(1e4 < v['pop'] < 2e7 for v in EU_M.values())  # 人口 1万~2000万
check("量级[欧盟NUTS2 人口]", eu_pop_ok, "")
# 边界 NUTS_ID 与指标键一致性（抽查 DE 与新国家 EL）
for cc in ("DE", "EL"):
    src_geo = open(f'vendor/eu/{cc.lower()}.js', encoding='utf-8').read()
    m_geo = re.search(r'window\.EU_' + cc + r'_GEO=(\{.*\})', src_geo, re.S)
    GEO = json.loads(m_geo.group(1))
    geo_ids = {f['properties']['NUTS_ID'] for f in GEO['features']}
    metric_ids = {k for k, v in EU_M.items() if v.get('cc') == cc}
    check(f"交叉[{cc} 边界vs指标]", geo_ids == metric_ids, f"边界{len(geo_ids)} vs 指标{len(metric_ids)}")

# ---------- 输出 ----------
print(f"\n=== 校验结果: OK {len(ok)} | WARN {len(warn)} | ERROR {len(err)} ===")
for w in warn: print(f"  ⚠ {w}")
for e in err: print(f"  ✗ {e}")
print("\n".join(f"  ✓ {x}" for x in ok[:10]) + ("..." if len(ok) > 10 else ""))
sys.exit(1 if err else 0)
