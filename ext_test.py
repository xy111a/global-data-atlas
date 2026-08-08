#!/usr/bin/env python3
"""新指标（EXT）专项验证 v2：世界层贸易着色 + 省/州层提示"""
import subprocess, os, re

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def dump(url, wait=18):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait+15)
    return r.stdout.decode("utf-8", "replace")

# 立即执行探针（不等 load，用 setTimeout 等数据就绪）
probe = """<script>
var out = [];
try{
  setTimeout(function(){
    try{
      var btns = document.querySelectorAll('#metricSeg button');
      out.push('指标按钮数=' + btns.length);
      out.push('按钮=' + Array.from(btns).map(b=>b.dataset.m+':'+b.textContent).join(','));
      out.push('EXT国家数=' + (window.EXT ? Object.keys(window.EXT).length : 0));
      // 世界层贸易取数
      var cn = regCountry('CN'), us = regCountry('US');
      out.push('CN trade@2023=' + (cn?regGet(cn,'trade',2023).toFixed(2):'null') + '%');
      out.push('US health@2023=' + (us?regGet(us,'health',2023).toFixed(2):'null') + '%');
      out.push('CN life@2023=' + (cn?regGet(cn,'life',2023):'null') + '岁');
      out.push('CN gdpcap@2023=' + (cn?regGet(cn,'gdpcap',2023).toFixed(0):'null') + 'USD');
      // 切到贸易指标（世界层）
      var tb = Array.from(btns).find(b=>b.dataset.m==='trade');
      if(tb) tb.click();
      setTimeout(function(){
        out.push('切换后排行标题=' + ((document.querySelector('.rank-title')||{}).textContent||''));
        // 省层应提示不可用
        loadChina();
        setTimeout(function(){
          out.push('省层面板=' + document.getElementById('pName').textContent + '|' + (document.getElementById('pHint').textContent||'').slice(0,50));
        }, 1500);
      }, 800);
    }catch(e){ out.push('内层错误: ' + e.message); }
    document.body.insertAdjacentHTML('beforeend','<pre id="probe">' + out.join('\\n') + '</pre>');
  }, 2500);
}catch(e){
  document.body.insertAdjacentHTML('beforeend','<pre id="probe">外层错误: ' + e.message + '</pre>');
}
</script>"""

def main():
    html = open('global-data-atlas.html', encoding='utf-8').read()
    html = html.replace('</body>', probe + '\n</body>')
    open('atlas_test/v2_ext.html', 'w', encoding='utf-8').write(html)
    dom = dump("file://" + os.path.abspath('atlas_test/v2_ext.html'))
    pres = re.findall(r'<pre id="probe">(.*?)</pre>', dom, re.S)
    print(pres[-1] if pres else "未获取验证输出")

if __name__ == "__main__":
    main()
