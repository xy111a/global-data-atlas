#!/usr/bin/env python3
"""L3j 视觉/响应式回归：覆盖此前未审的"视觉正确性"盲区。

此前 L3h 只校验"canvas 存在 + 图例文本存在"（存在性），未审：
  - 地图几何/配色是否真的渲染（非空白/崩溃）
  - 响应式布局（移动端 375 宽是否横向溢出）
  - 桌面/移动首屏 + 下钻后的真实视觉快照

本测试用 headless Chrome 在两种视口做两件事：
  (1) DOM/视口断言（硬门禁）：canvas 已绘制、下钻后面板含"中国"、无横向溢出
      （scrollWidth<=innerWidth，分别在 1280 与 375 宽）、visualMap 高/低 图例存在。
  (2) 真实截图（DOM 取 ECharts 主画布 toDataURL 导出地图 PNG）：
      - world_desktop.png / world_mobile.png / cn_drilled_desktop.png
      - Pillow 硬校验：非空白（非背景像素占比 > 3%，否则视为地图未渲染/崩溃）
      - Pillow 软校验：与基线 tests/baseline/*.png 做 MSE 像素 diff；
        首次运行无基线则建立基线并告警（不失败）；差异过大仅软告警（跨机字体/AA 差异）。

⚠ 移动端视口必须走 CDP Emulation.setDeviceMetricsOverride 真·设备模拟：headless 下
  --window-size=375 不会真正把布局视口设为 375（会停在 500px 默认宽度），曾在 500 视口下
  误报"横向溢出"。经 CDP 真机模拟复核，320/375/414/500/600/700/768/1024/1280 全宽度
  scrollWidth==innerWidth，应用响应式正常、无需改 CSS。故移动端溢出断言改为硬门禁（CDP 下
  仍溢出才算真缺陷），无 websocket 依赖时降级跳过该断言（不再误报）。

门禁：硬失败 = DOM 断言失败 / 截图空白。软告警 = 基线 MSE 超阈 / 无基线 / 缺少依赖跳过移动断言。
"""
import subprocess, os, re, json, sys, base64, shutil

CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(p):
            CHROME = p; break
assert CHROME and os.path.exists(CHROME), "未找到 Chrome/Chromium，请设 CHROME_BIN"

from PIL import Image

# 移动端真·设备模拟需要 CDP（websocket-client）；缺失时降级为 --window-size（移动端溢出断言跳过，不再误报）
try:
    import websocket  # noqa: F401
    HAVE_WS = True
except Exception:
    HAVE_WS = False

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(ROOT)
SHOTS = os.path.join("atlas_test", "shots")
BASE = os.path.join(ROOT, "baseline")
os.makedirs(SHOTS, exist_ok=True)
os.makedirs(BASE, exist_ok=True)

# ---------- 视口 + DOM 断言（复用 #ck 注入模式） ----------
DOM_INJECT = """<script>window.addEventListener('load',function(){setTimeout(function(){
  try{
  function ptext(){ return document.getElementById('panel')?document.getElementById('panel').textContent:''; }
  function canvasPainted(){ var cs=document.querySelectorAll('canvas'); for(var i=0;i<cs.length;i++){ if(cs[i].width>0&&cs[i].height>0) return true; } return false; }
  var out={};
  out.canvas=canvasPainted();
  out.legend=(/高/.test(document.body.textContent)&&/低/.test(document.body.textContent));
  out.overflow=(document.documentElement.scrollWidth<=window.innerWidth);
  out.scrollW=document.documentElement.scrollWidth; out.innerW=window.innerWidth;
  showCountry(COUNTRIES.find(function(c){return c[2]==='CN'}));
  setTimeout(function(){
    DRILLABLE['CN'].load();
    setTimeout(function(){
      out.panelCN=/中国/.test(ptext());
      document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify(out)+'</pre>');
    }, 1800);
  }, 900);
  }catch(e){ document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({fatal:e.message})+'</pre>'); }
  }, 1500);});</script>"""

def _read_ck_dom(dom_text):
    pres = [m for m in re.findall(r'<pre id="ck">R(.*?)</pre>', dom_text, re.S) if not m.startswith("'+")]
    raw = pres[-1] if pres else "{}"
    return json.loads(raw)

def run_dom_legacy(window):
    html = open(os.path.join(PROJ, "global-data-atlas.html"), encoding="utf-8").read()
    html = html.replace("</body>", DOM_INJECT + "\n</body>")
    p = os.path.join("atlas_test", "dom_%s.html" % window.replace(",", "x"))
    open(p, "w", encoding="utf-8").write(html)
    r = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                        "--window-size=" + window, "--virtual-time-budget=40000",
                        "--dump-dom", "file://" + os.path.abspath(p)],
                       capture_output=True, timeout=90)
    return _read_ck_dom(r.stdout.decode("utf-8", "replace"))

