#!/usr/bin/env python3
"""T11 回归：嵌入模式 ?embed=1 + postMessage 桥接。
A) 直接以 ?embed=1 打开：html 带 embed 标记，导航/页脚隐藏（iframe 外壳精简）
B) 由父页 iframe 载入：子页上报 atlas:state；父页指令 ping/setYear/setMetric 生效并回传状态
C) 不带 embed 参数时：不处嵌入态（不误隐藏导航，不对外发消息）

说明：iframe+postMessage 在 file:// 下受同源策略限制，故临时起本地 HTTP 服务测试，用后清理。
"""
import subprocess, os, re, json, base64, time, socket, threading, http.server, functools

CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
              "/usr/bin/chromium", "/usr/bin/chromium-browser"):
        if os.path.exists(p):
            CHROME = p; break
assert CHROME and os.path.exists(CHROME), "未找到 Chrome/Chromium，请设 CHROME_BIN"
os.makedirs("atlas_test", exist_ok=True)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ATLAS = open(os.path.join(ROOT, "global-data-atlas.html"), encoding="utf-8").read()

def dump(url, wait):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait + 30)
    return r.stdout.decode("utf-8", "replace")

def out_of(dom):
    pres = re.findall(r'<pre id="ck">B(.*?)</pre>', dom, re.S)
    if not pres:
        return None
    try:
        return json.loads(base64.b64decode(pres[-1].strip()).decode("utf-8"))
    except Exception as e:
        return {"err": f"decode-fail:{e}"}

ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

EMIT = """
function __emit(o){
  var b64=btoa(unescape(encodeURIComponent(JSON.stringify(o))));
  var el=document.createElement('pre'); el.id='ck'; el.textContent='B'+b64;
  document.body.appendChild(el);
}
"""

# ── 临时页面 ─────────────────────────────────────────────
# A/C：直接打开（注入断言脚本）；A 带 ?embed=1，C 不带
# 同步执行：embed 标记由 <head> 内脚本即时打到 <html>，header/footer 也已解析，
# 无需等 load（HTTP 下 vendor ~1MB，load 触发很晚，virtual-time 预算内等不到）。
check_inject = """<script>(function(){
try{
  var hd=document.querySelector('header'), ft=document.querySelector('footer');
  __emit({embed:!!window.ATLAS_EMBED,
          htmlClass:document.documentElement.classList.contains('embed'),
          headerHidden: hd? getComputedStyle(hd).display==='none' : null,
          footerHidden: ft? getComputedStyle(ft).display==='none' : null});
}catch(e){ __emit({err:e.message}) }
})();</script>"""

def without_sw(html):
    """移除 SW 注册：避免这台 HTTP 服务上的 root-scope Service Worker 接管临时页，
    干扰 A/C 两个纯 UI 断言场景（B 的消息桥接不受影响）。"""
    # 实际写法：if ('serviceWorker' in navigator) { ... }（含空格），故按整行脚本块匹配
    return re.sub(
        r"<script>\s*if \('serviceWorker' in navigator\)[\s\S]*?</script>\s*", "", html)

p_embed = os.path.join(ROOT, "embed_direct_tmp.html")
p_plain = os.path.join(ROOT, "embed_plain_tmp.html")
# ⚠️ EMIT 必须包在 <script> 里，否则只是被当作正文文本渲染，__emit 永远不会被定义
EMIT_SCRIPT = "<script>" + EMIT + "</" + "script>\n"
open(p_embed, "w", encoding="utf-8").write(
    without_sw(ATLAS).replace("</body>", EMIT_SCRIPT + check_inject + "\n</body>"))
open(p_plain, "w", encoding="utf-8").write(
    without_sw(ATLAS).replace("</body>", EMIT_SCRIPT + check_inject + "\n</body>"))

