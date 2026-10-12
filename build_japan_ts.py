#!/usr/bin/env python3
# 构建日本 47 都道府县「県内総生産（名目）」多年序列（2011-2022）
# 数据源：内阁府 ESRI 県民経済計算（免 key 直接下载 xlsx）
#   https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/tables/<年>/soukatu1.xlsx
#
# ⚠️ 货币口径（2026-10-12 修正 · 原 P0 数据缺陷）：
#   旧实现用「固定 JPY→CNY = 0.05」把 2011-2022 全部年份折成 CNY，再由 app-core 的
#   gdpApply 按「年度 USD/CNY」折成美元 —— 等价于假设 12 年间日元/人民币汇率恒定。
#   实际日元对美元 2011→2022 贬值约 39%（1USD=79.6円 → 130.7円），导致：
#     2011 年美元值低估约 38%，2022 年低估约 2.4%；
#     北海道 2011→2022 显示 +8.1%，真实美元计价为 -31.6%（增长方向相反）。
#   现改为与 build_eu_ts.py 同一范式：逐年 JPY→USD（ECB 当年日均，frankfurter）直折美元。
#
# 单位：xlsx 为「百万円」→ ×1e6 得円 → × 当年 JPY→USD → USD
# 输出：vendor/jp_ts.js -> window.JP_TS = {"北海道":{"2011":..., ...}, ...}（USD 口径）
import subprocess, os, sys, json, re

OUT = "vendor/jp_ts.js"
# 2024/2025 表尚不存在(404)；/2023/ 表虽存在但对 石川·奈良·徳島·香川·宮崎 5 县 GDP 单元格为 '-'（缺值），
# 直接用会把覆盖从 47 降到 42、破坏完整性 → 暂沿用 /2022/（2011-2022 全 47 县）。见 build 注释。
XLSX_URL = "https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/tables/2022/soukatu1.xlsx"
XLSX = "/tmp/soukatu1.xlsx"

# 逐年 JPY→USD 基线（1 日元 = ? 美元）。
# 来源：ECB 参考汇率，经 api.frankfurter.dev/v1 取当年全部交易日的算术平均，抓取于 2026-10-12。
# 内置基线保证离线可重现；联网时会尝试刷新（见 fetch_rate_map），失败则回退基线。
JPY_USD_BASELINE = {
    "2011": 0.012559, "2012": 0.012546, "2013": 0.010260, "2014": 0.009476,
    "2015": 0.008261, "2016": 0.009229, "2017": 0.008915, "2018": 0.009056,
    "2019": 0.009178, "2020": 0.009372, "2021": 0.009108, "2022": 0.007652,
    "2023": 0.007132,
}
# 对应 1 USD = ? 円（仅用于日志/校验展示）
USD_JPY_BASELINE = {y: round(1 / v, 2) for y, v in JPY_USD_BASELINE.items()}


