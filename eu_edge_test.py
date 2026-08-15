#!/usr/bin/env python3
"""欧盟边界行为验证：指标切换守卫/年份切换/对比趋势图/移动端"""
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
    return "file://" + os.path.abspath(p)

def dump(url, wait):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait+20)
    return r.stdout.decode("utf-8", "replace")

# 1. 欧盟层指标切换：切到 trade（scope=world 指标）应被守卫拒绝
TRIGGER1 = """DRILLABLE['DE'].load();
setTimeout(function(){
var out=[];
// 切到 trade（世界层专属指标）—— updateMetricButtons 应禁用
var tb=document.querySelector('#metricSeg button[data-m="trade"]');
out.push('trade按钮disabled='+ (tb?tb.disabled:'无按钮'));
// 年份切换（单年数据应无变化但重绘正常）
var ys=document.getElementById('yearSel'); ys.value='2020'; 
var ev=new Event('change'); ys.dispatchEvent(ev);
setTimeout(function(){ out.push('切年后LEVEL='+currentLevel+'|面板='+document.getElementById('introSum').textContent); 
document.body.insertAdjacentHTML('beforeend','<pre id="eu2">VERIFY '+out.join(' || ')+'</pre>'); },800);
},2500);"""
dom1 = dump(make_variant("eu_edge1.html", TRIGGER1, 15), 15)
p1 = [m for m in re.findall(r'<pre id="eu2">(.*?)</pre>', dom1, re.S) if m.startswith('VERIFY')]
print("指标守卫+年份切换:", p1[-1][:250] if p1 else "未获取")

# 2. 对比趋势图：德法各一区加入后 ≥2 应渲染 trendChart
TRIGGER2 = """DRILLABLE['DE'].load();
setTimeout(function(){
cmpHandleClick('nutspref','Stuttgart','DE11');
cmpHandleClick('nutspref','Ile de France','FR10');
setTimeout(function(){
var out=[];
out.push('对比数='+cmpList.length);
out.push('趋势图='+(document.getElementById('trendChart')?'有':'无'));
document.body.insertAdjacentHTML('beforeend','<pre id="eu2">VERIFY '+out.join(' || ')+'</pre>');
},800);
},2500);"""
dom2 = dump(make_variant("eu_edge2.html", TRIGGER2, 15), 15)
p2 = [m for m in re.findall(r'<pre id="eu2">(.*?)</pre>', dom2, re.S) if m.startswith('VERIFY')]
print("对比趋势图:", p2[-1][:250] if p2 else "未获取")

# 3. 移动端欧盟（375px）
html = open("global-data-atlas.html", encoding="utf-8").read()
inject3 = ("<script>window.addEventListener('load',function(){setTimeout(function(){"
           "try{DRILLABLE['DE'].load();}catch(e){}},600);});</script>")
html = html.replace("</body>", inject3 + "\n</body>")
p3 = os.path.join("atlas_test", "eu_mobile.html")
open(p3, "w", encoding="utf-8").write(html)
cmd3 = [CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
        "--window-size=375,812", "--virtual-time-budget=14000",
        "--screenshot=atlas_test/eu_mobile.png", "file://" + os.path.abspath(p3)]
subprocess.run(cmd3, capture_output=True, timeout=35)
sz = os.path.getsize("atlas_test/eu_mobile.png") if os.path.exists("atlas_test/eu_mobile.png") else 0
print(f"移动端欧盟截图: {sz}b {'OK' if sz>40000 else 'FAIL'}")
