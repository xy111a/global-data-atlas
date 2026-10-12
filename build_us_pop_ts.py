#!/usr/bin/env python3
# 构建美国 51 州+DC 人口多年序列
#
# 主源（免 key、权威）：U.S. Census Bureau Population Estimates Program (PEP)
#   静态发布目录，无需 API key、无需代理白名单：
#   https://www2.census.gov/programs-surveys/popest/datasets/<2020-YEAR>/state/totals/NST-EST<YEAR>-ALLDATA.csv
#   SUMLEV=040 为州级行；列为每年 7 月 1 日估计 POPESTIMATE<YEAR>（Vintage 2025 → 2020–2025）。
#   口径一致（同一「7 月 1 日」基准），适合逐年序列与人均 GDP(gdppc) 现算。
#
# 备源（旧维基表）：英文维基《List of U.S. states and territories by population》wikitext，
#   仅含 2020 普查(4/1) + 2025 估算，**无 2021–2024**。仅在 Census 不可达时整体兜底。
#   注意该源 2020 是 4 月 1 日普查数，与 Census 的 7 月 1 日估计基准不同，
#   两源混用会在 2020↔2021 引入一个季度的口径断点，故只作整体兜底、不逐年拼接。
#
# 2026-10-12 变更：原实现只解析维基 section 标记 → 序列退化为稀疏的 2020+2025，
#   且 Utah 因源转译模板缺 UT_2025 标记而缺 2025。改用 Census PEP 后为 2020–2025 逐年
#   完整序列（52 行州级齐全，Utah 补齐），人均 GDP 在中段年份不再靠"就近年份回退"硬凑。
#   ⚠️ api.census.gov 需注册 key（响应头 X-DataWebAPI-KeyError: 1），故走静态目录而非 API。
#
# 输出：vendor/us_pop_ts.js -> window.US_POP_TS = { "Alabama": {"2020":..., ..., "2025":...}, ... }
import csv
import io
import json
import os
import re
import subprocess

OUT = "vendor/us_pop_ts.js"
CENSUS_DIR = "https://www2.census.gov/programs-surveys/popest/datasets/{ds}/state/totals/NST-EST{v}-ALLDATA.csv"
# 倒序尝试：优先最新 vintage（覆盖年份最多）
CENSUS_VINTAGES = [("2020-2025", 2025), ("2020-2024", 2024)]
# 属地：有数据、官方 US 合计不含 → 加总自检时须剔除
NON_STATES = {"Puerto Rico"}
WIKI_URL = ("https://en.wikipedia.org/w/api.php?action=parse"
            "&page=List_of_U.S._states_and_territories_by_population&prop=wikitext&format=json")

USPS = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


def valid_states():
    """US_STATES_GDP（app-core.js）里真实存在的州名 → 只保留有 GDP 数据的州。"""
    txt = open("vendor/app-core.js", encoding="utf-8").read()
    return set(re.findall(r'"([A-Za-z ][A-Za-z .]*?)":\s*\{\s*gdpUsdM', txt))


def curl(url, timeout=60):
    r = subprocess.run(["curl", "--noproxy", "*", "-sL", "-m", str(timeout), url],
                       capture_output=True, text=True, timeout=timeout + 15)
    if r.returncode != 0:
        raise RuntimeError(f"curl exit {r.returncode}: {r.stderr[:160]}")
    return r.stdout


