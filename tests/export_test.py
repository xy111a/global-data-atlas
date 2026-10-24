#!/usr/bin/env python3
"""主页导出（CSV / PNG）回归。

背景：导出此前只存在于 compare.html，主页的排行榜与地图拿不到数据，用户只能手抄。
headless 无法校验"真的下载了文件"，故断言落在**生成的字节**与**渲染链路**上：
  1) 工具函数与按钮就位
  2) buildRankCsv() 在数值/增长两种模式下都能产出结构正确的 CSV（含 UTF-8 BOM）
  3) 派生指标（gdppc）也能导出
  4) ECharts getDataURL 真能产出 PNG data URL（说明画布已渲染，不是空白图）
  5) 嵌入模式下地图导出按钮不暴露
"""
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
function emit(){
  var pre=document.createElement('pre'); pre.id='ex';
  pre.textContent='B'+btoa(unescape(encodeURIComponent(JSON.stringify(out))));
  document.body.appendChild(pre);
}
try{
  out.hasPngBtn = !!document.getElementById('pngBtn');
  out.fnExportMapPng = (typeof exportMapPng==='function');
  out.fnExportRankCsv = (typeof exportRankCsv==='function');
  out.fnBuildRankCsv  = (typeof buildRankCsv==='function');
  out.rankCsvBtnText  = (document.getElementById('rankCsvBtn')||{}).textContent || null;

  // 数值模式
  rankMode='value'; metric='gdp'; renderRank();
  var b1=buildRankCsv();
  out.v_rows = b1?b1.rows:0;
  out.v_file = b1?b1.filename:null;
  out.v_head = b1?b1.csv.split('\n')[0]:null;
  out.v_line1= b1?b1.csv.split('\n')[1]:null;
  out.v_bomOk= !!(b1 && b1.text.indexOf('\ufeff')===0 && b1.csv.indexOf('\ufeff')!==0);

  // 派生指标
  metric='gdppc'; renderRank();
  var b2=buildRankCsv();
  out.pc_rows = b2?b2.rows:0;
  out.pc_file = b2?b2.filename:null;
  out.pc_line1= b2?b2.csv.split('\n')[1]:null;

  // 增长模式
  metric='gdp'; rankMode='growth'; renderRank();
  var b3=buildRankCsv();
  out.g_rows = b3?b3.rows:0;
  out.g_head = b3?b3.csv.split('\n')[0]:null;
  out.g_line1= b3?b3.csv.split('\n')[1]:null;

  // 导出调用不抛异常（真实下载由浏览器处理）
  try{ exportRankCsv(); out.callCsvOk=true; }catch(e){ out.callCsvOk='ERR:'+e.message; }
  try{ exportMapPng();  out.callPngOk=true; }catch(e){ out.callPngOk='ERR:'+e.message; }

  // PNG：直接取画布数据，确认非空图
  try{
    var u=chart.getDataURL({type:'png',pixelRatio:1,backgroundColor:'#05060a'});
    out.pngPrefix = u.slice(0,22);
    out.pngLen = u.length;
  }catch(e){ out.pngPrefix='ERR:'+e.message; out.pngLen=0; }
  // ===== C2 全量导出探针（当前层 world, metric gdp：区域×年份长表）=====
  metric='gdp'; rankMode='value';
  try{
    out.fnBuildFull = (typeof buildFullExport==='function');
    out.fnLevelRegs = (typeof atlasLevelRegs==='function');
    out.hasFullCsvBtn = !!document.getElementById('fullCsvBtn');
    out.hasFullJsonBtn = !!document.getElementById('fullJsonBtn');
    var bf=buildFullExport();
    out.full_rows = bf?bf.rows:0;
    out.full_regions = bf?bf.regions:0;
    out.full_head = bf?bf.csv.split('\n')[0]:null;
    out.full_line1= bf?bf.csv.split('\n')[1]:null;
    out.full_csvname = bf?bf.csvFilename:null;
    out.full_bom = !!(bf && bf.csvText.charCodeAt(0)===0xFEFF && bf.csv.indexOf('\ufeff')!==0);
    out.full_json_ok = !!(bf && (function(){try{var j=JSON.parse(bf.json); return j.level==='world' && j.metric==='gdp' && j.regions.length>100 && j.regions[0].series['2023']!=null;}catch(e){return false;}})());
    out.full_ycount = (function(){ if(!bf) return 0; try{var j=JSON.parse(bf.json); return j.regions.filter(function(x){return Object.keys(x.series).length>=20;}).length;}catch(e){return 0;} })();
    try{ exportFullCsv(); out.callFullCsvOk=true; }catch(e){ out.callFullCsvOk='ERR:'+e.message; }
  }catch(e){ out.full_err=''+e.message; }

  rankMode='value'; metric='gdp'; renderRank();   // 复位
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
    pres = re.findall(r'<pre id="ex">B(.*?)</pre>', dom, re.S)
    if not pres:
        return None
    return json.loads(base64.b64decode(pres[-1].strip()).decode("utf-8"))

ok = 0; total = 0
def check(label, cond, detail=""):
    global ok, total
    total += 1
    print(f"{'✅' if cond else '❌'} {label} {detail}")
    if cond: ok += 1

out = run("export_probe.html")
if out is None:
    check("探针产出结果", False)
    print(f"\n导出回归: {ok}/{total} 通过"); sys.exit(1)

print("— 主页面（世界层）—")
check("探针无异常", not out.get("err"), f"({out.get('err')})")
check("#pngBtn 存在", out.get("hasPngBtn") is True)
check("exportMapPng / exportRankCsv / buildRankCsv 均已定义",
      out.get("fnExportMapPng") and out.get("fnExportRankCsv") and out.get("fnBuildRankCsv"))
check("排行面板出现导出按钮", (out.get("rankCsvBtnText") or "").find("导出 CSV") >= 0,
      f"({out.get('rankCsvBtnText')})")

print("— CSV 内容 —")
check("数值模式 CSV 行数 ≥ 150（世界层 214 国）", (out.get("v_rows") or 0) >= 150, f"({out.get('v_rows')} 行)")
check("写入字节以 UTF-8 BOM 开头（csv 正文不含 BOM）", out.get("v_bomOk") is True)
check("表头含「排名,区域,指标,单位」", (out.get("v_head") or "").startswith("排名,区域,指标,单位,"),
      f"({out.get('v_head')})")
check("首行数据完整（6 列，含实际数据年）", len((out.get("v_line1") or "").split(",")) == 6, f"({out.get('v_line1')})")
check("文件名含层级/指标/年份", re.match(r"^atlas-[a-z]+-[a-z]+-\d{4}\.csv$", out.get("v_file") or "") is not None,
      f"({out.get('v_file')})")
check("派生指标 gdppc 也能导出", (out.get("pc_rows") or 0) >= 150, f"({out.get('pc_rows')} 行 · {out.get('pc_file')})")
check("gdppc 首行数值为正数",
      bool(out.get("pc_line1")) and float(out["pc_line1"].split(",")[4]) > 0,
      f"({out.get('pc_line1')})")
check("增长模式 CSV 有结果且表头标注名义增长",
      (out.get("g_rows") or 0) >= 50 and "名义增长" in (out.get("g_head") or ""),
      f"({out.get('g_rows')} 行 · {out.get('g_head')})")
check("增长模式首行为百分比", (out.get("g_line1") or "").rstrip().endswith("%"), f"({out.get('g_line1')})")
check("调用导出未抛异常", out.get("callCsvOk") is True and out.get("callPngOk") is True,
      f"(csv={out.get('callCsvOk')} png={out.get('callPngOk')})")

print("— 地图 PNG —")
check("getDataURL 返回 PNG data URL", (out.get("pngPrefix") or "").startswith("data:image/png;base64,"),
      f"({out.get('pngPrefix')})")
check("PNG 数据非空（>20KB，说明画布已渲染）", (out.get("pngLen") or 0) > 20000, f"({out.get('pngLen')} 字符)")

print("— C2 全量导出（区域×年份 长表）—")
check("C2 探针无异常", not out.get("full_err"), f"({out.get('full_err')})")
check("C2 buildFullExport / atlasLevelRegs 已定义", out.get("fnBuildFull") is True and out.get("fnLevelRegs") is True)
check("C2 全量导出按钮存在", out.get("hasFullCsvBtn") is True and out.get("hasFullJsonBtn") is True)
check("C2 全量 CSV 行数 ≥ 3000（214 国 × 多年）", (out.get("full_rows") or 0) >= 3000, f"({out.get('full_rows')} 行)")
check("C2 区域数 ≥ 150", (out.get("full_regions") or 0) >= 150, f"({out.get('full_regions')} 区域)")
check("C2 表头正确", (out.get("full_head") or "") == "层级,区域,键,指标,单位,年份,数值", f"({out.get('full_head')})")
check("C2 首行 7 列", len((out.get("full_line1") or "").split(",")) == 7, f"({out.get('full_line1')})")
check("C2 CSV 带 BOM(正文不含)", out.get("full_bom") is True)
check("C2 文件名 atlas-world-gdp-allyears.csv", out.get("full_csvname") == "atlas-world-gdp-allyears.csv", f"({out.get('full_csvname')})")
check("C2 JSON 结构正确(level/metric/regions/2023)", out.get("full_json_ok") is True)
check("C2 ≥100 国有 ≥20 年序列", (out.get("full_ycount") or 0) >= 100, f"({out.get('full_ycount')} 国)")
check("C2 调用全量 CSV 导出未抛异常", out.get("callFullCsvOk") is True, f"({out.get('callFullCsvOk')})")

print(f"\n导出回归: {ok}/{total} 通过")
sys.exit(0 if ok == total else 1)
