#!/usr/bin/env python3
"""P3·C1 关系散点渲染回归。
   吸取 visualMap 教训（配置存在≠组件注册/渲染）：断言 ScatterChart 组件模型真的创建、
   点确实进入数据模型（getData().count()），且未 import ScatterChart 时会失败。
   另测「切换 Y 指标重绘不报错」。headless 无法验下载/交互，故断言落在实例与渲染模型上。"""
import subprocess, os, re, json, base64, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(p):
            CHROME = p; break
assert CHROME and os.path.exists(CHROME), "未找到 Chrome/Chromium，请设 CHROME_BIN"
os.makedirs("atlas_test", exist_ok=True)

TRIGGER = r"""
var out={};
function emit(){ var pre=document.createElement('pre'); pre.id='sc';
  pre.textContent='B'+btoa(unescape(encodeURIComponent(JSON.stringify(out)))); document.body.appendChild(pre); }
try{
  out.fnOpen=(typeof openScatter==='function');
  out.hasBtn=!!document.getElementById('scatterBtn');
  out.hasOverlay=!!document.getElementById('scatterOverlay');
  dataYear="2023";                 // 用确定有数据的年份，避开 2025 国家缺测的歧义
  try{ openScatter(); out.openErr=false; }catch(e){ out.openErr=''+e.message; }
  out.overlayOpen=document.getElementById('scatterOverlay').classList.contains('open');
  var el=document.getElementById('scatterChart');
  var inst=window.echarts&&echarts.getInstanceByDom(el);
  out.instCreated=!!inst;
  if(inst){
    var opt=inst.getOption();
    out.seriesType=opt.series&&opt.series[0]&&opt.series[0].type;
    out.dataLen=(opt.series&&opt.series[0]&&opt.series[0].data)?opt.series[0].data.length:0;
    // 渲染级：scatter 组件模型确实创建（未 import 则空）+ 点进入数据模型
    out.scatterModelLen=inst.getModel().getSeriesByType('scatter').length;
    try{ out.pointCount=inst.getModel().getSeriesByIndex(0).getData().count(); }catch(e){ out.pointCount=-1; }
    out.xAxisType=opt.xAxis&&opt.xAxis[0]&&opt.xAxis[0].type;   // gdppc→log
  }
  // 切换 Y 指标（life→pop）重绘不报错、仍是 scatter
  try{ var ys=document.getElementById('scY'); ys.value='pop'; ys.dispatchEvent(new Event('change')); out.switchErr=false; }catch(e){ out.switchErr=''+e.message; }
  var inst2=echarts.getInstanceByDom(el);
  out.switchSeriesType=inst2&&inst2.getOption().series[0].type;
  out.err=null;
}catch(e){ out.err=''+e.message; }
emit();
"""

def run(variant, wait=14):
    html = open("global-data-atlas.html", encoding="utf-8").read()
    html = html.replace("</head>", f'<base href="file://{ROOT}/"></head>')
    html = html.replace("</body>", "<script>window.addEventListener('load',function(){setTimeout(function(){"
                        + TRIGGER + "},900);});</script>\n</body>")
    pg = os.path.join("atlas_test", variant)
    open(pg, "w", encoding="utf-8").write(html)
    dom = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                          f"--virtual-time-budget={wait*1000}", "--dump-dom",
                          "file://" + os.path.abspath(pg)],
                         capture_output=True, timeout=wait+40).stdout.decode("utf-8", "replace")
    pres = re.findall(r'<pre id="sc">B(.*?)</pre>', dom, re.S)
    if not pres:
        return None
    return json.loads(base64.b64decode(pres[-1].strip()).decode("utf-8"))

ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

out = run("scatter_probe.html")
if out is None:
    check("探针产出结果", False); print(f"\n散点回归: {ok}/{total} 通过"); sys.exit(1)

check("探针无异常", not out.get("err"), f"({out.get('err')})")
check("openScatter / scatterBtn / 浮层 就位",
      out.get("fnOpen") and out.get("hasBtn") and out.get("hasOverlay"))
check("打开浮层且无异常", out.get("overlayOpen") is True and out.get("openErr") is False,
      f"(open={out.get('overlayOpen')} err={out.get('openErr')})")
check("echarts 实例已在 #scatterChart 创建", out.get("instCreated") is True)
check("series[0].type === 'scatter'", out.get("seriesType") == "scatter", f"({out.get('seriesType')})")
check("ScatterChart 组件模型已创建（=1，未 import 会 0）",
      out.get("scatterModelLen") == 1, f"(modelLen={out.get('scatterModelLen')})")
check("点真正进入数据模型 count ≥ 100", (out.get("pointCount") or 0) >= 100, f"(count={out.get('pointCount')})")
check("gdppc 作 X 轴用对数刻度", out.get("xAxisType") == "log", f"({out.get('xAxisType')})")
check("切换 Y 指标重绘不报错且仍 scatter",
      out.get("switchErr") is False and out.get("switchSeriesType") == "scatter",
      f"(switchErr={out.get('switchErr')} type={out.get('switchSeriesType')})")

print(f"\n散点回归: {ok}/{total} 通过")
sys.exit(0 if ok == total else 1)
