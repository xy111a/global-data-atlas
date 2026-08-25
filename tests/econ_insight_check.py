#!/usr/bin/env python3
"""四维经济洞察验证：国家面板洞察区应显示 GDP/人均GDP/人口 增长率行"""
import subprocess, os, re

CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(p):
            CHROME = p; break
assert CHROME and os.path.exists(CHROME), "未找到 Chrome/Chromium，请设 CHROME_BIN"

def make_variant(name, trigger_js):
    html = open("global-data-atlas.html", encoding="utf-8").read()
    inject = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
              "try{" + trigger_js + "}catch(e){console.error('trigger',e);}},600);});</script>")
    html = html.replace("</body>", inject + "\n</body>")
    p = os.path.join("atlas_test", name)
    open(p, "w", encoding="utf-8").write(html)
    return "file://" + os.path.abspath(p)

def dump(url, wait=12):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait+15)
    return r.stdout.decode("utf-8", "replace")

# 1. GDP 视图：应显示 4 行（GDP不变价/GDP PPP/人均GDP/人口）
dom1 = dump(make_variant("econ_gdp.html",
    "showCountry(COUNTRIES.find(c=>c[2]==='CN'));"
    "setTimeout(function(){var ins=document.querySelectorAll('.dash-insight-row');"
    "var out=[];ins.forEach(r=>out.push(r.textContent.trim()));"
    "document.body.insertAdjacentHTML('beforeend','<pre id=\"eco\">VERIFY '+out.join(' || ')+'</pre>');},800);"), 12)
p1 = [m for m in re.findall(r'<pre id="eco">(.*?)</pre>', dom1, re.S) if m.startswith('VERIFY')]
print("GDP 视图洞察:", p1[-1][:300] if p1 else "未获取")

# 2. 贸易视图：应显示 贸易增长 + GDP不变价 + 人均GDP + 人口
dom2 = dump(make_variant("econ_trade.html",
    "metric='trade';showCountry(COUNTRIES.find(c=>c[2]==='CN'));"
    "setTimeout(function(){var ins=document.querySelectorAll('.dash-insight-row');"
    "var out=[];ins.forEach(r=>out.push(r.textContent.trim()));"
    "document.body.insertAdjacentHTML('beforeend','<pre id=\"eco\">VERIFY '+out.join(' || ')+'</pre>');},800);"), 12)
p2 = [m for m in re.findall(r'<pre id="eco">(.*?)</pre>', dom2, re.S) if m.startswith('VERIFY')]
print("贸易视图洞察:", p2[-1][:300] if p2 else "未获取")
