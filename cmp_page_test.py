#!/usr/bin/env python3
"""compare.html 独立对比页验证：?add 参数 / 图表渲染 / 搜索添加 / 指标切换"""
import subprocess, os, re

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
os.makedirs("atlas_test", exist_ok=True)

def dump(url, wait):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait+20)
    return r.stdout.decode("utf-8", "replace")

# 1. ?add 参数：country:CN + country:IN → 对比列表 2 项 + 图表渲染
url1 = "file://" + os.path.abspath("compare.html") + "?add=country:CN&add=country:IN"
dom1 = dump(url1, 10)
has_items = "对比列表（2 项）" in dom1
has_canvas = "trendChart" in dom1 and "canvas" in dom1
print(f"1. add 参数: 列表2项={'是' if has_items else '否'} 图表容器={'是' if has_canvas else '否'}")

# 2. 搜索添加（探针调 doAddSearch → 点击第一个结果）
html = open("compare.html", encoding="utf-8").read()
inject = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
doAddSearch('印度');
setTimeout(function(){
var first=document.querySelector('#addResults [data-add]');
if(first){ first.click(); }
setTimeout(function(){
var h=document.querySelector('#list h3').textContent;
document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({h:h})+'</pre>');
},400);
},400);
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},800);});</script>"""
html = html.replace("</body>", inject + "\n</body>")
p2 = os.path.join("atlas_test", "cmp_search.html")
open(p2, "w", encoding="utf-8").write(html)
dom2 = dump("file://" + os.path.abspath(p2), 12)
pres = [m for m in re.findall(r'<pre id="ck">R(.*?)</pre>', dom2, re.S) if not m.startswith("'+")]
print("2. 搜索添加:", pres[-1][:120] if pres else "未获取")
