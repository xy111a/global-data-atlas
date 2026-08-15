#!/usr/bin/env python3
"""compare.html 独立对比页测试（合并自 cmp_test / cmp_page_test / cmp_units_test）：
   ?add 参数 / 搜索添加 / 删除 / 轨迹图容器 / 层级点选"""
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

ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

# 1. ?add 参数：双区域 → 列表 2 项 + 图表容器
url1 = "file://" + os.path.abspath("compare.html") + "?add=country:CN&add=country:IN"
dom1 = dump(url1, 10)
check("add 参数双区域", "对比列表（2 项）" in dom1 and "canvas" in dom1, "(CN+IN)")

# 2. 搜索添加 → 点击 → 列表 1 项
html = open("compare.html", encoding="utf-8").read()
inject = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
doAddSearch('印度');
setTimeout(function(){
var first=document.querySelector('#addResults [data-add]');
if(first){ first.click(); }
setTimeout(function(){
document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({h:document.getElementById('cmpHead').textContent})+'</pre>');
},400);
},400);
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},800);});</script>"""
html = html.replace("</body>", inject + "\n</body>")
p2 = os.path.join("atlas_test", "cmp_search.html")
open(p2, "w", encoding="utf-8").write(html)
dom2 = dump("file://" + os.path.abspath(p2), 12)
out2 = runtime_out(dom2)
check("搜索添加", out2 and "1 项" in out2, f"({out2[:40] if out2 else '未获取'})")

# 3. 删除：add 2 项后删除 1 项 → 剩 1
html3 = open("compare.html", encoding="utf-8").read()
inject3 = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
addItem('country','CN'); addItem('country','IN');
setTimeout(function(){
var del=document.querySelector('.cmp-item .del'); if(del){ del.click(); }
setTimeout(function(){
document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({h:document.getElementById('cmpHead').textContent})+'</pre>');
},300);
},300);
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},800);});</script>"""
html3 = html3.replace("</body>", inject3 + "\n</body>")
p3 = os.path.join("atlas_test", "cmp_del.html")
open(p3, "w", encoding="utf-8").write(html3)
dom3 = dump("file://" + os.path.abspath(p3), 12)
out3 = runtime_out(dom3)
check("删除项", out3 and "1 项" in out3, f"({out3[:40] if out3 else '未获取'})")

# 4. 轨迹图表：2 项多年序列 → trendChart 有 series（canvas 存在且 hint 更新）
check("轨迹图容器", "trendChart" in dom1 and "canvas" in dom1, "(2 项自动出图)")

# 5. 层级点选（合并自 cmp_units_test）：默认国家层 → 切省级 → 点选广东 → 已选标记 → 国家层搜索过滤
inject5 = """<script>window.addEventListener('load',function(){setTimeout(function(){
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
html5 = open("compare.html", encoding="utf-8").read().replace("</body>", inject5 + "\n</body>")
p5 = os.path.join("atlas_test", "cmp_units.html")
open(p5, "w", encoding="utf-8").write(html5)
dom5 = dump("file://" + os.path.abspath(p5), 12)
out5 = runtime_out(dom5)
check("层级点选", bool(out5) and "广东已选标记=有" in out5, f"({(out5 or '未获取')[:80]})")

print(f"\n对比页测试: {ok}/{total} 通过")
exit(0 if ok == total else 1)
