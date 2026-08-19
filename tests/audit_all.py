#!/usr/bin/env python3
"""全面盘点：各层 总览/单击/双击 的仪表盘块 + 面板残留组件"""
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

html = open("global-data-atlas.html", encoding="utf-8").read()
inject = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
function blocks(){ return Array.from(document.querySelectorAll('#panel details.fold summary')).map(function(s){return s.textContent.trim();}); }
function resid(){ 
  var r=[];
  // 面板内非 details.fold 的直接子元素（潜在残留）
  Array.from(document.getElementById('panel').children).forEach(function(el){
    if(el.tagName==='DETAILS') return;
    var vis=el.style.display!=='none' && el.offsetParent!==null;
    var txt=(el.textContent||'').trim();
    r.push(el.id+':'+el.tagName+':['+txt.slice(0,15)+']:'+(vis?'可见':'隐藏'));
  });
  return r;
}
var out=[];
function step(label, fn, wait){ return new Promise(function(res){ fn(); setTimeout(function(){ out.push(label+'|块='+JSON.stringify(blocks())+'|面板残留='+JSON.stringify(resid())); res(); }, wait); }); }
(async function(){
  await step('世界总览', function(){}, 1200);
  await step('单击国家CN', function(){ showCountry(COUNTRIES.find(function(c){return c[2]==='CN'})); }, 800);
  await step('双击CN下钻→中国总览', function(){ DRILLABLE['CN'].load(); }, 1500);
  await step('单击省广东', function(){ showProvincePanel('广东'); }, 800);
  await step('双击省→省级总览', function(){ loadProvince('浙江','330000'); }, 1500);
  await step('单击市杭州', function(){ showCityPanel('杭州市','330100',330000); }, 800);
  await step('双击US→美国总览', function(){ DRILLABLE['US'].load(); }, 1500);
  await step('单击州CA', function(){ showUSStatePanel('California'); }, 800);
  await step('双击JP→日本总览', function(){ DRILLABLE['JP'].load(); }, 1500);
  await step('单击县', function(){ showJapanPrefPanel('北海道'); }, 800);
  await step('双击DE→欧盟总览', function(){ DRILLABLE['DE'].load(); }, 1500);
  await step('单击NUTS', function(){ showNUTSPanel('DE11'); }, 800);
  document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify(out)+'</pre>');
})();
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},800);});</script>"""
html = html.replace("</body>", inject + "\n</body>")
p = os.path.join("atlas_test", "audit_all.html")
open(p, "w", encoding="utf-8").write(html)
r = subprocess.run([CHROME,"--headless","--no-sandbox","--disable-gpu","--virtual-time-budget=30000","--dump-dom","file://"+os.path.abspath(p)],
                   capture_output=True, timeout=60)
dom = r.stdout.decode("utf-8","replace")
pres = [m for m in re.findall(r'<pre id="ck">R(.*?)</pre>', dom, re.S) if not m.startswith("'+")]
out = pres[-1] if pres else "未获取"
import json
try:
    for row in json.loads(out):
        print("  ", row)
except Exception as e:
    print(out, e)
