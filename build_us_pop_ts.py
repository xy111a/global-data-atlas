#!/usr/bin/env python3
# 构建美国 50 州人口多年序列（来源：Wikipedia "List of U.S. states and territories by population"）
# 该表以 <section begin=XX_YYYY/>数字<section end=XX_YYYY/> 标记各州各年人口（普查/估算），
# 目前可得年份：2020（普查）、2025（最新估算）。产出稀疏多年序列（诚实标注为 census+estimate）。
# 输出：vendor/us_pop_ts.js -> window.US_POP_TS = { "Alabama": {"2020": 5024279, "2025": 5193088}, ... }
import subprocess, os, re, sys, json

OUT = "vendor/us_pop_ts.js"
URL = "https://en.wikipedia.org/w/api.php?action=parse&page=List_of_U.S._states_and_territories_by_population&prop=wikitext&format=json"

# USPS 2字母州码 -> 州名（与 US_STATES_GDP key 一致）
USPS = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado",
    "CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho",
    "IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
    "ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi",
    "MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey",
    "NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma",
    "OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota",
    "TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington",
    "WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia",
}


def fetch():
    print("fetch", URL[:60], "...")
    r = subprocess.run(["curl","--noproxy","*","-sL","-m","40",URL], capture_output=True, text=True, timeout=55)
    if r.returncode != 0:
        sys.exit("fetch failed: " + r.stderr[:200])
    return json.loads(r.stdout)["parse"]["wikitext"]["*"]


def build(t):
    # 解析所有 <section begin=CODE_YYYY/>NUMBER<section end=CODE_YYYY/>
    pat = re.compile(r'<section begin=(\w+)_(\d{4})/>([\d,]+)<section end=\1_\2/>')
    raw = {}
    for code, year, num in pat.findall(t):
        name = USPS.get(code)
        if not name:
            continue
        raw.setdefault(name, {})[year] = int(num.replace(",", ""))
    # 仅保留 US_STATES_GDP 中存在的州
    import re as _re
    txt = open("vendor/app-core.js", encoding="utf-8").read()
    valid = set(_re.findall(r'^\s*"(Alabama|Alaska|[\w ]+)":\s*\{', txt))
    # 用更稳的方式：直接 require 不行（node），改为读取 US_STATES_GDP 字面量键
    valid = set(_re.findall(r'"([A-Za-z ][A-Za-z .]*?)":\s*\{\s*gdpUsdM', txt))
    out = {n: s for n, s in raw.items() if n in valid}
    print("states with pop series:", len(out))
    if "Alabama" in out:
        print("Alabama:", out["Alabama"])
    return out


def emit(out):
    os.makedirs("vendor", exist_ok=True)
    items = []
    for k in sorted(out.keys()):
        inner = ", ".join(f'"{y}":{out[k][y]}' for y in sorted(out[k].keys()))
        items.append(f'"{k}":{{{inner}}}')
    s = "/* 美国州人口多年序列（来源：Wikipedia 美国各州人口表；2020 普查 + 2025 估算，稀疏序列）\n * 由 build_us_pop_ts.py 自动生成，勿手改。 */\nwindow.US_POP_TS = {\n" + ",\n".join(items) + "\n};"
    open(OUT, "w", encoding="utf-8").write(s + "\n")
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    emit(build(fetch()))
