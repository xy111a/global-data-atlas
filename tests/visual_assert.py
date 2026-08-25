#!/usr/bin/env python3
"""L3h 视觉/数值深度断言：驱动交互并断言真实渲染值（非仅“不崩溃”）。

复用 audit_all.py 的 headless-chrome 模式：CHROME_BIN + --dump-dom + 注入脚本把
结果写入 <pre id="ck">R{json}</pre>。断言项：

  A 世界总览      canvas 已绘制(width>0)；visualMap 图例存在
  B 单击国家 CN   #panel 的 GDP 文本 == fmtGDP(regGet(regCountry('CN'),'gdp',dataYear))
  C 双击 CN 下钻  省级地图 canvas 已绘制；#panel 显示“中国”
  D 单击省 广东    #panel GDP == fmtGDP(regGet(regProv('广东'),'gdp',dataYear))；#trend 有 GDP 趋势块
  E 单击美国州 CA  #panel GDP == fmtGDP(regGet(regUSState('California'),'gdp',dataYear))  —— 同时守住 P2-6 USD 基准，
                  旧 CNY 反模式会产出不同字符串，故该断言即回归护栏
  F 单击日本县     #panel GDP == fmtGDP(regGet(regJapanPref('北海道'),'gdp',dataYear))
  G 单击欧盟 NUTS  #panel GDP == fmtGDP(regGet(regNUTS('DE11'),'gdp',dataYear))

任一断言失败即 exit(1)。
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
function ptext(){ return document.getElementById('panel') ? document.getElementById('panel').textContent : ''; }
function canvasPainted(){ var cs=document.querySelectorAll('canvas'); for(var i=0;i<cs.length;i++){ if(cs[i].width>0 && cs[i].height>0) return true; } return false; }
function trendHas(){ var t=document.getElementById('trend'); return !!t && t.textContent.replace(/\\s/g,'').length>0; }
var out=[];
function check(step, cond, detail){ out.push({step:step, pass:!!cond, detail:detail||''}); }
(async function(){
  // A 世界总览
  await new Promise(function(r){ setTimeout(r, 1500); });
  check('A_world_canvas', canvasPainted(), 'canvas width>0');
  check('A_world_legend', /高/.test(document.body.textContent) && /低/.test(document.body.textContent), 'visualMap 高/低 图例');

  // B 国家 CN
  showCountry(COUNTRIES.find(function(c){return c[2]==='CN'}));
  await new Promise(function(r){ setTimeout(r, 900); });
  var expCN=fmtGDP(regGet(regCountry('CN'),'gdp',dataYear));
  check('B_CN_panel_gdp', ptext().indexOf(expCN)>=0, 'expected='+expCN+'|got='+ptext().replace(/\\s+/g,' ').slice(0,80));

  // C 双击 CN 下钻 → 中国总览
  DRILLABLE['CN'].load();
  await new Promise(function(r){ setTimeout(r, 1600); });
  check('C_CN_drill_canvas', canvasPainted(), '省级地图 canvas');
  check('C_CN_panel_label', /中国/.test(ptext()), 'panel 含“中国”');

  // D 省 广东
  showProvincePanel('广东');
  await new Promise(function(r){ setTimeout(r, 900); });
  var expGD=fmtGDP(regGet(regProv('广东'),'gdp',dataYear));
  check('D_GD_panel_gdp', ptext().indexOf(expGD)>=0, 'expected='+expGD+'|got='+ptext().replace(/\\s+/g,' ').slice(0,80));
  check('D_GD_trend', trendHas(), 'GDP 趋势块存在');

  // E 美国州 California（P2-6 USD 基准护栏）
  showUSStatePanel('California');
  await new Promise(function(r){ setTimeout(r, 900); });
  var expUS=fmtGDP(regGet(regUSState('California'),'gdp',dataYear));
  check('E_US_panel_gdp', ptext().indexOf(expUS)>=0, 'expected='+expUS+'|got='+ptext().replace(/\\s+/g,' ').slice(0,80));
  // 旧 CNY 反模式会把 3.9万亿 美元误算成几十万亿人民币 → 含“元”且数值异常大；USD 基准应含“美元”或“$”
  check('E_US_not_cny_antipattern', /美元|\\$|万亿/.test(ptext()) && !/亿元/.test(ptext().replace(expUS,'')), '无 CNY 反模式残留');

  // F 日本县 北海道
  showJapanPrefPanel('北海道');
  await new Promise(function(r){ setTimeout(r, 900); });
  var expJP=fmtGDP(regGet(regJapanPref('北海道'),'gdp',dataYear));
  check('F_JP_panel_gdp', ptext().indexOf(expJP)>=0, 'expected='+expJP+'|got='+ptext().replace(/\\s+/g,' ').slice(0,80));

  // H 城市级（深圳市：adcode 440300 / 父 440000）。CITY_METRICS 随页面急加载（非懒加载），
  //    与"省→点击城市"同一渲染函数 showCityPanel，直接 open 即校验城市面板数据绑定
  showCityPanel('深圳市', '440300', '440000');
  await new Promise(function(r){ setTimeout(r, 900); });
  var cmSz=getCityMetric('440300','440000');
  var rCity=regCity(cmSz,'440300');
  var expCity=fmtGDP(rCity.get('gdp', dataYear));
  check('H_city_panel_gdp', ptext().indexOf(expCity)>=0 && /深圳市/.test(ptext()), 'expected='+expCity+'|got='+ptext().replace(/\\s+/g,' ').slice(0,80));
  check('H_city_panel_render', /地级市/.test(ptext()) || (document.getElementById('trend')&&document.getElementById('trend').textContent.replace(/\\s/g,'').length>0), '城市面板已渲染（层级标识/趋势）');

  // G 欧盟 NUTS DE11（必须先进入 EU/DE 下钻：EU_METRICS 与 geo 均为懒加载，
  //    应用从不裸调 showNUTSPanel，故此处先 loadNUTS('DE') 再下钻）
  await loadNUTS('DE');
  await new Promise(function(r){ setTimeout(r, 2500); });  // 等待 geo+metrics 懒加载完成
  showNUTSPanel('DE11');
  await new Promise(function(r){ setTimeout(r, 900); });
  var expEU=fmtGDP(regGet(regNUTS('DE11'),'gdp',dataYear));
  check('G_EU_panel_gdp', ptext().indexOf(expEU)>=0, 'expected='+expEU+'|got='+ptext().replace(/\\s+/g,' ').slice(0,80));
  check('G_EU_canvas', canvasPainted(), 'NUTS 地图 canvas 已绘制');

  document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify(out)+'</pre>');
})();
}catch(e){document.body.insertAdjacentHTML('beforeend','<pre id="ck">R'+JSON.stringify([{step:'FATAL',pass:false,detail:e.message}])+'</pre>')}
},900);});</script>"""
html = html.replace("</body>", inject + "\n</body>")
p = os.path.join("atlas_test", "visual_assert.html")
open(p, "w", encoding="utf-8").write(html)
r = subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                    "--virtual-time-budget=40000", "--dump-dom", "file://" + os.path.abspath(p)],
                   capture_output=True, timeout=90)
dom = r.stdout.decode("utf-8", "replace")
pres = [m for m in re.findall(r'<pre id="ck">R(.*?)</pre>', dom, re.S) if not m.startswith("'+")]
raw = pres[-1] if pres else "[]"
try:
    out = json.loads(raw)
except Exception as e:
    print("  解析失败:", raw[:200], e); sys.exit(1)

fails = 0
for row in out:
    mark = "✓" if row.get("pass") else "✗"
    print(f"  {mark} {row['step']}  {row.get('detail','')}")
    if not row.get("pass"):
        fails += 1
print(f"  断言: {len(out)-fails}/{len(out)} 通过")
if fails:
    print(f"  ✗ 视觉/数值深度断言失败 {fails} 项"); sys.exit(1)
print("  ✓ L3h 通过")