def fetch_rate_map(years):
    """尝试联网刷新逐年 JPY→USD（ECB 日均年均）；失败回退内置基线。"""
    lo, hi = min(years), max(years)
    try:
        import urllib.request
        url = f"https://api.frankfurter.dev/v1/{lo}-01-01..{hi}-12-31?base=JPY&symbols=USD"
        # frankfurter 对无 UA 的 urllib 默认请求返回 403，需显式声明 UA
        req = urllib.request.Request(url, headers={"User-Agent": "atlas-build/1.0 (+https://atlas.huajun.wang)"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            d = json.loads(resp.read().decode("utf-8"))
        by_year = {}
        for date, v in (d.get("rates") or {}).items():
            usd = v.get("USD")
            if usd is None:
                continue
            by_year.setdefault(int(date[:4]), []).append(usd)
        rm = {str(y): sum(x) / len(x) for y, x in by_year.items() if x}
        if rm:
            print(f"  汇率刷新成功（ECB 日均年均），覆盖 {len(rm)} 年", flush=True)
            return rm
    except Exception as e:
        print(f"  [warn] 汇率刷新失败（{e}），使用内置基线", flush=True)
    return dict(JPY_USD_BASELINE)


def download():
    if os.path.exists(XLSX) and os.path.getsize(XLSX) > 1000:
        return
    print("download", XLSX_URL)
    r = subprocess.run(
        ["curl", "--noproxy", "*", "-sL", "-m", "60", "-o", XLSX, XLSX_URL],
        capture_output=True, text=True, timeout=75,
    )
    if r.returncode != 0 or os.path.getsize(XLSX) < 1000:
        sys.exit("download failed: " + r.stderr[:200])


def load_jp_names():
    """从 JP_METRICS 取 47 个规范都道府县名（与地图 properties.name 对齐）"""
    import re
    txt = open("vendor/jp_metrics.js", encoding="utf-8").read()
    return set(re.findall(r'"([^"]+)":\s*\{', txt))


# ESRI 日文县名 → 应用内中文县名（与 vendor/japan.js properties.name 一致）
JP2CN = {
    "北海道": "北海道", "青森県": "青森县", "岩手県": "岩手县", "宮城県": "宫城县",
    "秋田県": "秋田县", "山形県": "山形县", "福島県": "福岛县", "茨城県": "茨城县",
    "栃木県": "栃木县", "群馬県": "群马县", "埼玉県": "埼玉县", "千葉県": "千叶县",
    "東京都": "东京都", "神奈川県": "神奈川县", "新潟県": "新潟县", "富山県": "富山县",
    "石川県": "石川县", "福井県": "福井县", "山梨県": "山梨县", "長野県": "长野县",
    "岐阜県": "岐阜县", "静岡県": "静冈县", "愛知県": "爱知县", "三重県": "三重县",
    "滋賀県": "滋贺县", "京都府": "京都府", "大阪府": "大阪府", "兵庫県": "兵库县",
    "奈良県": "奈良县", "和歌山県": "和歌山县", "鳥取県": "鸟取县", "島根県": "岛根县",
    "岡山県": "冈山县", "広島県": "广岛县", "山口県": "山口县", "徳島県": "德岛县",
    "香川県": "香川县", "愛媛県": "爱媛县", "高知県": "高知县", "福岡県": "福冈县",
    "佐賀県": "佐贺县", "長崎県": "长崎县", "熊本県": "熊本县", "大分県": "大分县",
    "宮崎県": "宫崎县", "鹿児島県": "鹿儿岛县", "沖縄県": "冲绳县",
}


def build():
    import openpyxl
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb["実数"]  # 実数（名义 GDP）
    rows = list(ws.iter_rows(values_only=True))
    # 表头第4行：平成23(2011)...令和4(2022)；第5行是对应的公历年
    yrs = rows[4]
    # 年份列从 index 3 起
    year_cols = {}
    for i in range(3, len(yrs)):
        y = yrs[i]
        if isinstance(y, int) and 2000 <= y <= 2025:
            year_cols[i] = y
    print("years:", sorted(year_cols.values()))

    rate_map = fetch_rate_map(sorted(year_cols.values()))
    missing = [str(y) for y in year_cols.values() if str(y) not in rate_map]
    if missing:
        sys.exit(f"汇率缺失年份: {missing}")

    jp_names = load_jp_names()
    out = {}
    for r in rows[6:]:
        name = r[1]
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()
        cn = JP2CN.get(name)
        if not cn:   # 仅保留 47 真实都道府县（ESRI 日文名→中文名映射；其余为聚合行）
            continue
        name = cn
        series = {}
        for ci, y in year_cols.items():
            v = r[ci]
            if isinstance(v, (int, float)) and v > 0:
                # 百万円 → 円 → USD（×1e6 × 当年 JPY→USD）
                series[str(y)] = round(v * 1e6 * rate_map[str(y)])
        if series:
            out[name] = series
    print("prefectures:", len(out))
    # 校验：北海道应有 2011；并打印美元口径值供人工比对
    if "北海道" in out:
        h = out["北海道"]
        print(f"北海道 2011: {h.get('2011')} USD ({h.get('2011', 0)/1e8:.0f} 亿美元)"
              f" | 2022: {h.get('2022')} USD ({h.get('2022', 0)/1e8:.0f} 亿美元)")
        if h.get("2011") and h.get("2022"):
            g = (h["2022"] / h["2011"] - 1) * 100
            print(f"北海道 2011→2022 名义增长（USD 口径）: {g:+.1f}%  [修正前为 +8.1%，真实约 -31.6%]")
    return out


def emit(out):
    os.makedirs("vendor", exist_ok=True)
    yrs = sorted({y for s in out.values() for y in s}, key=int)
    rate_line = ", ".join(f"{y}:{USD_JPY_BASELINE.get(y,'?')}" for y in yrs if y in USD_JPY_BASELINE)
    lines = ["/* 日本都道府县 GDP 多年序列（" + yrs[0] + "-" + yrs[-1] + "，名义，USD 口径；源：内阁府 ESRI 県民経済計算）",
             " * 汇率：逐年 JPY→USD（ECB 当年日均年均，frankfurter）；1USD≈" + rate_line + " 円",
             " * ⚠️ 2026-10-12 修正：旧版用固定 JPY→CNY=0.05 再按年度 USD/CNY 折算，等价于假设日/中汇率恒定，",
             " *    导致 2011 年美元值低估约 38%、增长方向失真（北海道 +8.1% vs 真实 -31.6%）。现直折逐年 USD。",
             " * 由 build_japan_ts.py 自动生成，勿手改。 */",
             "window.JP_TS = {"]
    items = []
    for k in sorted(out.keys()):
        s = out[k]
        inner = ", ".join(f'"{y}":{s[y]}' for y in sorted(s.keys(), key=int))
        items.append(f'"{k}":{{{inner}}}')
    lines.append(",\n".join(items))
    lines.append("};")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    download()
    emit(build())
