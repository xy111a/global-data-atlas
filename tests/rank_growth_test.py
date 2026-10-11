#!/usr/bin/env python3
"""T6 回归：区域排行榜「数值 ↔ 增长」模式切换。
断言：
  1) 默认 numeric 模式：排行有项，值按指标口径（GDP→$，含货币符号）
  2) 切到 growth 模式：标题含「增长」+ 基准区间，项值按百分比（含 %）
  3) 切回 numeric 模式：恢复 $ 口径
  4) 下钻层（美国州）growth 排行同样有数据（多层 rank(mode) 均生效）
"""
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

# helper 注入：读取当前排行区状态
def snap():
    return """function __snapRank(){
      var box=document.getElementById('rank');
      var sum=box?box.querySelector('summary'):null;
      var items=box?box.querySelectorAll('.rank-item'):[];
      var vals=[]; for(var i=0;i<Math.min(items.length,5);i++){
        var rv=items[i].querySelector('.rv'); if(rv) vals.push(rv.textContent.trim());
      }
      return {mode:rankMode, summary:sum?sum.textContent.trim():'', count:items.length, vals:vals};
    }"""

# 1+2+3. 世界层：value → growth → value
inject1 = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
  var out={};
  out.v1=__snapRank();
  var g=document.querySelector('.rank-toggle button[data-mode="growth"]');
  if(!g){ out.err='no growth button'; throw new Error('no growth btn'); }
  g.click();
  setTimeout(function(){
    out.v2=__snapRank();
    var b=document.querySelector('.rank-toggle button[data-mode="value"]');
    if(b) b.click();
    setTimeout(function(){
      out.v3=__snapRank();
      document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify(out)+'</pre>');
    },500);
  },500);
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},1500);});</script>"""

html = open("global-data-atlas.html", encoding="utf-8").read()
base = "<base href=\"file://" + os.path.abspath(".") + "/\">"
html = html.replace("</head>", base + "</head>", 1)
html = html.replace("</body>", "<script>" + snap() + "</script>\n" + inject1 + "\n</body>")
p1 = os.path.join("atlas_test", "rank_growth_world.html")
open(p1, "w", encoding="utf-8").write(html)
o1 = runtime_out(dump("file://" + os.path.abspath(p1), 18))

if not o1 or "err" in o1:
    check("排行模式切换脚本执行", False, f"({o1})")
else:
    v1, v2, v3 = o1.get("v1", {}), o1.get("v2", {}), o1.get("v3", {})
    check("默认 numeric 模式有排行项", v1.get("count", 0) > 0,
          f"(mode={v1.get('mode')} n={v1.get('count')} sample={v1.get('vals')})")
    check("numeric 排行有活跃 toggle", v1.get("mode") == "value", f"({v1.get('mode')})")
    check("切 growth 模式生效", v2.get("mode") == "growth",
          f"(mode={v2.get('mode')} summary={v2.get('summary')})")
    check("growth 标题标注增长区间",
          bool(v2.get("summary")) and "增长" in (v2.get("summary") or ""),
          f"({v2.get('summary')})")
    check("growth 排行有项且按百分比", v2.get("count", 0) > 0
          and all("%" in s for s in (v2.get("vals") or []) if s),
          f"(n={v2.get('count')} vals={v2.get('vals')})")
    check("切回 numeric 恢复", v3.get("mode") == "value" and v3.get("count", 0) > 0,
          f"(mode={v3.get('mode')} n={v3.get('count')} vals={v3.get('vals')})")
    check("numeric 值仍按货币口径($)",
          any("$" in s for s in (v3.get("vals") or [])), f"({v3.get('vals')})")

# 4. 下钻层（美国州）：growth 排行应有数据
inject2 = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
  loadUS();
  setTimeout(function(){
    var out={};
    out.v1=__snapRank();
    var g=document.querySelector('.rank-toggle button[data-mode="growth"]');
    if(g) g.click();
    setTimeout(function(){
      out.v2=__snapRank();
      document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify(out)+'</pre>');
    },600);
  },2600);
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},1200);});</script>"""

html2 = open("global-data-atlas.html", encoding="utf-8").read()
html2 = html2.replace("</head>", base + "</head>", 1)
html2 = html2.replace("</body>", "<script>" + snap() + "</script>\n" + inject2 + "\n</body>")
p2 = os.path.join("atlas_test", "rank_growth_us.html")
open(p2, "w", encoding="utf-8").write(html2)
o2 = runtime_out(dump("file://" + os.path.abspath(p2), 20))

if not o2 or "err" in o2:
    check("美国州 growth 排行执行", False, f"({o2})")
else:
    u1, u2 = o2.get("v1", {}), o2.get("v2", {})
    check("美国州 numeric 排行有项", u1.get("count", 0) > 0,
          f"(n={u1.get('count')} sample={u1.get('vals')})")
    check("美国州 growth 排行有项", u2.get("count", 0) > 0 and u2.get("mode") == "growth",
          f"(n={u2.get('count')} vals={u2.get('vals')})")
    check("美国州 growth 按百分比",
          all("%" in s for s in (u2.get("vals") or []) if s), f"({u2.get('vals')})")

print(f"\n排行模式切换(T6)回归: {ok}/{total} 通过")
exit(0 if ok == total else 1)
