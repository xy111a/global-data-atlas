#!/usr/bin/env python3
"""构建欧盟 NUTS2 省级数据（Phase E 试点 8 国）：
   边界拆分（Eurostat GISCO NUTS2 GeoJSON）+ GDP（nama_10r_2gdp）+ 人口（demo_r_pjanaggr3）
   + EUR/CNY 汇率（Frankfurter=ECB）→ vendor/eu/{cc}.js（边界）+ vendor/eu/eu_metrics.js（指标）

   用法：python3 build_eu.py [--geojson /tmp/eu_build/nuts2.geojson] [--skip-network]
   依赖：出网（Eurostat API + Frankfurter）；边界 GeoJSON 需先下载：
     curl -L -o /tmp/eu_build/nuts2.geojson \
       "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326_LEVL_2.geojson"
"""
import json, os, sys, math, urllib.request, urllib.parse, argparse, time

ROOT = os.path.dirname(os.path.abspath(__file__))
EU_DIR = os.path.join(ROOT, "vendor", "eu")
COUNTRIES = ["DE", "FR", "IT", "ES", "NL", "PL", "BE", "AT"]
YEAR = 2023   # 单年快照（与日本/城市单年模式一致）

def fetch(url, timeout=60, retries=3):
    """用 curl 拉取（绕过本机 Python SSL 证书链问题，--noproxy 避免代理拦截），失败自动重试"""
    import subprocess, time
    last_err = ""
    for attempt in range(retries):
        r = subprocess.run(
            ["curl", "--noproxy", "*", "-sL", "-m", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 10)
        if r.returncode == 0:
            try:
                return json.loads(r.stdout)
            except json.JSONDecodeError as e:
                last_err = f"JSON解析失败: {e}"
        else:
            last_err = f"curl 失败({r.returncode}): {r.stderr[:150]}"
        time.sleep(2 * (attempt + 1))   # 退避重试
    raise RuntimeError(f"拉取失败（重试{retries}次）: {last_err}")

def area_km2(polygon_rings):
    """球面多边形面积近似（km²），输入 = GeoJSON 坐标环列表"""
    R = 6371.0
    total = 0.0
    def ring_area(ring):
        if len(ring) < 3: return 0.0
        s = 0.0
        for i in range(len(ring)):
            x1, y1 = ring[i]; x2, y2 = ring[(i+1) % len(ring)]
            s += math.radians(x2 - x1) * (2 + math.sin(math.radians(y1)) + math.sin(math.radians(y2)))
        return abs(s) * R * R / 2.0
    for ring in polygon_rings:
        total += ring_area(ring)
    return total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--geojson", default="/tmp/eu_build/nuts2.geojson")
    ap.add_argument("--skip-network", action="store_true", help="跳过 API 拉取（仅用本地/已有数据）")
    args = ap.parse_args()

    os.makedirs(EU_DIR, exist_ok=True)
    print(f"目标: {len(COUNTRIES)} 国 NUTS2 · 年份 {YEAR}")

    # ---------- 1. 边界拆分 ----------
    gj = json.load(open(args.geojson, encoding="utf-8"))
    by_country = {cc: [] for cc in COUNTRIES}
    for f in gj["features"]:
        cc = f["properties"]["CNTR_CODE"]
        if cc in by_country:
            by_country[cc].append(f)
    print("边界:", {cc: len(fs) for cc, fs in by_country.items()})

    # ---------- 2. GDP / 人口（API） ----------
    metrics = {}   # NUTS_ID -> {name, cc, gdp(元), pop, area(km²)}
    if args.skip_network:
        print("跳过网络拉取（--skip-network）")
    else:
        for cc in COUNTRIES:
            ids = [f["properties"]["NUTS_ID"] for f in by_country[cc]]
            names = {f["properties"]["NUTS_ID"]: f["properties"]["NUTS_NAME"] for f in by_country[cc]}
            geo_q = "&".join(f"geo={i}" for i in ids)
            # GDP（百万欧元，现价）——注意：API 会按字典序重排 geo 参数，必须用 API 返回的索引反查
            url = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10r_2gdp"
                   f"?{geo_q}&time={YEAR}&unit=MIO_EUR&format=JSON")
            d = fetch(url)
            geo_idx = d["dimension"]["geo"]["category"]["index"]   # {NUTS_ID: index}
            rev_idx = {v: k for k, v in geo_idx.items()}           # index → NUTS_ID
            gdp_by_id = {}
            for k, v in d["value"].items():
                gdp_by_id[rev_idx[int(k)]] = v
            print(f"  {cc} GDP: {len(gdp_by_id)} 区域")
            # 人口（含 sex/age 维度，过滤为总计；同样按 API 索引反查）
            url2 = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_r_pjanaggr3"
                    f"?{geo_q}&time={YEAR}&sex=T&age=TOTAL&format=JSON")
            d2 = fetch(url2)
            geo_idx2 = d2["dimension"]["geo"]["category"]["index"]
            rev_idx2 = {v: k for k, v in geo_idx2.items()}
            pop_by_id = {}
            for k, v in d2["value"].items():
                pop_by_id[rev_idx2[int(k)]] = v
            print(f"  {cc} 人口: {len(pop_by_id)} 区域")
            for nid in ids:
                g = gdp_by_id.get(nid)
                p = pop_by_id.get(nid)
                if g is None and p is None:
                    continue   # 完全无数据（Eurostat 缺失）跳过
                metrics[nid] = {"name": names[nid], "cc": cc, "gdp": g, "pop": p}   # gdp/pop 可单缺（如 NL31/NL33 无 GDP），面板显示"—"
            time.sleep(0.5)   # 限流礼貌间隔

    # ---------- 3. 汇率 EUR/CNY（Frankfurter=ECB，年度均值） ----------
    if args.skip_network:
        rate = 7.85
        print("汇率: 跳过拉取，用 7.85（近似）")
    else:
        url3 = (f"https://api.frankfurter.app/{YEAR}-01-01..{YEAR}-12-31?from=EUR&to=CNY")
        d3 = fetch(url3, timeout=150)
        rates = [v["CNY"] for v in d3["rates"].values()]
        rate = sum(rates) / len(rates)
        print(f"汇率 EUR/CNY {YEAR} 均值: {rate:.4f}")

    # ---------- 4. 面积（边界球面计算） ----------
    for cc, fs in by_country.items():
        for f in fs:
            nid = f["properties"]["NUTS_ID"]
            if nid in metrics:
                geom = f.get("geometry")
                a = 0.0
                if geom and geom.get("type") == "Polygon":
                    a = area_km2(geom["coordinates"])
                elif geom and geom.get("type") == "MultiPolygon":
                    a = sum(area_km2(p) for p in geom["coordinates"])
                metrics[nid]["area"] = round(a)

    # ---------- 5. 输出 ----------
    # 5a. 边界：每国一个 js（window.EU_{CC}_GEO）
    for cc, fs in by_country.items():
        out = {"type": "FeatureCollection", "features": fs}
        js = f"window.EU_{cc}_GEO=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
        p = os.path.join(EU_DIR, f"{cc.lower()}.js")
        open(p, "w", encoding="utf-8").write(js)
        print(f" 边界 → {os.path.relpath(p, ROOT)} ({os.path.getsize(p)//1024}KB)")

    # 5b. 指标：window.EU_METRICS（gdp 折算人民币元；单年快照）
    out_m = {}
    for nid, m in metrics.items():
        out_m[nid] = {
            "name": m["name"], "cc": m["cc"],
            "gdp": (m["gdp"] * 1e6 * rate) if m["gdp"] is not None else None,   # 百万欧元 → 元；Eurostat 缺 GDP 保留 null
            "pop": int(m["pop"]) if m["pop"] is not None else None, "area": m.get("area", 0),
            "year": YEAR
        }
    js_m = ("/* 欧盟 NUTS2 单年快照（Eurostat " + str(YEAR) + "）：gdp=元(人民币, EUR/CNY=" + f"{rate:.4f}" + "), pop=人, area=km² */\n"
            "window.EU_RATE=" + f"{rate:.4f}" + ";\n"
            "window.EU_METRICS=" + json.dumps(out_m, ensure_ascii=False, separators=(",", ":")) + ";\n")
    p = os.path.join(EU_DIR, "eu_metrics.js")
    open(p, "w", encoding="utf-8").write(js_m)
    print(f" 指标 → {os.path.relpath(p, ROOT)} ({len(out_m)} 区域, {os.path.getsize(p)//1024}KB)")
    print(f"\n完成：{len(out_m)} 个 NUTS2 区域（{len(COUNTRIES)} 国），汇率 {rate:.4f}")

if __name__ == "__main__":
    main()
