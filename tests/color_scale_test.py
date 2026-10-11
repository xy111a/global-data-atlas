#!/usr/bin/env python3
"""T7 回归：地图配色刻度「线性 ↔ 对数」切换。
断言：
  1) 默认线性：visualMap min/max 为真实量级（GDP 为巨额实数）
  2) 切对数：min/max 落在对数量级（log10，远小于实数），标题标注「对数刻度」
  3) 对数模式下 series 数据仍携带 reg/cn（tooltip 走 reg 取真实值，不受 log 变换影响）
  4) 再次点击可切回线性
  5) 中国省级层同样生效（paintGeoMap 骨架共用 buildColorScale）
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

SNAP = """function __snapScale(){
  var o=chart.getOption();
  /* ECharts5：visualMap 单对象时 getOption 返回 object；多实例时为 array —— 两种都兼容 */
  var raw=o.visualMap;
  var vm=(Array.isArray(raw)?raw[0]:raw)||{};
  var sd=(o.series&&o.series[0]&&o.series[0].data)||[];
  var hasReg=false, sampleVal=null;
  for(var i=0;i<sd.length;i++){
    if(sd[i]&&sd[i].reg)hasReg=true;
    if(sd[i]&&typeof sd[i].value==='number'&&sampleVal===null)sampleVal=sd[i].value;
    break;   // 只取首项采样
  }
  var btn=document.getElementById('scaleBtn');
  var note=document.getElementById('scaleNote');
  /* colorScale 是 let 顶层绑定（非 window 属性），必须用裸引用读 */
  return {mode:(typeof colorScale!=='undefined')?colorScale:null,
          vmin:vm.min, vmax:vm.max, title:vm.title||'',
          hasReg:hasReg, sampleVal:sampleVal, btn:btn?btn.textContent.trim():'',
          note:note?note.textContent.trim():''};
}"""

def build(tmp_name, inject, wait):
    html = open("global-data-atlas.html", encoding="utf-8").read()
    base = "<base href=\"file://" + os.path.abspath(".") + "/\">"
    html = html.replace("</head>", base + "</head>", 1)
    html = html.replace("</body>", "<script>" + SNAP + "</script>\n" + inject + "\n</body>")
    p = os.path.join("atlas_test", tmp_name)
    open(p, "w", encoding="utf-8").write(html)
    return runtime_out(dump("file://" + os.path.abspath(p), wait))

# 世界层：linear → log → linear
inject_world = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
  var out={};
  out.s1=__snapScale();
  document.getElementById('scaleBtn').click();
  setTimeout(function(){
    out.s2=__snapScale();
    document.getElementById('scaleBtn').click();
    setTimeout(function(){
      out.s3=__snapScale();
      document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify(out)+'</pre>');
    },900);
  },900);
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},1500);});</script>"""

o1 = build("color_scale_world.html", inject_world, 20)

def is_float(x):
    return isinstance(x, (int, float))

if not o1 or "err" in o1:
    check("配色刻度切换脚本执行", False, f"({o1})")
else:
    s1, s2, s3 = o1.get("s1", {}), o1.get("s2", {}), o1.get("s3", {})
    check("默认 线性 模式", s1.get("mode") == "linear", f"({s1.get('mode')})")
    check("线性 visualMap 为真实量级(GDP 巨额)",
          is_float(s1.get("vmax")) and s1.get("vmax", 0) > 1e10,
          f"(min={s1.get('vmin')} max={s1.get('vmax')})")
    check("按钮初始文案为线性", "线性" in (s1.get("btn") or ""), f"({s1.get('btn')})")
    check("切 对数 生效", s2.get("mode") == "log", f"({s2.get('mode')})")
    check("对数 visualMap 落在对数量级",
          is_float(s2.get("vmax")) and 0 < s2.get("vmax", 0) < 100,
          f"(min={s2.get('vmin')} max={s2.get('vmax')})")
    check("对数模式标题标注对数刻度",
          "对数刻度" in (s2.get("title") or ""), f"({s2.get('title')})")
    check("对数模式 series 值已 log 变换",
          is_float(s2.get("sampleVal")) and s2.get("sampleVal", 0) < 100,
          f"(sample={s2.get('sampleVal')})")
    check("对数模式 tooltip 数据完整(含 reg)",
          s2.get("hasReg") is True, f"(hasReg={s2.get('hasReg')})")
    check("页脚标注同步为对数刻度",
          "对数" in (s2.get("note") or ""), f"({s2.get('note')})")
    check("再切回线性恢复真实量级",
          s3.get("mode") == "linear" and is_float(s3.get("vmax")) and s3.get("vmax", 0) > 1e10,
          f"(mode={s3.get('mode')} max={s3.get('vmax')})")

# 中国省级层（paintGeoMap 骨架）同样生效
inject_cn = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
  DRILLABLE['CN'].load();
  setTimeout(function(){
    var out={};
    out.c1=__snapScale();
    document.getElementById('scaleBtn').click();
    setTimeout(function(){
      out.c2=__snapScale();
      document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify(out)+'</pre>');
    },1200);
  },3000);
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>')}
},1200);});</script>"""

o2 = build("color_scale_cn.html", inject_cn, 24)

if not o2 or "err" in o2:
    check("中国省级配色刻度脚本执行", False, f"({o2})")
else:
    c1, c2 = o2.get("c1", {}), o2.get("c2", {})
    check("省级层线性为真实量级",
          c1.get("mode") == "linear" and is_float(c1.get("vmax")) and c1.get("vmax", 0) > 1e10,
          f"(mode={c1.get('mode')} max={c1.get('vmax')})")
    check("省级层切对数生效",
          c2.get("mode") == "log" and is_float(c2.get("vmax")) and 0 < c2.get("vmax", 0) < 100,
          f"(mode={c2.get('mode')} max={c2.get('vmax')})")

print(f"\n配色刻度切换(T7)回归: {ok}/{total} 通过")
exit(0 if ok == total else 1)
