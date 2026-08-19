#!/usr/bin/env python3
"""双币切换验证（GDP 人民币/美元）：默认 CNY / 切 USD / URL ?cur=usd 恢复"""
import subprocess, os, re

CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(p):
            CHROME = p; break
assert CHROME and os.path.exists(CHROME), "未找到 Chrome/Chromium，请设 CHROME_BIN"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(ROOT, "atlas_test"), exist_ok=True)

def make_variant(name, trigger_js, wait, extra_hash=""):
    html = open(os.path.join(ROOT, "global-data-atlas.html"), encoding="utf-8").read()
    base = f'<base href="file://{ROOT}/">'
    html = html.replace("</head>", base + "</head>")
    inject = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
              "try{" + trigger_js + "}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id=\"cur\">ERR:'+e.message+'</pre>')}"
              "},500);});</script>")
    html = html.replace("</body>", inject + "\n</body>")
    p = os.path.join(ROOT, "atlas_test", name)
    open(p, "w", encoding="utf-8").write(html)
    return "file://" + os.path.abspath(p) + extra_hash, wait

def dump(url, wait):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait+25)
    dom = r.stdout.decode("utf-8", "replace")
    pres = [m for m in re.findall(r'<pre id="cur">(.*?)</pre>', dom, re.S)]
    return pres[-1] if pres else "未获取"

# 1. 默认 CNY：中国/美国 GDP 为人民币量级
TRIGGER1 = """var out=[];
out.push('CUR='+window.CURRENCY);
out.push('CN='+fmtGDP(regGet(regCountry('CN'),'gdp',2024)));
out.push('US='+fmtGDP(regGet(regCountry('US'),'gdp',2024)));
document.body.insertAdjacentHTML('beforeend','<pre id="cur">'+out.join(' || ')+'</pre>');"""
url1, w1 = make_variant("cur_cny.html", TRIGGER1, 10)
o1 = dump(url1, w1)

# 2. 切 USD：GDP 显示 $ 且数值 ≈ CNY/7.2
TRIGGER2 = """document.getElementById('curSel').value='USD';
document.getElementById('curSel').dispatchEvent(new Event('change'));
setTimeout(function(){
var out=[];
out.push('CUR='+window.CURRENCY);
out.push('CN='+fmtGDP(regGet(regCountry('CN'),'gdp',2024)));
out.push('US='+fmtGDP(regGet(regCountry('US'),'gdp',2024)));
out.push('sel='+document.getElementById('curSel').value);
document.body.insertAdjacentHTML('beforeend','<pre id="cur">'+out.join(' || ')+'</pre>');
},400);"""
url2, w2 = make_variant("cur_usd.html", TRIGGER2, 10)
o2 = dump(url2, w2)

# 3. URL #cur=usd 恢复
TRIGGER3 = """setTimeout(function(){
var out=[]; out.push('CUR='+window.CURRENCY+'|sel='+document.getElementById('curSel').value);
document.body.insertAdjacentHTML('beforeend','<pre id="cur">'+out.join(' || ')+'</pre>');
},600);"""
url3, w3 = make_variant("cur_restore.html", TRIGGER3, 10, "#cur=usd")
o3 = dump(url3, w3)

ok = 0; total = 3
def check(label, cond, detail=""):
    global ok
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

check("默认 CNY", "CUR=CNY" in o1 and "CN=¥" in o1 and "US=¥" in o1, f"({o1[:90]})")
check("切 USD", "CUR=USD" in o2 and "CN=$" in o2 and "US=$" in o2 and "sel=USD" in o2, f"({o2[:90]})")
check("URL 恢复 USD", "CUR=USD" in o3 and "sel=USD" in o3, f"({o3[:60]})")
print(f"\n双币切换测试: {ok}/{total} 通过")
exit(0 if ok == total else 1)
