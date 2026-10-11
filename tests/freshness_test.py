#!/usr/bin/env python3
"""T8 回归：tooltip 数据新鲜度标注（实际采用年份 / 回退年 ≈ 标记）。
断言：
  1) 日本县（T3 多年序列 2011-2022）已就绪
  2) 请求年缺失 → freshnessTag 返回 "≈<最近可得年>"（日本 2025→≈2022，世界 US 2025→≈2024）
  3) 请求年命中 → 返回精确年（日本 2020→2020）
  4) geoTooltipBody 头部展示该 ≈ 年份（拒绝过期快照误导，不再写死 2021）
  5) 世界层 tooltip formatter 真实输出含年份角标
"""
import subprocess, os, re, json

CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(p):
            CHROME = p; break
assert CHROME and os.path.exists(CHROME), "未找到 Chrome/Chromium，请设 CHROME_BIN"
os.makedirs("atlas_test", exist_ok=True)

def dump(url, wait):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait + 25)
    return r.stdout.decode("utf-8", "replace")

def runtime_out(dom):
    """<pre id="ck"> 用 B+base64 传输（tooltip 内含 HTML/引号，直接塞 insertAdjacentHTML 会被
    DOM 解析吞掉引号/标签 → JSON 损坏。故用 textContent + base64 保真。）"""
    pres = [m for m in re.findall(r'<pre id="ck">B(.*?)</pre>', dom, re.S)]
    if not pres:
        return None
    import base64
    try:
        raw = base64.b64decode(pres[-1].strip()).decode("utf-8")
        return json.loads(raw)
    except Exception as e:
        return {"err": f"decode-fail: {e}", "raw": pres[-1][:120]}

ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

html = open("global-data-atlas.html", encoding="utf-8").read()
base = "<base href=\"file://" + os.path.abspath(".") + "/\">"

# 日本数据体量大、延迟就绪 → 轮询等待（不用固定 sleep）
inject = """<script>window.addEventListener('load',function(){
var tries=0;
(function poll(){
 tries++;
 var bareChart = (typeof chart!=='undefined') && !!chart;
 var hasTT = false;
 try{ var op=bareChart?chart.getOption():null; hasTT=!!(op&&op.tooltip); }catch(e){}
 var ready = window.JP_METRICS && window.JP_TS && window.WB && bareChart
             && typeof freshnessTag==='function' && hasTT;
 if(!ready){ if(tries<60) return setTimeout(poll,200); return; }
 var out={tries:tries};
 var rc=regCountry('US');
 out.worldFresh=freshnessTag(rc,'gdp',dataYear);
 var jp=regJapanPref('北海道');
 out.jpYears=jp?jp.years():null;
 out.jp2025=freshnessTag(jp,'gdp',2025);
 out.jp2020=freshnessTag(jp,'gdp',2020);
 out.jpTip=geoTooltipBody({name:'北海道',data:{reg:jp}},'2021');
 var opt=chart.getOption();
 var tt=opt.tooltip; var fm=(Array.isArray(tt)?tt[0]:tt);
 var c=COUNTRIES.filter(function(x){return x[2]==='US';})[0];
 out.worldTip = fm && fm.formatter ? fm.formatter({name:c[1],data:{cn:c,reg:rc}}) : null;
 out.dataYear = dataYear;
 /* base64 保真输出：避免 tooltip HTML 里的标签/引号被 DOM 解析破坏 JSON */
 var json=JSON.stringify(out);
 var b64=btoa(unescape(encodeURIComponent(json)));
 var el=document.createElement('pre'); el.id='ck'; el.textContent='B'+b64;
 document.body.appendChild(el);
})();
});</script>"""

h = html.replace("</head>", base + "</head>", 1).replace("</body>", inject + "\n</body>")
p = os.path.join("atlas_test", "freshness.html")
open(p, "w", encoding="utf-8").write(h)
o = runtime_out(dump("file://" + os.path.abspath(p), 20))

if not o or "err" in o:
    check("新鲜度标注脚本执行", False, f"({o})")
else:
    yrs = o.get("jpYears") or []
    check("日本多年序列已就绪(含 2022)", 2022 in yrs,
          f"(tries={o.get('tries')} years={yrs[:3]}...{yrs[-2:] if yrs else []})")
    check("日本请求 2025 → 回退标记 ≈2022", o.get("jp2025") == "≈2022", f"({o.get('jp2025')})")
    check("日本请求 2020 → 精确年 2020", o.get("jp2020") == "2020", f"({o.get('jp2020')})")
    jtip = o.get("jpTip") or ""
    check("geoTooltipBody 头部展示 ≈2022（非过期写死 2021）",
          "≈2022" in jtip and "· 2021" not in jtip, f"({jtip[:64]})")
    check("世界层 freshnessTag 为 ≈回退年",
          bool(re.fullmatch(r"(≈)?\d{4}", str(o.get("worldFresh") or "")))
          and str(o.get("worldFresh")).startswith("≈"),
          f"(dataYear={o.get('dataYear')} → {o.get('worldFresh')})")
    wtip = o.get("worldTip") or ""
    check("世界层 tooltip 输出含年份角标", bool(re.search(r"(≈)?\d{4}", wtip)), f"({wtip[:76]})")

print(f"\n数据新鲜度标注(T8)回归: {ok}/{total} 通过")
exit(0 if ok == total else 1)
