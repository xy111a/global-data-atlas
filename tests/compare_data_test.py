#!/usr/bin/env python3
"""对比页数据口径回归（2026-10-24 审计）：
  1) NUTS2 不得显示 "—"（对象型 gdp/pop 曾被除以汇率变 NaN）
  2) 城市名必须是中文名而不是 adcode
  3) 城市/日本/省份的当前值必须按所选年份，而不是各自固定年
  4) 城市层级列表可用（CITY_INDEX 必须加载），且值按当前指标/年份
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

def dump(url, wait=12):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait+25)
    return r.stdout.decode("utf-8", "replace")

def runtime_out(dom):
    pres = [m for m in re.findall(r'<pre id="ck">R(.*?)</pre>', dom, re.S) if not m.startswith("'+")]
    return json.loads(pres[-1]) if pres else None

ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

# 1) ?add 多层级 + 2015：NUTS 有值、城市中文名、城市值跟随 2015、日本不再是 2021 CNY 值
url = ("file://" + os.path.abspath("compare.html")
       + "?add=nutspref:AT11&add=jppref:北海道&add=city:440300:440000&add=prov:广东&year=2015&metric=gdp")
dom = dump(url, 14)
dom_body = re.sub(r"<script.*?</script>", "", dom, flags=re.S)
rows = re.findall(r'<div class="cmp-item"[^>]*>(.*?)</div>', dom_body, re.S)
rows = [re.sub(r"<[^>]+>", " ", r).replace("×", "").strip() for r in rows]
rows = [re.sub(r"\s+", " ", r) for r in rows]
text = " | ".join(rows)
print("  rows:", text)
check("NUTS2 GDP 不是 —", "Burgenland" in text and "Burgenland —" not in text, "")
check("城市显示中文名", "深圳市" in text and "440300" not in text, "")
check("城市 GDP 不再固定 2023（≈$2051 亿，实际 2012）", "2051" in text and "（2012）" in text, text)
check("日本按 2015 美元值（≈$1650 亿）", "1650" in text, text)
check("省份按 2015 值", "6915" in text, text)

# 2) 城市层级列表：不抛错、有 300+ 行、值按当前指标（人口）
html = open("compare.html", encoding="utf-8").read()
base = '<base href="file://%s/">' % os.path.abspath(".")
html = html.replace("</head>", base + "</head>", 1)
inject = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
  var lv=document.getElementById('levelSel'); lv.value='city'; renderUnitList();
  var rows=document.querySelectorAll('#unitList .unit');
  var first=rows[0]?rows[0].textContent.replace(/\\s+/g,' ').trim():'';
  var b=document.querySelector('#metricSeg button[data-m="pop"]'); if(b) b.click();
  setTimeout(function(){
    var rows2=document.querySelectorAll('#unitList .unit');
    document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({
      n:rows.length, n2:rows2.length, first:first,
      popFirst:rows2[0]?rows2[0].textContent.replace(/\\s+/g,' ').trim():'',
      err:window.__cmpErr||null
    })+'</pre>');
  },700);
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},2200);});</script>"""
p = os.path.join("atlas_test", "cmp_data_city.html")
open(p, "w", encoding="utf-8").write(html.replace("</body>", inject + "\n</body>"))
out = runtime_out(dump("file://" + os.path.abspath(p), 14))
print("  city:", out)
check("城市层级列表可用", bool(out) and out.get("err") is None and out.get("n", 0) > 300, str(out)[:120])
check("城市列表值非人民币当美元", bool(out) and "亿" in (out.get("first") or ""), (out or {}).get("first", ""))
check("切人口后列表按人口格式化", bool(out) and "万人" in (out.get("popFirst") or ""), (out or {}).get("popFirst", ""))

print(f"\n对比页数据口径: {ok}/{total} 通过")
raise SystemExit(0 if ok == total else 1)
