#!/usr/bin/env python3
"""抽取 app-core.js：从 global-data-atlas.html 主 script 提取核心层（纯数据/逻辑，无 DOM）。
   const 常量改为 window.X 暴露（跨 script 共享）；函数声明保持（全局共享）。
   用法：python3 extract_core.py  → 生成 vendor/app-core.js + 备份主 HTML"""
import re, shutil

SRC = "global-data-atlas.html"
BACKUP = "global-data-atlas.html.bak"
CORE_OUT = "vendor/app-core.js"

html = open(SRC, encoding="utf-8").read()
shutil.copy(SRC, BACKUP)

# 主 script 块（最后一个无 src 的大 script）
scripts = re.findall(r'<script>(.*?)</script>', html, re.S)
main = scripts[-1]
main_start = html.rfind("<script>")   # 主 script 起点

# ---------- 核心函数列表（括号匹配提取） ----------
CORE_FUNCS = [
    "enToWb","wbForMapName","fmtPct","esc","metricLabel","metricFmt","metricScope",
    "metricUnavailableMsg","cMetric","cYear","cGrowth","fmtGrowth","fmtGrowthFor",
    "usGdpUsdM","usGdpY","usGdpYear","usGdpUsdT","usNominalGrowth",
    "cnGdpRMB","cnGdpYear","cnNominalGrowth","fmtGDP","fmtPop","fmtArea","normProv",
    "regCountry","regProv","regUSState","regCity","regJapanPref","regNUTS","regGet",
    "countryTrend","provTrend","usTrend","currencyTag","getCityMetric","euCCName",
    "fmtBy","usVal","cmpGetData"
]

def extract_func(text, fname):
    """括号匹配提取 function fname 的完整定义"""
    m = re.search(r'function %s\s*\(' % re.escape(fname), text)
    if not m:
        return None
    i = m.start()
    # 找第一个 {
    j = text.find("{", i)
    depth = 0
    k = j
    while k < len(text):
        if text[k] == "{": depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[i:k+1]
        k += 1
    return None

# 提取所有核心函数
core_code = []
for f in CORE_FUNCS:
    body = extract_func(main, f)
    if body:
        core_code.append(body)
        # 标记已提取（从 main 移除）
        main = main.replace(body, "", 1)
    else:
        print(f"⚠️ 未找到函数: {f}")

# ---------- 核心常量（const → window.X） ----------
CONST_DEFS = [
    ("COUNTRIES", False), ("BY_EN", False),
    ("EN_ALIAS", True), ("METRICS", True), ("USD_CNY", False),
    ("CN", True), ("PROV_ADCODE", True),
    ("US_STATES_GDP", True), ("RATE23", False),
]
core_const = []
for name, is_obj in CONST_DEFS:
    m = re.search(r'const %s\s*=\s*' % re.escape(name), main)
    if not m:
        print(f"⚠️ 未找到常量: {name}")
        continue
    i = m.start()
    if is_obj:
        # 对象：从 = 后的第一个 { 括号匹配到闭合 }
        j = main.find("{", m.end())
        if j < 0:
            print(f"⚠️ 常量 {name} 无对象起点")
            continue
        depth = 0
        k = j
        while k < len(main):
            if main[k] == "{": depth += 1
            elif main[k] == "}":
                depth -= 1
                if depth == 0:
                    k += 1
                    break
            k += 1
        semi = main.find(";", k)
        block = main[i:semi+1]
    else:
        semi = main.find(";", i)
        block = main[i:semi+1]
    # 转 window 暴露：const X = → window.X =
    core_const.append(block.replace(f"const {name} =", f"window.{name} =", 1))
    main = main.replace(block, "", 1)

# ---------- 组装 app-core.js ----------
header = """/* ============== app-core.js 核心数据/逻辑层（两页共享） ==============
   从 global-data-atlas.html 抽取：指标注册表 METRICS / 区域统一接口 reg* /
   数据取数 / 格式化 / 常量。对比页 compare.html 与主页面共用。
   依赖：vendor/ 数据文件（world.js, countries_wb.js, fxrate.js, ext_indicators.js,
   cn_prov_ts.js, us_states_bea.js, jp_metrics.js, cn/city_metrics.js, eu/eu_metrics.js）
   需在数据文件之后加载。
   ⚠️ 修改此处后需同步主页面；用 extract_core.py 重新生成时勿手工编辑此文件。 */
"""
core_out = header + "\n".join(core_const) + "\n\n" + "\n".join(core_code) + "\n"
open(CORE_OUT, "w", encoding="utf-8").write(core_out)
print(f"✅ 生成 {CORE_OUT} ({len(core_code)} 函数 + {len(core_const)} 常量, {len(core_out)//1024}KB)")

# ---------- 更新主 HTML：删除已提取代码 + 加 app-core.js 引用 ----------
# 主 script 现在不含 core（main 已移除），重写 HTML
new_html = html[:main_start] + "<script>" + main + "</script></body></html>"
# 在数据 script 后插入 app-core.js（fxrate.js 后）
new_html = new_html.replace('<script src="vendor/fxrate.js"></script>',
                            '<script src="vendor/fxrate.js"></script>\n<script src="vendor/app-core.js"></script>', 1)
open(SRC, "w", encoding="utf-8").write(new_html)
print(f"✅ 主 HTML 已更新（移除 core 代码，引用 app-core.js）；备份: {BACKUP}")