def run_dom_cdp(width):
    """用 CDP Emulation.setDeviceMetricsOverride 真·模拟设备视口（headless 下 --window-size
    不会真正设置移动布局视口，会停在 500px 默认宽度导致横向溢出误报）。"""
    import time, tempfile, urllib.request
    from pathlib import Path as _P
    PROFILE = _P(tempfile.mkdtemp(prefix="cdpdom_"))
    TMP = _P(tempfile.mkdtemp(prefix="cdphtml_"))
    shutil.copy(os.path.join(PROJ, "global-data-atlas.html"), TMP / "gda.html")
    shutil.copytree(os.path.join(PROJ, "vendor"), TMP / "vendor", dirs_exist_ok=True)
    if os.path.isdir(os.path.join("atlas_test", "vendor")):
        shutil.copytree(os.path.join("atlas_test", "vendor"), TMP / "vendor", dirs_exist_ok=True)
    html = (TMP / "gda.html").read_text(encoding="utf-8").replace("</body>", DOM_INJECT + "\n</body>")
    (TMP / "gda.html").write_text(html, encoding="utf-8")
    port = 9341
    proc = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu",
        "--remote-allow-origins=*", "--remote-debugging-port=%d" % port,
        "--user-data-dir=%s" % PROFILE, "--window-size=800,900"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/json" % port, timeout=10) as r:
            targets = json.loads(r.read())
        ws_url = next((t["webSocketDebuggerUrl"] for t in targets if t.get("type") == "page"), None)
        ws = websocket.create_connection(ws_url, timeout=30)
        _id = [0]
        def send(method, params=None):
            _id[0] += 1
            ws.send(json.dumps({"id": _id[0], "method": method, "params": params or {}}))
            return _id[0]
        def recv_until(mid, timeout=25):
            t0 = time.time()
            while time.time() - t0 < timeout:
                try:
                    m = json.loads(ws.recv())
                except Exception:
                    continue
                if m.get("id") == mid:
                    return m
            return None
        ws.send(json.dumps({"id": 1, "method": "Page.enable", "params": {}}))
        send("Emulation.setDeviceMetricsOverride",
             {"width": width, "height": 812, "deviceScaleFactor": 2,
              "mobile": width < 768, "fitWindow": False})
        nav_id = send("Page.navigate", {"url": "file://%s/gda.html" % TMP})
        recv_until(nav_id, 10)
        time.sleep(6)
        ev_id = send("Runtime.evaluate",
                     {"expression": "(function(){var e=document.getElementById('ck');return e?e.textContent.slice(1):'';})()",
                      "returnByValue": True})
        m = recv_until(ev_id, 25)
        raw = m.get("result", {}).get("result", {}).get("value", "{}") if m else "{}"
        return json.loads(raw)
    finally:
        try: ws.close()
        except Exception: pass
        proc.terminate()
        try: proc.wait(timeout=5)
        except Exception: proc.kill()

def run_dom(window, use_cdp=False):
    if use_cdp and HAVE_WS:
        width = int(window.split(",")[0])
        return run_dom_cdp(width)
    return run_dom_legacy(window)

# ---------- 截图（chart.getDataURL 导出真实地图） ----------
def build_shot_html(kind):
    html = open(os.path.join(PROJ, "global-data-atlas.html"), encoding="utf-8").read()
    if kind == "cn_drilled":
        auto = """<script>window.addEventListener('load',function(){setTimeout(function(){
          try{ showCountry(COUNTRIES.find(function(c){return c[2]==='CN'})); setTimeout(function(){ DRILLABLE['CN'].load(); }, 1600); }catch(e){}
        }, 1200); });</script>"""
    else:
        auto = ""
    inject = auto + """<script>window.addEventListener('load',function(){setTimeout(function(){
      try{
        // chart 是顶层 let（非 window 属性），改用 DOM 取 ECharts 主画布
        var cv=document.querySelector('#chart canvas');
        var url = cv ? cv.toDataURL('image/png') : '';
        document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({url:url})+'</pre>');
      }catch(e){ document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify({err:e.message})+'</pre>'); }
    }, 3500);});</script>"""
    html = html.replace("</body>", inject + "\n</body>")
    p = os.path.join("atlas_test", "shot_%s.html" % kind)
    open(p, "w", encoding="utf-8").write(html)
    return p

