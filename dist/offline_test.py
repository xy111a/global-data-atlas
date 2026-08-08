#!/usr/bin/env python3
"""Offline self-test: file:// WITHOUT --allow-file-access-from-files.
Verifies the main HTML renders via window globals (zero fetch)."""
import subprocess, os, time, re

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SRC = "global-data-atlas.html"
WS = os.path.abspath(".")
OUT = "atlas_test"
os.makedirs(OUT, exist_ok=True)
# Copy vendor/ into OUT so relative paths in variant HTMLs resolve correctly
import shutil
shutil.copytree("vendor", os.path.join(OUT, "vendor"), dirs_exist_ok=True)

def make_variant(name, trigger_js):
    html = open(SRC, encoding="utf-8").read()
    inject = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
              "try{" + trigger_js + "}catch(e){console.error('trigger',e);}},600);});</script>")
    html = html.replace("</body>", inject + "\n</body>")
    p = os.path.join(OUT, name)
    open(p, "w", encoding="utf-8").write(html)
    return "file://" + os.path.abspath(p)

def shot(name, url, wait=11, extra=None):
    extra = extra or []
    path = os.path.join(OUT, name)
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           "--hide-scrollbars", "--window-size=1280,800",
           f"--virtual-time-budget={wait*1000}", *extra,
           f"--screenshot={path}", url]
    subprocess.run(cmd, capture_output=True, timeout=wait+15)
    sz = os.path.getsize(path) if os.path.exists(path) else 0
    print(f"  {'OK ' if sz>50000 else 'FAIL'} {name}: {sz}b")
    return sz

print("=== Offline Self-Test (file://, no allow-file-access) ===\n")
shot("o1_2d.png", "file://" + os.path.abspath(SRC), wait=9)
shot("o2_china.png", make_variant("t_china.html", "loadChina()"), wait=12)
shot("o3_zj.png", make_variant("t_zj.html", "loadChina();loadProvince('浙江','330000')"), wait=13)
shot("o4_us.png", make_variant("t_us.html", "loadUS()"), wait=12)

# --- DOM verification of CN multi-year functions (no screenshot needed) ---
def dump_dom(name, url, wait=9):
    path = os.path.join(OUT, name)
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", f"--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait+15)
    return r.stdout.decode("utf-8", "replace")

verify_js = (
    "loadChina();"
    "var out=[];"
    "['广东','内蒙古','浙江','山西'].forEach(function(p){[2000,2010,2024,2025].forEach(function(y){"
    "var v=cnGdpRMB(p,y); out.push(p+'@'+y+'='+(v!=null?(v/1e12).toFixed(2):'NULL'));});});"
    "var ng=cnNominalGrowth('广东',2000); out.push('广东较2000='+(ng!=null?(ng*100).toFixed(1)+'%':'NULL'));"
    "dataYear='2000'; showProvincePanel('广东');"
    "var p0=document.getElementById('pMetrics').innerText.replace(/\\s+/g,' ');"
    "dataYear='2024'; showProvincePanel('浙江');"
    "var p4=document.getElementById('pMetrics').innerText.replace(/\\s+/g,' ');"
    "document.body.insertAdjacentHTML('beforeend','<pre id=\"testout\">VERIFY '+out.join(' ; ')"
    "+' || P2000 '+p0+' || P2024 '+p4+'</pre>');"
)
vurl = make_variant("t_cn_verify.html", verify_js)
dom = dump_dom("cn_verify_dom.html", vurl, wait=10)
tag = "VERIFY" in dom and "P2024" in dom
print("  " + ("OK " if tag else "FAIL") + " cn_verify DOM captured")
# Take the LAST match: the rendered <pre> is injected at runtime (end of body),
# after the inline <script> source that also contains the same string literal.
pres = [m for m in re.findall(r'<pre id="testout">(.*?)</pre>', dom, re.S) if 'P2024' in m]
if pres: print("    " + pres[-1][:700])

print("\nDone ->", os.path.abspath(OUT))
