#!/usr/bin/env python3
"""欧盟 NUTS2「多年序列真正可用 + 派生指标全层可用」浏览器验证。

背景：build_eu_ts.py 早已把 EU NUTS2 建成多年序列（242 区域 / GDP 2000–2024 / 人口 1990–2025），
但 FEATURES.md 与 meta.js 一直写着「2023 单年」，文档与数据脱节——这类脱节正是本项目的
高发故障模式（日本 P0、嵌入模式 P1 都源于「以为的状态 ≠ 实际状态」）。
本测试不信任文档，直接在浏览器里跑真实代码验证：
  1) 欧盟层年份切换真的生效（2000 与 2024 的 GDP 必须显著不同）
  2) 派生指标（人均GDP·现价 / 地均GDP）在**非世界层**可用、按钮未禁用
  3) 排行「名义增长」模式在欧盟层能排出结果（此前 growth 口径错误会让排序失真）
"""
import subprocess, os, re, json, base64, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(p):
            CHROME = p; break
assert CHROME and os.path.exists(CHROME), "未找到 Chrome/Chromium，请设 CHROME_BIN"
os.makedirs("atlas_test", exist_ok=True)

TRIGGER = r"""
var out={};
try{
  DRILLABLE['DE'].load();
  setTimeout(function(){
    try{
      var r=regNUTS('DE11');
      var ys=r?r.years():[];
      out.yearsLen=ys.length;
      out.span=ys.length?(ys[0]+'-'+ys[ys.length-1]):'';
      var v2000=r?r.get('gdp',2000):null, v2024=r?r.get('gdp',2024):null;
      out.gdp2000=v2000; out.gdp2024=v2024;
      out.yearSwitchWorks = !!((v2000!=null)&&(v2024!=null)&&(Math.abs(v2024/v2000-1)>0.05));
      out.growthUSD = r?r.growth('gdp',2000):null;
      var g0=regGet(r,'gdp',2000), g1=regGet(r,'gdp',dataYear);
      out.growthSelfConsistent = !!((out.growthUSD!=null)&&(g0)&&(Math.abs(out.growthUSD-(g1/g0-1))<1e-9));
      out.pc = r?METRICS.gdppc.near(r,2024):null;
      out.den= r?METRICS.gdpden.near(r,2024):null;
      var btns=Array.prototype.slice.call(document.querySelectorAll('#metricSeg button'));
      out.btnKeys=btns.map(function(b){return b.dataset.m;}).join('|');
      out.disabledInNuts=btns.filter(function(b){return b.disabled;}).map(function(b){return b.dataset.m;}).join('|');
      metric='gdp'; rankMode='growth'; renderRank();
      var ri=document.querySelectorAll('.rank-item');
      out.rankGrowthCount=ri.length;
      out.rankTop=ri.length?ri[0].textContent.trim().replace(/\s+/g,' ').slice(0,70):'';
      metric='gdppc'; renderRank();
      var ri2=document.querySelectorAll('.rank-item');
      out.rankPcCount=ri2.length;
      out.rankPcTop=ri2.length?ri2[0].textContent.trim().replace(/\s+/g,' ').slice(0,70):'';
      out.err=null;
    }catch(e){ out.err='inner:'+e.message; }
    var pre=document.createElement('pre'); pre.id='ey';
    pre.textContent='B'+btoa(unescape(encodeURIComponent(JSON.stringify(out))));
    document.body.appendChild(pre);
  }, 4200);
}catch(e){
  var pre0=document.createElement('pre'); pre0.id='ey';
  pre0.textContent='B'+btoa(unescape(encodeURIComponent(JSON.stringify({err:'outer:'+e.message}))));
  document.body.appendChild(pre0);
}
"""

html = open("global-data-atlas.html", encoding="utf-8").read()
html = html.replace("</head>", f'<base href="file://{ROOT}/"></head>')
html = html.replace("</body>", "<script>window.addEventListener('load',function(){setTimeout(function(){"
                    + TRIGGER + "},500);});</script>\n</body>")
pg = os.path.join("atlas_test", "eu_year_metric.html")
open(pg, "w", encoding="utf-8").write(html)

dom = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                      "--virtual-time-budget=22000", "--dump-dom",
                      "file://" + os.path.abspath(pg)],
                     capture_output=True, timeout=90).stdout.decode("utf-8", "replace")

pres = re.findall(r'<pre id="ey">B(.*?)</pre>', dom, re.S)
ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

if not pres:
    check("探针产出结果", False, "(未找到 <pre id=ey>，页面可能未执行完)")
    print(f"\n欧盟年份/派生指标回归: {ok}/{total} 通过")
    sys.exit(1)

out = json.loads(base64.b64decode(pres[-1].strip()).decode("utf-8"))
check("探针无异常", not out.get("err"), f"({out.get('err')})")
check("欧盟层有多年序列（≥20 年）", out.get("yearsLen", 0) >= 20, f"({out.get('yearsLen')} 年, {out.get('span')})")
check("年份切换生效（2000 vs 2024 GDP 显著不同）", out.get("yearSwitchWorks") is True,
      f"(2000={out.get('gdp2000')} · 2024={out.get('gdp2024')})")
check("增长与展示值自洽（USD 口径）", out.get("growthSelfConsistent") is True,
      f"(growth={out.get('growthUSD')})")
check("派生指标 人均GDP 在欧盟层可算", out.get("pc") is not None and out.get("pc") > 1000,
      f"(${out.get('pc')})")
check("派生指标 地均GDP 在欧盟层可算", out.get("den") is not None and out.get("den") > 0,
      f"(${out.get('den')})")
check("指标按钮含 gdppc/gdpden", "gdppc" in (out.get("btnKeys") or "") and "gdpden" in (out.get("btnKeys") or ""),
      f"({out.get('btnKeys')})")
check("欧盟层 gdppc/gdpden 未被禁用", "gdppc" not in (out.get("disabledInNuts") or "") and "gdpden" not in (out.get("disabledInNuts") or ""),
      f"(禁用项: {out.get('disabledInNuts') or '无'})")
check("排行「名义增长」模式有结果", (out.get("rankGrowthCount") or 0) >= 10, f"({out.get('rankGrowthCount')} 条)")
check("排行可切到人均GDP并出结果", (out.get("rankPcCount") or 0) >= 10, f"({out.get('rankPcCount')} 条 · 首位 {out.get('rankPcTop')})")

print(f"\n欧盟年份/派生指标回归: {ok}/{total} 通过")
sys.exit(0 if ok == total else 1)
