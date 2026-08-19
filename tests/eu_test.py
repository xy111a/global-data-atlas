#!/usr/bin/env python3
"""欧盟 NUTS2 下钻验证：德国 NUTS2 加载 + 面板 + 排行 + 泛化下钻"""
import subprocess, os, re

CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(p):
            CHROME = p; break
assert CHROME and os.path.exists(CHROME), "未找到 Chrome/Chromium，请设 CHROME_BIN"
os.makedirs("atlas_test", exist_ok=True)

def make_variant(name, trigger_js, wait):
    html = open("global-data-atlas.html", encoding="utf-8").read()
    # 探针页位于 atlas_test/，相对路径 vendor/... 会解析到 atlas_test/vendor（可能残留旧数据）；
    # 注入 <base href> 指向项目根，确保加载根目录最新 vendor 数据
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = f'<base href="file://{root}/">'
    html = html.replace("</head>", base + "</head>")
    inject = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
              "try{" + trigger_js + "}catch(e){console.error('trigger',e);}},600);});</script>")
    html = html.replace("</body>", inject + "\n</body>")
    p = os.path.join("atlas_test", name)
    open(p, "w", encoding="utf-8").write(html)
    return "file://" + os.path.abspath(p), wait

def dump(url, wait):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait+20)
    return r.stdout.decode("utf-8", "replace")

TRIGGER_DE = """var c=BY_EN['Germany']; var d=DRILLABLE[c[2]]; if(d){ d.load(); }
setTimeout(function(){
var out=[];
out.push('LEVEL='+currentLevel+'|NUTS='+currentNUTS);
out.push('面板='+document.getElementById('pName').textContent);
var ri=document.querySelectorAll('.rank-item'); out.push('排行条数='+ri.length);
out.push('排行前2='+Array.from(ri).slice(0,2).map(function(x){return x.textContent.trim();}).join(' | '));
showNUTSPanel('DE11');
out.push('DE11面板='+document.getElementById('pName').textContent+'|'+document.getElementById('pMetrics').textContent.replace(/\\s+/g,' ').slice(0,80));
document.body.insertAdjacentHTML('beforeend','<pre id="eu">VERIFY '+out.join(' || ')+'</pre>');
},2500);"""

TRIGGER_FR = """try{
DRILLABLE['FR'].load();
setTimeout(function(){
try{
var out=[]; out.push('FR_LEVEL='+currentLevel+'|NUTS='+currentNUTS);
out.push('FR面板='+document.getElementById('pName').textContent);
var ri=document.querySelectorAll('.rank-item'); out.push('FR排行='+ri.length+'条');
showNUTSPanel('FR10');
out.push('FR10面板='+document.getElementById('pName').textContent+'|'+document.getElementById('pMetrics').textContent.replace(/\\s+/g,' ').slice(0,60));
document.body.insertAdjacentHTML('beforeend','<pre id="eu">VERIFY '+out.join(' || ')+'</pre>');
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="eu">VERIFY ERR:'+e.message+'</pre>')}
},4000);
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="eu">VERIFY LOADERR:'+e.message+'</pre>')}
"""

url1, w1 = make_variant("eu_de.html", TRIGGER_DE, 14)
dom1 = dump(url1, w1)
p1 = [m for m in re.findall(r'<pre id="eu">(.*?)</pre>', dom1, re.S) if m.startswith('VERIFY')]
print("德国下钻:", p1[-1][:400] if p1 else "未获取")

url2, w2 = make_variant("eu_fr.html", TRIGGER_FR, 14)
dom2 = dump(url2, w2)
p2 = [m for m in re.findall(r'<pre id="eu">(.*?)</pre>', dom2, re.S) if m.startswith('VERIFY')]
print("法国+对比:", p2[-1][:300] if p2 else "未获取")

# 3. 新国家抽查（希腊）：WB ISO=GR 别名 → loadNUTS("EL")，验证 EU27 扩展下钻
TRIGGER_EL = """var c=BY_EN['Greece']; var d=DRILLABLE[c[2]]; if(d){ d.load(); }
setTimeout(function(){
var out=[];
out.push('LEVEL='+currentLevel+'|NUTS='+currentNUTS);
out.push('METRICS='+(window.EU_METRICS?'已加载('+Object.keys(window.EU_METRICS).length+')':'未加载'));
out.push('EL30reg='+(regNUTS('EL30')?'有':'无')+'|gdp='+(regNUTS('EL30')?regGet(regNUTS('EL30'),'gdp',2023):'null'));
var rk=LAYERS.nuts.rank(); out.push('rank_raw='+rk.length+'条');
var ri=document.querySelectorAll('.rank-item'); out.push('dom排行='+ri.length+'条');
document.body.insertAdjacentHTML('beforeend','<pre id="eu">VERIFY '+out.join(' || ')+'</pre>');
},4500);"""

url3, w3 = make_variant("eu_el.html", TRIGGER_EL, 16)
dom3 = dump(url3, w3)
p3 = [m for m in re.findall(r'<pre id="eu">(.*?)</pre>', dom3, re.S) if m.startswith('VERIFY')]
print("希腊(GR别名→EL):", p3[-1][:300] if p3 else "未获取")
