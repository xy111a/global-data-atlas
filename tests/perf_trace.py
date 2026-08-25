#!/usr/bin/env python3
"""L3i 运行时性能实测：headless Chrome 采集真实运行指标。

采集项：
  - navigation timing: domContentLoadedEventEnd / loadEventEnd（相对 startTime，ms）
  - JS 堆内存: performance.memory.usedJSHeapSize / jsHeapSizeLimit（Chrome 专属，headless 可能缺）
  - 交互流畅度: 1s 内 requestAnimationFrame 计数（≈FPS，空闲主线程应接近 60）
  - 渲染: ECharts canvas 是否绘制(width>0)
  - 结构规模: DOM 节点数 / <script> 数（复杂度代理）

门禁阈值（软/硬）：
  硬失败: 解析失败 / canvas 未绘制
  软告警(非失败): domLoad>5000ms / fullLoad>8000ms / heapUsed>120MB
  说明: FPS 在 headless --virtual-time-budget 下 rAF 仅触发一次（虚拟时钟不推进帧），
        不能代表真实交互帧率，故仅作信息输出、不纳入门禁。
结果写 atlas_test/perf_report.json。
"""
import subprocess, os, re, json, sys

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
var m={};
var nav=performance.getEntriesByType('navigation')[0];
if(nav){ m.domLoad=Math.round(nav.domContentLoadedEventEnd-nav.startTime); m.fullLoad=Math.round(nav.loadEventEnd-nav.startTime); }
else { var t=performance.timing; m.domLoad=t.domContentLoadedEventEnd-t.navigationStart; m.fullLoad=t.loadEventEnd-t.navigationStart; }
if(performance.memory){ m.heapUsedMB=Math.round(performance.memory.usedJSHeapSize/1048576); m.heapLimitMB=Math.round(performance.memory.jsHeapSizeLimit/1048576); }
function canvasPainted(){ var cs=document.querySelectorAll('canvas'); for(var i=0;i<cs.length;i++){ if(cs[i].width>0&&cs[i].height>0) return true; } return false; }
m.canvasPainted=canvasPainted();
m.domNodes=document.getElementsByTagName('*').length;
m.scripts=document.getElementsByTagName('script').length;
// FPS: 1s 内 rAF 计数
var fps=0, start=performance.now();
function loop(){ fps++; if(performance.now()-start<1000) requestAnimationFrame(loop); else { m.fps=fps; finish(); } }
function finish(){ document.body.insertAdjacentHTML('beforeend','<pre id=\"ck\">R'+JSON.stringify(m)+'</pre>'); }
requestAnimationFrame(loop);
}catch(e){ document.body.insertAdjacentHTML('beforeend','<pre id=\"ck\">R'+JSON.stringify({err:e.message})+'</pre>'); }
},1200);});</script>"""
html = html.replace("</body>", inject + "\n</body>")
p = os.path.join("atlas_test", "perf_trace.html")
open(p, "w", encoding="utf-8").write(html)
r = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                    "--enable-precise-memory-info", "--virtual-time-budget=30000",
                    "--dump-dom", "file://" + os.path.abspath(p)],
                   capture_output=True, timeout=90)
dom = r.stdout.decode("utf-8", "replace")
pres = [m for m in re.findall(r'<pre id="ck">R(.*?)</pre>', dom, re.S) if not m.startswith("'+")]
raw = pres[-1] if pres else "{}"
try:
    m = json.loads(raw)
except Exception as e:
    print("  解析失败:", raw[:200], e); sys.exit(1)

if "err" in m:
    print("  ✗ 采集异常:", m["err"]); sys.exit(1)

with open(os.path.join("atlas_test", "perf_report.json"), "w", encoding="utf-8") as f:
    json.dump(m, f, ensure_ascii=False, indent=2)

print(f"  DOMContentLoaded: {m.get('domLoad','?')} ms")
print(f"  Load(full):       {m.get('fullLoad','?')} ms")
print(f"  FPS(1s rAF):       {m.get('fps','?')}")
print(f"  JS Heap:           {m.get('heapUsedMB','?')}/{m.get('heapLimitMB','?')} MB")
print(f"  Canvas painted:    {m.get('canvasPainted','?')}")
print(f"  DOM nodes:         {m.get('domNodes','?')}  scripts: {m.get('scripts','?')}")

# 门禁
hard = []
if m.get("canvasPainted") is False:
    hard.append("canvas 未绘制")
soft = []
if m.get("fps") is not None and m["fps"] < 30:
    soft.append(f"FPS {m['fps']} (headless 虚拟时钟下仅触发一次 rAF，非真实交互帧率，仅供参考)")
if m.get("domLoad") and m["domLoad"] > 5000: soft.append(f"domLoad {m['domLoad']}ms>5s")
if m.get("fullLoad") and m["fullLoad"] > 8000: soft.append(f"fullLoad {m['fullLoad']}ms>8s")
if m.get("heapUsedMB") and m["heapUsedMB"] > 120: soft.append(f"heap {m['heapUsedMB']}MB>120MB")

if hard:
    print("  ✗ 性能硬门禁未过:", "; ".join(hard)); sys.exit(1)
if soft:
    print("  ⚠ 性能软告警(不阻断):", "; ".join(soft))
print("  ✓ L3i 通过")
