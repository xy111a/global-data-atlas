#!/usr/bin/env python3
# 构建日本 47 都道府县「県内総生産（名目）」多年序列（2011-2022）
# 数据源：内阁府 ESRI 県民経済計算（免 key 直接下载 xlsx）
#   https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/tables/<年>/soukatu1.xlsx
# 单位：xlsx 中为「百万円」→ 转换与现有 JP_METRICS 一致口径为 CNY（×1e6 ×0.05）
# 输出：vendor/jp_ts.js  ->  window.JP_TS = { "北海道": {"2011": 9.26e11, ...}, ... }
import subprocess, os, sys, json, re

OUT = "vendor/jp_ts.js"
XLSX_URL = "https://www.esri.cao.go.jp/jp/sna/data/data_list/kenmin/files/contents/tables/2022/soukatu1.xlsx"
XLSX = "/tmp/soukatu1.xlsx"
JPY2CNY = 0.05  # 与 JP_METRICS 既有口径一致（1 日元≈0.05 元）


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
                # 百万円 → 円 → CNY（×1e6 ×0.05）
                series[str(y)] = round(v * 1e6 * JPY2CNY)
        if series:
            out[name] = series
    print("prefectures:", len(out))
    # 校验：北海道应有 2011
    if "北海道" in out:
        print("北海道 2011:", out["北海道"].get("2011"), "2022:", out["北海道"].get("2022"))
    return out


def emit(out):
    os.makedirs("vendor", exist_ok=True)
    lines = ["/* 日本都道府县 GDP 多年序列（2011-2022，名义，CNY 口径；源：内阁府 ESRI 県民経済計算）",
             " * 与 JP_METRICS 单年值口径一致（1日元≈0.05元）。由 build_japan_ts.py 自动生成，勿手改。 */",
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
