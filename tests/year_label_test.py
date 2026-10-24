#!/usr/bin/env python3
"""年份标签/增长窗口回归（2026-10-24 审计）：
  - 城市 GDP 标签必须是实际采用年（2025→≈2023，2015→≈2012）
  - 日本 GDP 标签必须是 ≈2022（不是写死 2021），且有多趋势
  - 欧盟 GDP 标签必须是 ≈2024（不是写死 2023），且有多趋势
  - 省级增长排行 2015 的实际窗口必须是 2010→2012（不是 2010→2015）
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

src = open("global-data-atlas.html", encoding="utf-8").read()
base = '<base href="file://%s/">' % os.path.abspath(".")
src = src.replace("</head>", base + "</head>", 1)

inject = """<script>
window.__lab={};
function __grab(){
  return {
    stats:[].map.call(document.querySelectorAll('#introStats .dash-stat'),function(x){return x.textContent.replace(/\\s+/g,' ').trim();}),
    tags:[].map.call(document.querySelectorAll('#pHint .tag'),function(x){return x.textContent.trim();}),
    trend:!!document.querySelector('#trend #trendChart'),
    rank:(document.querySelector('#rank summary')||{}).textContent||''
  };
}
window.addEventListener('load',function(){setTimeout(function(){
  var se=document.getElementById('yearSel'); se.value='2025'; se.dispatchEvent(new Event('change'));
  loadProvince('广东','440000').then(function(){
    showCityPanel('深圳市','440300','440000');
    __lab.city2025=__grab();
    se.value='2015'; se.dispatchEvent(new Event('change'));
    showCityPanel('深圳市','440300','440000');
    __lab.city2015=__grab();
    rankMode='growth'; renderRank(); __lab.rankGrowth2015=__grab();
    return loadJapan();
  }).then(function(){
    se.value='2025'; se.dispatchEvent(new Event('change'));
    showJapanPrefPanel('北海道'); __lab.jp=__grab();
    return loadNUTS('AT');
  }).then(function(){
    showNUTSPanel('AT11'); __lab.nuts=__grab();
  }).catch(function(e){ __lab.err=e.message; }).then(function(){
    document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify(__lab)+'</pre>');
  });
},2500);});</script>"""
p = os.path.join("atlas_test", "year_label.html")
open(p, "w", encoding="utf-8").write(src.replace("</body>", inject + "\n</body>"))

cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
       "--virtual-time-budget=50000", "--dump-dom", "file://" + os.path.abspath(p)]
r = subprocess.run(cmd, capture_output=True, timeout=90)
dom = r.stdout.decode("utf-8", "replace")
pres = [m for m in re.findall(r'<pre id="ck">R(.*?)</pre>', dom, re.S) if not m.startswith("'+")]
out = json.loads(pres[-1]) if pres else {}
print(json.dumps(out, ensure_ascii=False, indent=1)[:1800])

ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

if out.get("err"):
    check("页面脚本无异常", False, out["err"])
else:
    c25 = " ".join((out.get("city2025") or {}).get("stats", []))
    c15 = " ".join((out.get("city2015") or {}).get("stats", []))
    jp = " ".join((out.get("jp") or {}).get("stats", []))
    nuts = " ".join((out.get("nuts") or {}).get("stats", []))
    check("城市 2025 标签 ≈2023", "≈2023" in c25 and "GDP (2025)" not in c25, c25[:80])
    check("城市 2015 标签 ≈2012", "≈2012" in c15, c15[:80])
    check("日本标签 ≈2022 且有趋势", "≈2022" in jp and (out.get("jp") or {}).get("trend") is True, jp[:80])
    check("欧盟标签 ≈2024 且有趋势", "≈2024" in nuts and (out.get("nuts") or {}).get("trend") is True, nuts[:80])
    rank = (out.get("rankGrowth2015") or {}).get("rank", "")
    check("增长排行实际窗口 2010→2012", "2010→2012" in rank, rank)

print(f"\n年份标签/增长窗口: {ok}/{total} 通过")
raise SystemExit(0 if ok == total else 1)