def from_census(valid):
    """解析 Census PEP 静态 CSV：SUMLEV=040 州级行 → {州名: {年: 人口}}"""
    last_err = None
    for ds, v in CENSUS_VINTAGES:
        url = CENSUS_DIR.format(ds=ds, v=v)
        print(f"  试 Census Vintage {v} …")
        try:
            raw = curl(url)
        except Exception as e:                                   # 网络不可达 → 试下一 vintage
            last_err = e
            print(f"    取回失败：{e}")
            continue
        if not raw.lstrip().startswith("SUMLEV"):
            last_err = RuntimeError("响应不是 CSV（可能被拦截）")
            print("    响应不是 CSV，跳过")
            continue
        rd = csv.DictReader(io.StringIO(raw))
        years = sorted({k for k in (rd.fieldnames or []) if re.fullmatch(r"POPESTIMATE\d{4}", k)})
        out, total = {}, None
        for row in rd:
            name = (row.get("NAME") or "").strip()
            if row.get("SUMLEV") == "010":                       # 美国合计（仅用于校验）
                total = row
                continue
            if row.get("SUMLEV") != "040" or name not in valid:
                continue
            series = {}
            for k in years:
                val = (row.get(k) or "").strip().replace(",", "")
                if val.isdigit():
                    series[k.replace("POPESTIMATE", "")] = int(val)
            if series:
                out[name] = series
        if len(out) < 45:                                        # 州数明显不对 → 视为解析失败
            last_err = RuntimeError(f"仅解析到 {len(out)} 州")
            print(f"    仅 {len(out)} 州，判定异常")
            continue
        # 口径自检：50 州+DC 加总应≈官方美国合计（±0.5%），防止列错位/静默截断。
        # ⚠️ Puerto Rico 等属地存在于 US_STATES_GDP，但**不计入**官方 US 合计(SUMLEV=010)，
        #    求和须剔除，否则恒定偏高约 0.93%（=PR 318万/美国 3.42亿）而误判为坏数据。
        # ⚠️ 键名坑：years[] 已是 'POPESTIMATE2025'，不能再拼前缀；
        #    而 out 的序列键是纯年份 '2025'，两者不同源，必须分别取。
        if total and years:
            uyear = years[-1].replace("POPESTIMATE", "")
            us_last = (total.get(years[-1]) or "").strip().replace(",", "")
            s_last = sum(s.get(uyear, 0) for k, s in out.items() if k not in NON_STATES)
            if us_last.isdigit() and int(us_last):
                dev = abs(s_last - int(us_last)) / int(us_last)
                print(f"    加总自检 {uyear}（已剔除属地）：{s_last:,} vs 官方 {int(us_last):,}，偏差 {dev:.4%}")
                if dev > 0.005:
                    last_err = RuntimeError(f"加总偏差 {dev:.2%} 超阈值")
                    continue
        print(f"  ✓ Census Vintage {v}：{len(out)} 州 × {len(years)} 年（{years[0]}–{years[-1]}）")
        return out
    raise RuntimeError(f"Census 全部 vintage 失败：{last_err}")


def from_wiki(valid):
    """兜底：英文维基 section 标记（仅 2020 普查 + 2025 估算，稀疏）"""
    print("  回落维基…")
    wt = json.loads(curl(WIKI_URL, timeout=55))["parse"]["wikitext"]["*"]
    pat = re.compile(r'<section begin=(\w+)_(\d{4})/>([\d,]+)<section end=\1_\2/>')
    raw = {}
    for code, year, num in pat.findall(wt):
        nm = USPS.get(code)
        if nm in valid:
            raw.setdefault(nm, {})[year] = int(num.replace(",", ""))
    return {k: v for k, v in raw.items() if k in valid}


def emit(out, source):
    years = sorted({y for s in out.values() for y in s})
    span = f"{years[0]}–{years[-1]}" if len(years) > 1 else years[0]
    head = (
        "/* 美国州人口多年序列\n"
        f" * 来源：{source}\n"
        f" * 覆盖：{len(out)} 州+DC，{span} 逐年（共 {len(years)} 个数据点）\n"
        " * 由 build_us_pop_ts.py 自动生成，勿手改。 */\n"
    )
    items = []
    for k in sorted(out):
        inner = ", ".join(f'"{y}":{out[k][y]}' for y in sorted(out[k]))
        items.append(f'"{k}":{{{inner}}}')
    os.makedirs("vendor", exist_ok=True)
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(head + "window.US_POP_TS = {\n" + ",\n".join(items) + "\n};\n")
    os.replace(tmp, OUT)
    print(f"  → 写入 {OUT}（{os.path.getsize(OUT)} bytes）")


if __name__ == "__main__":
    valid = valid_states()
    print(f"US_STATES_GDP 中的州：{len(valid)}")
    try:
        data = from_census(valid)
        src = ("U.S. Census Bureau PEP 静态发布目录（免 key）；各年为 7 月 1 日估计，逐年同基准")
    except Exception as e:
        print(f"! Census 不可用：{e}")
        data = from_wiki(valid)
        src = "英文维基《List of U.S. states and territories by population》"
    missing = valid - set(data)
    if missing:
        print(f"! 缺 {len(missing)} 州：{sorted(missing)[:6]}")
    print(f"最终 {len(data)} 州；样本：")
    for s in ("California", "Utah", "Texas", "District of Columbia"):
        if s in data:
            print(f"  {s}: {data[s]}")
    emit(data, src)
