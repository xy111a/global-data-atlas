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

def run_iframe_roundtrip(parent_url, wait_ms=45000):
    """用 playwright 真实等待跑 iframe+postMessage 往返；无 playwright 时回退 headless virtual-time。"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return out_of(dump(parent_url, 60))
    try:
        import os as _os
        _env = dict(_os.environ)
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
            _env.pop(k, None)
        _os.environ.clear(); _os.environ.update(_env)
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page()
            pg.goto(parent_url)
            try:
                pg.wait_for_function("window.__done === true", timeout=wait_ms)
            except Exception:
                pass
            data = pg.evaluate("window.__msgs || []")
            b.close()
        return {"n": len(data), "msgs": data}
    except Exception as e:
        # playwright 已安装但浏览器未下载时，不要让整步失败：回退 headless dump
        try:
            r = out_of(dump(parent_url, 60))
            if r is not None:
                print(f"  ⚠ playwright 不可用（{str(e).splitlines()[0][:80]}），已回退 headless")
                return r
        except Exception:
            pass
        return {"err": f"playwright-fail:{e}"}

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

p_path = p_allow = None
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
var msgs=[]; window.__msgs=msgs; window.__done=false;   // 供 playwright 直接读取（真实等待方案）
window.addEventListener('message', function(e){ msgs.push(e.data); });
function __emit(o){
  var b64=btoa(unescape(encodeURIComponent(JSON.stringify(o))));
  var el=document.createElement('pre'); el.id='ck'; el.textContent='B'+b64;
  document.body.appendChild(el);
}
function send(o){ document.getElementById('fr').contentWindow.postMessage(o,'*'); }
/* 事件驱动 + 明确起点：iframe load 后主动 ping，不依赖子页自动上报
   （子页自动上报在 restoreState().then() 里，virtual-time 下可能晚于父页兜底，曾导致 n=0 假失败） */
var stage=0, finished=false;
function finish(){ if(finished) return; finished=true; window.__done=true;
  __emit({n:msgs.length, msgs:msgs.map(function(m){
    return {type:m&&m.type, cmd:m&&m.cmd, level:m&&m.level, metric:m&&m.metric,
            year:m&&m.year, embed:m&&m.embed, kind:m&&m.sel?m.sel.kind:null};
  })});
}
function next(){
  if(finished) return;
  try{
    if(stage===0){ stage=1; send({type:'atlas:cmd',cmd:'ping'}); return; }
    if(stage===1){ stage=2; send({type:'atlas:cmd',cmd:'setYear',year:2020}); return; }
    if(stage===2){ stage=3; send({type:'atlas:cmd',cmd:'setMetric',metric:'pop'}); return; }
    setTimeout(finish, 700);
  }catch(e){ finish(); }
}
window.addEventListener('message', function(e){ msgs.push(e.data); setTimeout(next, 300); });
document.getElementById('fr').addEventListener('load', function(){ setTimeout(next, 1500); });
setTimeout(finish, 30000);   // 兜底：即使消息不来也能产出诊断结果
</script></body></html>"""
p_parent = os.path.join(ROOT, "embed_parent_tmp.html")
open(p_parent, "w", encoding="utf-8").write(parent_html)

# ── 临时 HTTP 服务 ───────────────────────────────────────
def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

