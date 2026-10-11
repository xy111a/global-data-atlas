#!/usr/bin/env python3
"""欧盟 NUTS2 多年序列补齐（A1-EU，并发版）：
   读取现有 vendor/eu/eu_metrics.js（已含 242 个 NUTS_ID + 名称 + 面积 + 单年 2023），
   仅补齐多年 GDP（nama_10r_2gdp）与人口（demo_r_pjanaggr3），逐年 EUR→CNY 折算，
   重写 window.EU_METRICS 为 {name,cc,area,gdp:{year:元},pop:{year:人},year:最新年}。
   边界文件（vendor/eu/<cc>.js）不动；无需重下 1.3MB GeoJSON。
   API 缺失的区域回退到旧单年 2023 值，绝不丢数据。

   用法：python3 build_eu_ts.py [--skip-network] [--workers 6]
   依赖：出网（Eurostat API + Frankfurter=ECB）。线程池并发 + 退避重试。
"""
import json, os, re, time, tempfile, shutil, argparse, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.abspath(__file__))
EU_DIR = os.path.join(ROOT, "vendor", "eu")
METRICS_JS = os.path.join(EU_DIR, "eu_metrics.js")
WORKERS = 6

def fetch(url, timeout=45, retries=4):
    last_err = ""
    for attempt in range(retries):
        r = subprocess.run(
            ["curl", "--noproxy", "*", "-sL", "-m", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 15)
        if r.returncode == 0:
            try:
                return json.loads(r.stdout)
            except json.JSONDecodeError as e:
                last_err = f"JSON解析失败: {e}"
        else:
            last_err = f"curl 失败({r.returncode}): {r.stderr[:120]}"
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"拉取失败（重试{retries}次）: {last_err}")

def round4(x):
    return round(x, 2) if isinstance(x, float) else x

def atomic_write(path, content, backup=True):
    bak = None
    if backup and os.path.exists(path):
        bak = f"/tmp/{os.path.basename(path)}.bak.{int(time.time())}"
        shutil.copy2(path, bak)
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".js")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp): os.unlink(tmp)
        if bak and os.path.exists(path): shutil.copy2(bak, path)
        raise
    return bak

def parse_ts(d):
    """单区域多维（geo 维度 size=1）→ value 键即 timeIdx。返回 {year_str: value}"""
    dims = d.get("dimension", {})
    time_idx = dims.get("time", {}).get("category", {}).get("index", {})
    rev_time = {v: k for k, v in time_idx.items()}
    out = {}
    for k, val in d.get("value", {}).items():
        if val is None: continue
        t = rev_time.get(int(k))
        if t is not None:
            out[str(t)] = val
    return out