parent_html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>embed parent</title></head><body>
<iframe id="fr" src="/embed_direct_tmp.html?embed=1" style="width:900px;height:600px;border:0"></iframe>
<script>
var msgs=[];
window.addEventListener('message', function(e){ msgs.push(e.data); });
function __emit(o){
  var b64=btoa(unescape(encodeURIComponent(JSON.stringify(o))));
  var el=document.createElement('pre'); el.id='ck'; el.textContent='B'+b64;
  document.body.appendChild(el);
}
function send(o){ document.getElementById('fr').contentWindow.postMessage(o,'*'); }
/* 事件驱动：收到一条就推进下一步（固定 sleep 在 virtual-time 下不稳定，易漏消息） */
var stage=0, done=false;
function finish(){ if(done) return; done=true;
  __emit({n:msgs.length, msgs:msgs.map(function(m){
    return {type:m&&m.type, cmd:m&&m.cmd, level:m&&m.level, metric:m&&m.metric,
            year:m&&m.year, embed:m&&m.embed, kind:m&&m.sel?m.sel.kind:null};
  })});
}
function step(){
  try{
    if(stage===0) send({type:'atlas:cmd',cmd:'ping'});
    else if(stage===1) send({type:'atlas:cmd',cmd:'setYear',year:2020});
    else if(stage===2) send({type:'atlas:cmd',cmd:'setMetric',metric:'pop'});
    else { setTimeout(finish, 600); return; }
    stage++;
  }catch(e){ finish(); }
}
window.addEventListener('message', function(e){ msgs.push(e.data); step(); });
setTimeout(finish, 20000);   // 兜底：即使消息不来也能产出诊断结果
</script></body></html>"""
p_parent = os.path.join(ROOT, "embed_parent_tmp.html")
open(p_parent, "w", encoding="utf-8").write(parent_html)

# ── 临时 HTTP 服务 ───────────────────────────────────────
def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

PORT = free_port()
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
Handler.log_message = lambda *a, **k: None
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()
BASE_URL = f"http://127.0.0.1:{PORT}"
try:
    time.sleep(0.6)
    # A) ?embed=1 直接打开
    oA = out_of(dump(f"{BASE_URL}/embed_direct_tmp.html?embed=1", 20))
    if not oA or "err" in oA:
        check("A 脚本执行", False, f"({oA})")
    else:
        check("A embed=1 → ATLAS_EMBED 生效", oA.get("embed") is True, f"({oA.get('embed')})")
        check("A html 带 embed 标记", oA.get("htmlClass") is True, f"({oA.get('htmlClass')})")
        check("A 顶栏导航隐藏", oA.get("headerHidden") is True, f"({oA.get('headerHidden')})")
        check("A 页脚隐藏", oA.get("footerHidden") is True, f"({oA.get('footerHidden')})")

    # C) 不带 embed → 保持常规站点形态
    oC = out_of(dump(f"{BASE_URL}/embed_plain_tmp.html", 20))
    if not oC or "err" in oC:
        check("C 脚本执行", False, f"({oC})")
    else:
        check("C 无 embed 参数 → 非嵌入态", oC.get("embed") is False, f"({oC.get('embed')})")
        check("C 顶栏保持可见（不误精简）", oC.get("headerHidden") is False, f"({oC.get('headerHidden')})")

    # B) iframe + postMessage 往返
    oB = out_of(dump(f"{BASE_URL}/embed_parent_tmp.html", 40))
    if not oB or "err" in oB:
        check("B 父页脚本执行", False, f"({oB})")
    else:
        msgs = oB.get("msgs") or []
        check("B 子页已上报状态( ≥2 条含自动就绪+ping 应答)",
              oB.get("n", 0) >= 2, f"(n={oB.get('n')})")
        check("B 消息类型为 atlas:state",
              bool(msgs) and all(m.get("type") == "atlas:state" for m in msgs),
              f"(types={[m.get('type') for m in msgs]})")

        def last_with(**kw):
            cand = [m for m in msgs
                    if all((m.get(k) == v) for k, v in kw.items())]
            return cand[-1] if cand else {}
        check("B 初始/ping 回传 embed 标记",
              any(m.get("embed") is True for m in msgs),
              f"(embed={[m.get('embed') for m in msgs][:3]})")
        check("B setYear 指令生效（回传 year=2020）",
              bool(last_with(year="2020")), f"(years={[m.get('year') for m in msgs]})")
        check("B setMetric 指令生效（回传 metric=pop）",
              bool(last_with(metric="pop")), f"(metrics={[m.get('metric') for m in msgs]})")
        check("B 状态含层级信息", any(m.get("level") for m in msgs),
              f"(levels={[m.get('level') for m in msgs][:3]})")
finally:
    httpd.shutdown(); httpd.server_close()
    for f in (p_embed, p_plain, p_parent):
        try: os.remove(f)
        except Exception: pass

print(f"\n嵌入模式(T11)回归: {ok}/{total} 通过")
exit(0 if ok == total else 1)
