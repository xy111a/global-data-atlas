#!/usr/bin/env python3
"""V2 DOM 验证：确认趋势容器真实渲染了 ECharts canvas 与标题"""
import subprocess, os

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def dump(url, wait=9):
    cmd = [CHROME, "--headless", "--no-sandbox", "--disable-gpu",
           f"--virtual-time-budget={wait*1000}", "--dump-dom", url]
    r = subprocess.run(cmd, capture_output=True, timeout=wait+15)
    return r.stdout.decode("utf-8", "replace")

dom = dump("file://" + os.path.abspath("global-data-atlas.html"), 9)
print("世界层: trendChart=" + ("是" if 'id="trendChart"' in dom else "否")
      + ", 对比标题=" + ("是" if '较2000 实际增长' in dom else "否"))

dom2 = dump("file://" + os.path.abspath("atlas_test/v2_gd.html"), 13)
print("广东详情: trendChart=" + ("是" if 'id="trendChart"' in dom2 else "否")
      + ", 趋势标题=" + ("是" if 'GDP 趋势' in dom2 else "否"))
