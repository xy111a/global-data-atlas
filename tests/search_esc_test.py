#!/usr/bin/env python3
"""P1 回归：世界层搜索美国州（不依赖 US_GEO）+ ESC 不在 SELECT 上触发返回。"""
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
    pres = [m for m in re.findall(r'<pre id="ck">R(.*?)</pre>', dom, re.S)
            if not m.startswith("'+")]
    if not pres:
        return None
    try:
        return json.loads(pres[-1])
    except Exception:
        return {"raw": pres[-1]}

ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

# 1. 搜 California：世界层（无 US_GEO）应打开美国州面板
inject1 = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
  doSearch('california');
  setTimeout(function(){
    var p=document.getElementById('panel');
    var txt=p?p.textContent.replace(/\\s+/g,' '):'';
    document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({
      hasGeo:!!window.US_GEO,
      panel:txt.slice(0,120),
      ok:txt.indexOf('California')>=0
    })+'</pre>');
  },1200);
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},800);});</script>"""
html = open("global-data-atlas.html", encoding="utf-8").read()
base = "<base href=\"file://" + os.path.abspath(".") + "/\">"
html = html.replace("</head>", base + "</head>", 1)
html = html.replace("</body>", inject1 + "\n</body>")
p1 = os.path.join("atlas_test", "search_us.html")
open(p1, "w", encoding="utf-8").write(html)
out1 = runtime_out(dump("file://" + os.path.abspath(p1), 14))
check(
    "搜 California 不依赖 US_GEO",
    bool(out1) and out1.get("ok") is True,
    f"({out1})",
)

# 2. ESC 在 #yearSel 上不应触发返回（level 保持/或至少不因 ESC 变 world 若本就在 world）
# 更强：先下钻中国，再 focus yearSel 按 ESC，level 应仍为 china（或面板仍中国）
inject2 = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
  DRILLABLE['CN'].load();
  setTimeout(function(){
    var ys=document.getElementById('yearSel');
    ys.focus();
    var ev=new KeyboardEvent('keydown',{key:'Escape',bubbles:true});
    ys.dispatchEvent(ev);
    setTimeout(function(){
      document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({
        level:currentLevel,
        sum:(document.getElementById('introSum')||{}).textContent||'',
        ok:currentLevel==='china'
      })+'</pre>');
    },400);
  },2500);
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},600);});</script>"""
html2 = open("global-data-atlas.html", encoding="utf-8").read()
html2 = html2.replace("</head>", base + "</head>", 1)
html2 = html2.replace("</body>", inject2 + "\n</body>")
p2 = os.path.join("atlas_test", "esc_select.html")
open(p2, "w", encoding="utf-8").write(html2)
out2 = runtime_out(dump("file://" + os.path.abspath(p2), 16))
check("ESC 在 SELECT 不返回", bool(out2) and out2.get("ok") is True, f"({out2})")

print(f"\n搜索/ESC 回归: {ok}/{total} 通过")
exit(0 if ok == total else 1)