PORT = free_port()
class _AtlasHandler(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        # 无扩展名的 /embed 必须按 HTML 处理（对齐 Cloudflare Pages：/embed.html 重定向后落在 /embed）
        base = os.path.basename(str(path).rstrip("/"))
        if base == "embed":
            return "text/html"
        return super().guess_type(path)
    def log_message(self, *a, **k):
        pass
Handler = functools.partial(_AtlasHandler, directory=ROOT)
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
    #    ⚠️ 改用 playwright 真实等待：此场景在 --virtual-time-budget 下不稳定
    #    （iframe 内需加载 ~1.6MB vendor，虚拟时钟常在资源到达前耗尽，导致 n=0 假失败）。
    #    playwright 用真实时间等待，稳定且更快；不可用时回退到原来的 headless 方案。
    oB = run_iframe_roundtrip(f"{BASE_URL}/embed_parent_tmp.html")
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

    # ── 场景 D：/embed.html 路径入口 + 父页来源白名单（2026-10-12 审计修复项） ──
    # D1 路径为 /embed.html 且不带 ?embed=1 时自动进入嵌入模式（跨域嵌入唯一入口）
    # D2 来源校验：同源放行；未授权跨域拒绝；?allowOrigin= 授权后放行
    ORIGIN_INJECT = """<script>(function(){
try{
  var out={embed:!!window.ATLAS_EMBED,
           htmlClass:document.documentElement.classList.contains('embed'),
           selfAllowed: window.atlasOriginAllowed ? window.atlasOriginAllowed(location.origin) : null,
           evilAllowed: window.atlasOriginAllowed ? window.atlasOriginAllowed('https://evil.example') : null,
           allowList: window.ATLAS_ALLOWED_ORIGINS || []};
  __emit(out);
}catch(e){ __emit({err:e.message}) }
})();</script>"""

    p_path = os.path.join(ROOT, "embed.html")     # 文件名必须精确为 embed.html（路径判定）
    p_allow = os.path.join(ROOT, "embed_direct_tmp.html")
    open(p_path, "w", encoding="utf-8").write(
        without_sw(ATLAS).replace("</body>", EMIT_SCRIPT + ORIGIN_INJECT + "\n</body>"))
    open(p_allow, "w", encoding="utf-8").write(
        without_sw(ATLAS).replace("</body>", EMIT_SCRIPT + ORIGIN_INJECT + "\n</body>"))

    oD1 = out_of(dump(f"{BASE_URL}/embed.html", 14))
    if not oD1 or oD1.get("err"):
        check("D 脚本执行", False, f"({oD1})")
    else:
        check("D1 /embed.html 路径自动进入嵌入模式（无需 ?embed=1）",
              oD1.get("embed") is True, f"(embed={oD1.get('embed')})")
        check("D1 /embed.html 带 embed 样式标记",
              oD1.get("htmlClass") is True, f"(htmlClass={oD1.get('htmlClass')})")
        check("D2 同源父页放行", oD1.get("selfAllowed") is True, f"({oD1.get('selfAllowed')})")
        check("D2 未授权跨域来源被拒（默认拒绝）",
              oD1.get("evilAllowed") is False, f"({oD1.get('evilAllowed')})")

    # D4: 无 .html 后缀的 /embed（Cloudflare Pages 会把 /embed.html 308 重定向到 /embed，
    #     实际 pathname 是 "/embed"，路径判定必须同时覆盖，否则线上嵌入态失效）
    p_bare = os.path.join(ROOT, "embed")
    open(p_bare, "w", encoding="utf-8").write(
        without_sw(ATLAS).replace("</body>", EMIT_SCRIPT + ORIGIN_INJECT + "\n</body>"))
    oD4 = out_of(dump(f"{BASE_URL}/embed", 14))
    if not oD4 or oD4.get("err"):
        check("D4 脚本执行", False, f"({oD4})")
    else:
        check("D4 /embed（无后缀，重定向后的真实路径）也进入嵌入模式",
              oD4.get("embed") is True, f"(embed={oD4.get('embed')})")
    try: os.remove(p_bare)
    except Exception: pass

    oD3 = out_of(dump(f"{BASE_URL}/embed_direct_tmp.html?embed=1&allowOrigin=https://evil.example", 14))
    if not oD3 or oD3.get("err"):
        check("D3 脚本执行", False, f"({oD3})")
    else:
        check("D3 ?allowOrigin= 授权后该来源放行",
              oD3.get("evilAllowed") is True, f"({oD3.get('evilAllowed')})")
        check("D3 白名单解析正确",
              "https://evil.example" in (oD3.get("allowList") or []), f"({oD3.get('allowList')})")


finally:
    httpd.shutdown(); httpd.server_close()
    for f in (p_embed, p_plain, p_parent):
        try: os.remove(f)
        except Exception: pass
    for f in ("embed.html", "embed_direct_tmp.html"):
        try: os.remove(os.path.join(ROOT, f))
        except Exception: pass

print(f"\n嵌入模式(T11)回归: {ok}/{total} 通过")
exit(0 if ok == total else 1)
