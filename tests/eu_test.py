#!/usr/bin/env python3
"""欧盟 NUTS2 下钻验证：德国 NUTS2 加载 + 面板 + 排行 + 泛化下钻"""
import subprocess, os, re

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
os.makedirs("atlas_test", exist_ok=True)

def make_variant(name, trigger_js, wait):
    html = open("global-data-atlas.html", encoding="utf-8").read()
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

TRIGGER_FR = """DRILLABLE['FR'].load();
setTimeout(function(){
var out=[]; out.push('FR_LEVEL='+currentLevel+'|NUTS='+currentNUTS);
out.push('FR面板='+document.getElementById('pName').textContent);
var ri=document.querySelectorAll('.rank-item'); out.push('FR排行='+ri.length+'条');
cmpHandleClick('nutspref','Baden-Württemberg','DE1');
cmpHandleClick('nutspref','Île de France','FR10');
out.push('对比数='+cmpList.length);
document.body.insertAdjacentHTML('beforeend','<pre id="eu">VERIFY '+out.join(' || ')+'</pre>');
},2500);"""

url1, w1 = make_variant("eu_de.html", TRIGGER_DE, 14)
dom1 = dump(url1, w1)
p1 = [m for m in re.findall(r'<pre id="eu">(.*?)</pre>', dom1, re.S) if m.startswith('VERIFY')]
print("德国下钻:", p1[-1][:400] if p1 else "未获取")

url2, w2 = make_variant("eu_fr.html", TRIGGER_FR, 14)
dom2 = dump(url2, w2)
p2 = [m for m in re.findall(r'<pre id="eu">(.*?)</pre>', dom2, re.S) if m.startswith('VERIFY')]
print("法国+对比:", p2[-1][:300] if p2 else "未获取")
