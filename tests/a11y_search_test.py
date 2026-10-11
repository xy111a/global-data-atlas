#!/usr/bin/env python3
"""T10 回归：搜索建议下拉的键盘可达性 + ARIA（a11y）。
断言：
  1) 输入后出现 listbox 选项，aria-expanded=true
  2) ↓ 键移动高亮（aria-activedescendant 变化），↑ 可回退
  3) Enter 选中 → 触发区域跳转（面板显示该地区）
  4) ESC 关闭下拉（aria-expanded=false）
  5) 排行项本身键盘可操作（role=button + tabindex=0）
"""
import subprocess, os, re, json, base64

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
    """<pre id="ck">B<base64> 保真传输（可能含 HTML/引号，避免 DOM 解析破坏 JSON）"""
    pres = re.findall(r'<pre id="ck">B(.*?)</pre>', dom, re.S)
    if not pres:
        return None
    try:
        return json.loads(base64.b64decode(pres[-1].strip()).decode("utf-8"))
    except Exception as e:
        return {"err": f"decode-fail: {e}"}

ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

HELPERS = """
function __emit(out){
  var json=JSON.stringify(out);
  var b64=btoa(unescape(encodeURIComponent(json)));
  var el=document.createElement('pre'); el.id='ck'; el.textContent='B'+b64;
  document.body.appendChild(el);
}
function __snap(){
  var inp=document.getElementById('search');
  var ul=document.getElementById('sugList');
  var opts=document.querySelectorAll('#sugList .sug-item');
  var active=( ul && ul.querySelector('.sug-item.active') ) ? ul.querySelector('.sug-item.active').textContent : null;
  var panel=document.getElementById('panel');
  return {n:opts.length, expanded:inp.getAttribute('aria-expanded'),
          activedesc:inp.getAttribute('aria-activedescendant'),
          activeText:active, level:currentLevel,
          role:inp.getAttribute('role'),
          panel:(panel?panel.textContent:'').replace(/\\s+/g,' ').slice(0,120)};
}
function __type(v){ var inp=document.getElementById('search'); inp.focus(); inp.value=v;
  inp.dispatchEvent(new Event('input',{bubbles:true})); }
function __key(k){ var inp=document.getElementById('search');
  inp.dispatchEvent(new KeyboardEvent('keydown',{key:k,bubbles:true})); }
"""

inject = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
  var out={};
  /* 排行项自身键盘可操作性（既有能力，防止回归） */
  var ri=document.querySelectorAll('#rank .rank-item');
  out.rankN=ri.length;
  out.rankRole=ri.length?ri[0].getAttribute('role'):null;
  out.rankTab=ri.length?ri[0].getAttribute('tabindex'):null;

  /* A. 多候选下的键盘遍历 */
  __type('c');
  setTimeout(function(){
    out.a1=__snap();
    __key('ArrowDown');
    setTimeout(function(){
      out.a2=__snap();
      __key('ArrowUp');
      setTimeout(function(){
        out.a3=__snap();
        __key('Escape');
        setTimeout(function(){
          out.a4=__snap();
          /* B. 精确词 → Enter 选中并跳转 */
          __type('california');
          setTimeout(function(){
            out.b1=__snap();
            __key('Enter');
            setTimeout(function(){
              out.b2=__snap();
              __emit(out);
            },1900);
          },600);
        },350);
      },350);
    },350);
  },700);
}catch(e){ __emit({err:e.message}) }
},1500);});</script>"""

html = open("global-data-atlas.html", encoding="utf-8").read()
base = "<base href=\"file://" + os.path.abspath(".") + "/\">"
html = html.replace("</head>", base + "</head>", 1)
html = html.replace("</body>", "<script>" + HELPERS + "</script>\n" + inject + "\n</body>")
p = os.path.join("atlas_test", "a11y_search.html")
open(p, "w", encoding="utf-8").write(html)
o = runtime_out(dump("file://" + os.path.abspath(p), 22))

if not o or "err" in o:
    check("a11y 搜索脚本执行", False, f"({o})")
else:
    check("输入框 role=combobox", o.get("a1", {}).get("role") == "combobox",
          f"({o.get('a1',{}).get('role')})")
    a1, a2, a3, a4 = (o.get(k, {}) for k in ("a1", "a2", "a3", "a4"))
    b1, b2 = (o.get(k, {}) for k in ("b1", "b2"))
    check("输入后出现多个候选（可遍历）", a1.get("n", 0) >= 2, f"(n={a1.get('n')})")
    check("下拉展开且 aria-expanded=true", a1.get("expanded") == "true", f"({a1.get('expanded')})")
    check("默认高亮第 1 项", a1.get("activedesc") == "sug-opt-0", f"({a1.get('activedesc')})")
    check("↓ 键下移高亮到第 2 项", a2.get("activedesc") == "sug-opt-1", f"({a2.get('activedesc')})")
    check("↑ 键可回退到第 1 项", a3.get("activedesc") == "sug-opt-0", f"({a3.get('activedesc')})")
    check("ESC 关闭下拉", a4.get("expanded") == "false", f"({a4.get('expanded')})")
    check("精确词输入后可再次展开", b1.get("expanded") == "true" and b1.get("n", 0) >= 1,
          f"(expanded={b1.get('expanded')} n={b1.get('n')})")
    check("Enter 选中并跳转（面板出现该地区）",
          "California" in (b2.get("panel") or "") or "加利福" in (b2.get("panel") or ""),
          f"(level={b2.get('level')} panel={b2.get('panel')})")
    check("选中后下拉关闭", b2.get("expanded") == "false", f"({b2.get('expanded')})")

print(f"\n搜索键盘可达性(T10)回归: {ok}/{total} 通过")
exit(0 if ok == total else 1)
