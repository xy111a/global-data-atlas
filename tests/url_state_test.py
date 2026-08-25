#!/usr/bin/env python3
"""优化3 URL 状态持久化验证（最终版）：
   探针运行段输出 '<pre id="st">VERIFY&gt;...'（dump-dom 里 > 转义为 &gt;）；
   匹配 VERIFY&gt; 前缀 + html.unescape 还原 &amp;，排除注入源码段（VERIFY&gt;'+ 形式）"""
import subprocess, os, re, html as htmllib, json

CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(p):
            CHROME = p; break
assert CHROME and os.path.exists(CHROME), "未找到 Chrome/Chromium，请设 CHROME_BIN"
os.makedirs("atlas_test", exist_ok=True)

def make_variant(name, trigger_js):
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

def runtime_out(dom):
    pres = [m for m in re.findall(r'<pre id="st">(.*?)</pre>', dom, re.S)
            if m.startswith('VERIFY&gt;') and not m.startswith("VERIFY&gt;'")]
    return htmllib.unescape(pres[-1][10:]) if pres else None   # 去掉 'VERIFY&gt;' 前缀（10字符）并还原 &amp;

# ---------- 1. save ----------
TRIGGER1 = """DRILLABLE['CN'].load();
setTimeout(function(){
showProvincePanel('广东');
setTimeout(function(){
document.body.insertAdjacentHTML('beforeend','<pre id="st">VERIFY>' + location.hash + '</pre>');
},600);
},2500);"""
dom1 = dump(make_variant("url_save.html", TRIGGER1), 14)
out1 = runtime_out(dom1)
hash_arg = out1.lstrip("#") if out1 else ""
print("save hash:", ("#"+hash_arg)[:120])
ok_save = out1 and all(k in hash_arg for k in ["level=china", "metric=gdp", "sel="])
print("  save 编码:", "OK ✅" if ok_save else "FAIL ❌")

# ---------- 2. restore ----------
html = open("global-data-atlas.html", encoding="utf-8").read()
inject2 = """<script>window.addEventListener('load',function(){
var t=0;var iv=setInterval(function(){t++;
if(currentLevel!=='world'||t>15){clearInterval(iv);
var o=[];o.push('LEVEL='+currentLevel+'|面板='+document.getElementById('introSum').textContent);
o.push('指标='+metric+'|年份='+dataYear);
document.body.insertAdjacentHTML('beforeend','<pre id="st">VERIFY>' + o.join(' || ') + '</pre>');
}},1000)});</script>"""
html = html.replace("</body>", inject2 + "\n</body>")
p2 = os.path.join("atlas_test", "url_restore.html")
open(p2, "w", encoding="utf-8").write(html)
url2 = "file://" + os.path.abspath(p2) + ("#" + hash_arg if hash_arg else "")
dom2 = dump(url2, 20)
out2 = runtime_out(dom2)
print("restore:", out2 if out2 else "未获取")
ok_restore = out2 and "LEVEL=china" in out2 and "广东" in out2
print("  restore:", "OK ✅" if ok_restore else "FAIL ❌")