def run_shot(kind, window, out_png):
    p = build_shot_html(kind)
    r = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                        "--window-size=" + window, "--virtual-time-budget=40000",
                        "--dump-dom", "file://" + os.path.abspath(p)],
                       capture_output=True, timeout=90)
    dom = r.stdout.decode("utf-8", "replace")
    pres = [m for m in re.findall(r'<pre id="ck">R(.*?)</pre>', dom, re.S) if not m.startswith("'+")]
    raw = pres[-1] if pres else "{}"
    try:
        o = json.loads(raw)
    except Exception as e:
        print("  截图解析失败:", raw[:200], e); return None
    if "err" in o:
        print("  ✗ 截图采集异常:", o["err"]); return None
    if not o.get("url"):
        print("  ✗ chart.getDataURL 为空（地图未渲染？）"); return None
    b64 = o["url"].split(",", 1)[1]
    with open(out_png, "wb") as f:
        f.write(base64.b64decode(b64))
    return out_png

# ---------- Pillow 分析 ----------
def nonblank_ratio(png):
    im = Image.open(png).convert("RGB")
    colors = im.getcolors(maxcolors=10**7)
    if not colors:
        return 0.0
    total = sum(c for c, _ in colors)
    dom = max(colors)[0]
    return 1.0 - dom / total

def mse_vs_baseline(png, base_png):
    a = Image.open(png).convert("RGB").resize((320, 200))
    b = Image.open(base_png).convert("RGB").resize((320, 200))
    if a.size != b.size:
        return None
    ba, bb = a.tobytes(), b.tobytes()
    if len(ba) != len(bb):
        return None
    s = sum((ba[i]-bb[i])**2 for i in range(len(ba)))
    return s / (len(ba) * 255 * 255)

# ================= 执行 =================
fails, warns = [], []
print("  ── 视口/DOM 断言（硬门禁） ──")
# 移动端走 CDP 真·设备模拟（use_cdp=True）；无 websocket 依赖时降级 --window-size 并跳过移动端溢出断言
cities = (("桌面 1280x800", "1280,800", False),
          ("移动 375x667", "375,667", True))
for label, win, mobile in cities:
    d = run_dom(win, use_cdp=mobile)
    if "fatal" in d:
        print("  ✗ %s 致命: %s" % (label, d["fatal"])); fails.append(label + " 致命"); continue
    print("  [%s] canvas=%s legend=%s overflow=%s panelCN=%s (scrollW=%s/innerW=%s)" % (
        label, d.get("canvas"), d.get("legend"), d.get("overflow"), d.get("panelCN"), d.get("scrollW"), d.get("innerW")))
    if not d.get("canvas"): fails.append(label + " canvas 未绘制")
    if not d.get("legend"): fails.append(label + " 图例缺失")
    if not d.get("panelCN"): fails.append(label + " 下钻后面板无'中国'")
    if not d.get("overflow"):
        if mobile:
            if HAVE_WS:
                # CDP 真·设备模拟下仍溢出 = 真实响应式缺陷（硬门禁）
                fails.append("%s 横向溢出 scrollW=%s > innerW=%s" % (label, d.get("scrollW"), d.get("innerW")))
            else:
                # 无 websocket：--window-size 在 headless 下不能真设移动视口（停 500px 默认），
                # 该断言不可靠，降级为跳过并告警，避免 CI 误报
                warns.append("%s 横向溢出断言已跳过（未装 websocket-client，无法真·设备模拟；请用真机/装依赖复测）" % label)
        else:
            fails.append(label + " 横向溢出(scrollW>innerW)")

print("  ── 真实地图截图 + 像素分析 ──")
shots = [("world_desktop", "world", "1280,800"), ("world_mobile", "world", "375,667"), ("cn_drilled_desktop", "cn_drilled", "1280,800")]
for name, kind, win in shots:
    out = os.path.join(SHOTS, name + ".png")
    got = run_shot(kind, win, out)
    if not got:
        fails.append(name + " 截图失败"); continue
    ratio = nonblank_ratio(out)
    print("  %s: %s 非背景像素占比=%.1f%%" % (name, out, ratio * 100))
    if ratio < 0.03:
        fails.append(name + " 地图疑似空白(占比<3%)")
    base = os.path.join(BASE, name + ".png")
    if os.path.exists(base):
        m = mse_vs_baseline(out, base)
        if m is None:
            warns.append(name + " 基线尺寸不一致")
        elif m > 0.06:
            warns.append(name + " 与基线 MSE=%.3f 超阈(>0.06)" % m)
    else:
        shutil.copy(out, base)
        warns.append(name + " 首次运行已建立基线(后续比对)")

print("  ── 结果 ──")
for w in warns:
    print("  ⚠ 软告警(不阻断):", w)
if fails:
    print("  ✗ 视觉/响应式回归硬门禁未过 %d 项:" % len(fails))
    for f in fails:
        print("    -", f)
    sys.exit(1)
print("  ✓ L3j 通过（地图非空白 + 响应式无溢出 + 下钻面板正常；基线已比对/建立）")
