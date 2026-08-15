#!/usr/bin/env python3
"""compare.html 层级点选验证：层级切换 / 点选加入 / 已选标记 / 搜索过滤"""
import subprocess, os, re

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
os.makedirs("atlas_test", exist_ok=True)

def dump(url, wait):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait+20)
    return r.stdout.decode("utf-8", "replace")

def runtime_out(dom):
    pres = [m for m in re.findall(r'<pre id="ck">R(.*?)</pre>', dom, re.S) if not m.startswith("'+")]
    return pres[-1] if pres else None

html = open("compare.html", encoding="utf-8").read()
inject = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
var out=[];
// 1. 默认国家层：单元列表应含 214 项（含中国）
out.push('默认国家层单元数='+document.querySelectorAll('#unitList .unit').length);
// 2. 切到省级层
document.getElementById('levelSel').value='prov';
document.getElementById('levelSel').dispatchEvent(new Event('change'));
out.push('省级单元数='+document.querySelectorAll('#unitList .unit').length);
// 3. 点选广东加入
var gd=Array.from(document.querySelectorAll('#unitList .unit')).find(u=>u.textContent.includes('广东'));
if(gd) gd.click();
out.push('点选后列表='+document.getElementById('cmpHead').textContent);
out.push('广东已选标记='+(document.querySelector('#unitList .unit.added')?'有':'无'));
// 4. 切回国家层，搜索过滤
document.getElementById('levelSel').value='country';
document.getElementById('levelSel').dispatchEvent(new Event('change'));
document.getElementById('addInput').value='印度';
document.getElementById('addInput').dispatchEvent(new Event('input'));
out.push('国家层搜索印度='+document.querySelectorAll('#unitList .unit').length+'项');
document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify(out)+'</pre>');
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},1000);});</script>"""
html = html.replace("</body>", inject + "\n</body>")
p = os.path.join("atlas_test", "cmp_units.html")
open(p, "w", encoding="utf-8").write(html)
dom = dump("file://" + os.path.abspath(p), 12)
out = runtime_out(dom)
print("层级点选:", out if out else "未获取")