def fetch_rate_map(years):
    lo, hi = min(years), max(years)
    try:
        d = fetch(f"https://api.frankfurter.app/{lo}-01-01..{hi}-12-31?from=EUR&to=CNY", timeout=180)
        by_year = {}
        for date, v in d.get("rates", {}).items():
            y = int(date[:4]); cny = v.get("CNY")
            if cny is None: continue
            by_year.setdefault(y, []).append(cny)
        rm = {y: sum(x)/len(x) for y, x in by_year.items()}
    except Exception as e:
        print(f"  [warn] 汇率拉取失败: {e}，全部用 7.85 兜底", flush=True)
        rm = {}
    if rm:
        ys = sorted(rm)
        for y in range(lo, hi+1):
            if y not in rm:
                prev = max([x for x in ys if x < y], default=None)
                nxt = min([x for x in ys if x > y], default=None)
                rm[y] = rm.get(prev) or rm.get(nxt) or 7.85
    else:
        rm = {y: 7.85 for y in range(lo, hi+1)}
    return rm

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-network", action="store_true")
    ap.add_argument("--workers", type=int, default=WORKERS)
    args = ap.parse_args()

    src = open(METRICS_JS, encoding="utf-8").read()
    m = re.search(r'window\.EU_METRICS=(\{.*\})', src, re.S)
    if not m:
        raise SystemExit("未找到 window.EU_METRICS")
    old = json.loads(m.group(1))
    nids = sorted(old.keys())
    print(f"读入现有 NUTS2 区域: {len(nids)}", flush=True)

    gdp_ts, pop_ts = {}, {}
    if args.skip_network:
        print("[skip-network] 仅重排格式", flush=True)
        for nid in nids:
            o = old[nid]
            yr = str(o.get("year", 2023))
            gdp_ts[nid] = {yr: o.get("gdp")} if o.get("gdp") is not None else {}
            pop_ts[nid] = {yr: o.get("pop")} if o.get("pop") is not None else {}
        rate_map, YEARS = {}, [2023]
    else:
        def grab(nid):
            g = p = None
            try:
                g = parse_ts(fetch(f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10r_2gdp?geo={nid}&unit=MIO_EUR&format=JSON"))
            except Exception as e:
                print(f"  [warn] {nid} GDP 失败: {e}", flush=True); g = {}
            try:
                p = parse_ts(fetch(f"https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_r_pjanaggr3?geo={nid}&sex=T&age=TOTAL&format=JSON"))
            except Exception as e:
                print(f"  [warn] {nid} 人口 失败: {e}", flush=True); p = {}
            return nid, g, p

        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(grab, nid) for nid in nids]
            for fut in as_completed(futs):
                nid, g, p = fut.result()
                gdp_ts[nid], pop_ts[nid] = g, p
                done += 1
                if done % 40 == 0:
                    print(f"  进度 {done}/{len(nids)}", flush=True)

        all_years = set()
        for nid in nids:
            all_years.update(int(y) for y in gdp_ts[nid])
            all_years.update(int(y) for y in pop_ts[nid])
        all_years = sorted(y for y in all_years if 1998 <= y <= 2025)
        print(f"年份范围: {all_years[0]}–{all_years[-1]}（{len(all_years)} 年）", flush=True)
        rate_map = fetch_rate_map(all_years)
        YEARS = all_years

    # 组装（API 缺失区域回退旧单年 2023 值）
    new = {}
    for nid in nids:
        o = old[nid]
        g = gdp_ts.get(nid, {})
        p = pop_ts.get(nid, {})
        if not g and o.get("gdp") is not None:
            g = {str(o.get("year", 2023)): o["gdp"]}
        if not p and o.get("pop") is not None:
            p = {str(o.get("year", 2023)): o["pop"]}
        gdp_cny = {y: (round4(v * 1e6 * rate_map.get(int(y), 7.85)) if v is not None else None)
                   for y, v in g.items()}
        pop_out = {y: (int(v) if v is not None else None) for y, v in p.items()}
        yrs = sorted(int(y) for y in gdp_cny if gdp_cny[y] is not None) or [o.get("year", 2023)]
        new[nid] = {
            "name": o.get("name"), "cc": o.get("cc"), "area": o.get("area"),
            "gdp": gdp_cny, "pop": pop_out, "year": max(yrs),
        }

    latest_year = max((v.get("year", 2023) for v in new.values()), default=2023)
    latest_rate = rate_map.get(latest_year, 7.85) if rate_map else 7.85
    out_js = (
        f"/* 欧盟 NUTS2 多年序列（Eurostat nama_10r_2gdp / demo_r_pjanaggr3，GDP 折算人民币元，"
        f"EUR/CNY 逐年 ECB 均值）：gdp/pop 为 {{年: 值}}；year=最新可得年 */\n"
        f"window.EU_RATE={latest_rate:.4f};\n"
        f"window.EU_METRICS=" + json.dumps(new, ensure_ascii=False, separators=(",", ":")) + ";\n"
    )
    bak = atomic_write(METRICS_JS, out_js)
    n_ts = sum(1 for v in new.values() if isinstance(v.get("gdp"), dict) and len([x for x in v["gdp"].values() if x is not None]) >= 2)
    print(f"已写 {os.path.relpath(METRICS_JS, ROOT)}（{len(new)} 区域，{n_ts} 个有≥2年序列，"
          f"最新年 {latest_year}，汇率 {latest_rate:.4f}）" + (f" · 备份 {bak}" if bak else ""), flush=True)

if __name__ == "__main__":
    main()
