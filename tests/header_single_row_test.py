#!/usr/bin/env python3
"""顶栏单行化布局探针：在多个视口宽度下测量 header 是否保持单行、是否横向溢出、
下拉（更多指标 / 工具）是否正确渲染与展开、品牌区是否存在。"""
import subprocess, os, re, json, base64, sys

CHROME = os.environ.get("CHROME_BIN")
if not CHROME:
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/usr/bin/google-chrome", "/usr/bin/chromium"):
        if os.path.exists(p):
            CHROME = p; break
assert CHROME, "未找到 Chrome"

HELPERS = """
function __emit(out){
  var json=JSON.stringify(out);
  var b64=btoa(unescape(encodeURIComponent(json)));
  var el=document.createElement('pre'); el.id='ck'; el.textContent='B'+b64;
  document.body.appendChild(el);
}
"""

PROBE = """<script>window.addEventListener('load',function(){setTimeout(function(){
try{
  var out={};
  var h=document.querySelector('header');
  var r=h.getBoundingClientRect();
  out.headerH=Math.round(r.height);
  function box(sel){ var e=document.querySelector(sel); if(!e) return null;
    var b=e.getBoundingClientRect();
    return {top:Math.round(b.top),cy:Math.round(b.top+b.height/2),h:Math.round(b.height),w:Math.round(b.width),right:Math.round(b.right)}; }
  out.brand=box('.brand');
  out.metricZone=box('.metric-zone');
  out.tbActions=box('.tb-actions');
  out.tbMain=box('.tb-main');
  out.crumb=box('#crumb');
  out.moreBtn=box('#metricMoreBtn');
  out.toolBtn=box('#toolMoreBtn');
  out.backBtn=box('#backBtn');
  out.cmpBtn=box('#cmpBtn');
  out.viewport={w:innerWidth,h:innerHeight};
  out.overflowX=document.documentElement.scrollWidth>innerWidth;
  out.bodyOverflowX=document.body.scrollWidth>innerWidth;
  out.seg=document.querySelectorAll('#metricSeg button').length;
  out.drop=document.querySelectorAll('#metricMoreDropdown button').length;
  out.tool=document.querySelectorAll('#toolMoreDropdown button').length;
  out.siteBrand=!!document.querySelector('.site-brand');
  out.title=document.title;
  out.headerBg=getComputedStyle(h).backgroundColor;
  var mb=document.getElementById('metricMoreBtn');
  mb.click();
  setTimeout(function(){
    var dd=document.getElementById('metricMoreDropdown');
    out.dropOpen=getComputedStyle(dd).display;
    out.dropExpanded=mb.getAttribute('aria-expanded');
    out.tradeDisabled=(function(){ var t=dd.querySelector('button[data-m="trade"]'); return t? t.disabled : null; })();
    out.dropBtnCount=dd.querySelectorAll('button').length;
    var tbtn=document.getElementById('toolMoreBtn');
    tbtn.click();
    setTimeout(function(){
      var td=document.getElementById('toolMoreDropdown');
      out.toolOpen=getComputedStyle(td).display;
      out.toolBtnCount=td.querySelectorAll('button').length;
      out.toolIds=Array.prototype.map.call(td.querySelectorAll('button'),function(b){return b.id;}).join(',');
      __emit(out);
    },250);
  },250);
}catch(e){ __emit({err:String(e)}); }
}, 2200); });
</script>"""

def dump(url, wait, size):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--window-size={size}", f"--virtual-time-budget={wait*1000}",
           "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait + 40)
    return r.stdout.decode("utf-8", "replace")

def runtime_out(dom):
    pres = re.findall(r'<pre id="ck">B(.*?)</pre>', dom, re.S)
    if not pres: return None
    try: return json.loads(base64.b64decode(pres[-1].strip()).decode("utf-8"))
    except Exception as e: return {"err": f"decode-fail: {e}"}

src = open("dist/index.html", encoding="utf-8").read()
base = "<base href=\"file://" + os.path.abspath(".") + "/\">"
html = src.replace("</head>", base + "</head>", 1)
html = html.replace("</body>", "<script>" + HELPERS + "</script>\n" + PROBE + "\n</body>")
p = "atlas_test/header_probe.html"
os.makedirs("atlas_test", exist_ok=True)
open(p, "w", encoding="utf-8").write(html)

SIZES = ["1920,1080", "1600,900", "1440,900", "1366,768", "1280,800", "1024,768", "768,1024", "500,900"]
rows = []
for size in SIZES:
    o = runtime_out(dump("file://" + os.path.abspath(p), 8, size))
    if not o or "err" in o:
        print(f"[{size}] 探针失败: {o}"); continue
    vw = o["viewport"]["w"]
    b, mz, ta = o.get("brand"), o.get("metricZone"), o.get("tbActions")
    cys = [x["cy"] for x in (b, mz, ta) if x]
    same_row = (max(cys) - min(cys) <= 6) if cys else False
    print(f"[{vw:>4}px] header={o['headerH']:>3}px  同一行={same_row}  横向溢出={o['overflowX']}  "
          f"seg={o['seg']} 下拉={o['drop']} 工具={o['tool']}  品牌区={o['siteBrand']}  "
          f"更多指标展开={o.get('dropOpen')} 工具展开={o.get('toolOpen')}")
    print(f"        brand cy={b['cy'] if b else '-'} mz cy={mz['cy'] if mz else '-'} ta cy={ta['cy'] if ta else '-'} "
          f"| tb-main h={o['tbMain']['h'] if o.get('tbMain') else '-'} "
          f"| crumb cy={o['crumb']['cy'] if o.get('crumb') else '-'} moreBtn cy={o['moreBtn']['cy'] if o.get('moreBtn') else '-'} "
          f"toolBtn cy={o['toolBtn']['cy'] if o.get('toolBtn') else '-'} backBtn cy={o['backBtn']['cy'] if o.get('backBtn') else '-'}")
    rows.append((vw, o, same_row))

print("\n=== 判定 ===")
bad = 0
for vw, o, same_row in rows:
    if vw >= 1280 and not same_row:
        print(f"❌ {vw}px 顶栏未保持单行"); bad += 1
    if o["overflowX"]:
        print(f"❌ {vw}px 横向溢出"); bad += 1
    if not o["siteBrand"]:
        print(f"❌ {vw}px 品牌区缺失"); bad += 1
    if o["seg"] != 5 or o["drop"] != 10:
        print(f"❌ {vw}px 指标分区异常 (seg={o['seg']} drop={o['drop']})"); bad += 1
    if o["tool"] != 6:
        print(f"❌ {vw}px 工具下拉项异常 ({o['tool']})"); bad += 1
    if o.get("dropOpen") != "block":
        print(f"❌ {vw}px 更多指标下拉未展开 ({o.get('dropOpen')})"); bad += 1
    if o.get("toolOpen") != "block":
        print(f"❌ {vw}px 工具下拉未展开 ({o.get('toolOpen')})"); bad += 1
print("全部通过" if bad == 0 else f"{bad} 项问题")
sys.exit(0 if bad == 0 else 1)
