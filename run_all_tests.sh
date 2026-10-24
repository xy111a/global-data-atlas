#!/bin/bash
# 全量测试门禁（L5）：语法 → 数据自洽 → 回归截图 → 对比 → EXT → 深度断言 → 性能 → 视觉回归 → 排行模式切换
# 用法: ./run_all_tests.sh   （任一步失败即退出非 0）
# 依赖: L3j 视觉回归需要 Pillow + websocket-client（pip install -r tests/requirements.txt）；
#       本机受管 venv 已装；无 websocket-client 时移动端溢出断言降级跳过（不误报）
set -e
cd "$(dirname "$0")"
# 选取能 import PIL + websocket 的 python（L3j 视觉/移动端真机模拟需要）；
# 2026-10-24 审计：此前只测 PIL，系统 python3 命中后跳过了带 websocket 的受管 venv，
# 导致 375 视口断言被软跳过（实际在 500 宽下测）。
PY="${PYTHON:-python3}"
if ! "$PY" -c "import PIL, websocket" 2>/dev/null; then
  for cand in /Users/huajun/.workbuddy/binaries/python/envs/default/bin/python python3; do
    if [ -x "$cand" ] && "$cand" -c "import PIL, websocket" 2>/dev/null; then PY="$cand"; break; fi
  done
fi
if ! "$PY" -c "import PIL, websocket" 2>/dev/null; then
  echo "⚠ 未找到同时具备 Pillow + websocket-client 的 Python，L3j 移动端断言将降级（建议 pip install -r tests/requirements.txt）"
fi
PASS=0; FAIL=0
step() { echo ""; echo "════ $1 ════"; }

step "L1 语法检查（inline scripts）"
python3 - <<'EOF'
import re, subprocess, tempfile, os
html = open('global-data-atlas.html', encoding='utf-8').read()
blocks = re.findall(r'<script>(.*?)</script>', html, re.S)
ok = True
for i, b in enumerate(blocks):
    if not b.strip(): continue
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
        f.write(b); path = f.name
    r = subprocess.run(['node', '--check', path], capture_output=True, text=True)
    if r.returncode != 0:
        ok = False; print(f'  FAIL {i}: {r.stderr[:200]}')
    os.unlink(path)
print('  SYNTAX:', 'OK' if ok else 'FAIL')
exit(0 if ok else 1)
EOF
echo "  ✓ L1 通过"; PASS=$((PASS+1))

step "L2 数据自洽校验"
"$PY" tests/data_verify.py > /tmp/verify.log 2>&1 && tail -1 /tmp/verify.log || { echo "  ✗ 数据自洽失败:"; grep ✗ /tmp/verify.log | head -5; exit 1; }
echo "  ✓ L2 通过"; PASS=$((PASS+1))

step "L2b 增长口径一致性（growth_currency_test，P0 回归护栏）"
# reg.growth() 必须与「展示币种(USD)端点之比」完全吻合。
# 2026-10-12 曾发现 EU NUTS2 / 中国省级 / 中国城市 三层在源币种(CNY)上算增长、
# 却以 USD 展示，导致同屏数值与百分比不自洽（省最大偏差 383pp、EU 最大 177pp）。
NODE="${NODE:-node}"
"$NODE" tests/growth_currency_test.js > /tmp/growthcur.log 2>&1 && tail -1 /tmp/growthcur.log || { echo "  ✗ 增长口径失败:"; grep '✗' /tmp/growthcur.log | head -8; exit 1; }
echo "  ✓ L2b 通过"; PASS=$((PASS+1))

step "L2c ATLAS_META 新鲜度（meta_freshness_test，含浏览器渲染断言）"
# meta.js 的 datasets 曾是零引用死元数据，us/japan 年份写错也无人发现。
# 此处同时守住「声明年==数据实际年」与「about.html 真的把表渲染出来」。
"$PY" tests/meta_freshness_test.py > /tmp/metafresh.log 2>&1 && tail -1 /tmp/metafresh.log || { echo "  ✗ meta 新鲜度失败:"; grep '❌' /tmp/metafresh.log | head -8; exit 1; }
echo "  ✓ L2c 通过"; PASS=$((PASS+1))

step "L3a 回归截图（offline_test）"
"$PY" tests/offline_test.py > /tmp/offline.log 2>&1 && grep -c "OK" /tmp/offline.log || { echo "  ✗ 回归失败:"; grep -E "FAIL|Error" /tmp/offline.log | head -5; exit 1; }
echo "  ✓ L3a 通过"; PASS=$((PASS+1))

step "L3b 对比模式（cmp_test）"
"$PY" tests/test_compare.py > /tmp/cmp.log 2>&1 && tail -2 /tmp/cmp.log || { echo "  ✗ 对比失败:"; tail -5 /tmp/cmp.log; exit 1; }
echo "  ✓ L3b 通过"; PASS=$((PASS+1))

step "L3b2 对比页数据口径（compare_data_test，2026-10-24 P1 回归）"
"$PY" tests/compare_data_test.py > /tmp/cmpdata.log 2>&1 && tail -1 /tmp/cmpdata.log || { echo "  ✗ 对比页数据口径失败:"; tail -20 /tmp/cmpdata.log; exit 1; }
echo "  ✓ L3b2 通过"; PASS=$((PASS+1))

step "L3c 扩展指标（ext_test）"
"$PY" tests/ext_test.py > /tmp/ext.log 2>&1 && tail -2 /tmp/ext.log || { echo "  ✗ EXT 失败:"; tail -5 /tmp/ext.log; exit 1; }
echo "  ✓ L3c 通过"; PASS=$((PASS+1))

step "L3d 四维经济洞察（econ_insight）"
"$PY" tests/econ_insight_check.py > /tmp/econ.log 2>&1 && grep -q "人均GDP" /tmp/econ.log || { echo "  ✗ 四维洞察失败:"; tail -8 /tmp/econ.log; exit 1; }
echo "  ✓ L3d 通过"; PASS=$((PASS+1))

step "L3e 欧盟 NUTS2 下钻（eu_test）"
"$PY" tests/eu_test.py > /tmp/eu.log 2>&1 && grep -q "LEVEL=nuts" /tmp/eu.log || { echo "  ✗ 欧盟下钻失败:"; tail -8 /tmp/eu.log; exit 1; }
echo "  ✓ L3e 通过"; PASS=$((PASS+1))

step "L3f URL 状态持久化（url_state_test）"
"$PY" tests/url_state_test.py > /tmp/url.log 2>&1 && grep -q "restore: OK" /tmp/url.log || { echo "  ✗ URL 持久化失败:"; tail -8 /tmp/url.log; exit 1; }
echo "  ✓ L3f 通过"; PASS=$((PASS+1))

step "L3f2 深层 URL 恢复（url_restore_deep_test，省/市分享链接）"
"$PY" tests/url_restore_deep_test.py > /tmp/urldeep.log 2>&1 && tail -1 /tmp/urldeep.log || { echo "  ✗ 深层 URL 恢复失败:"; tail -12 /tmp/urldeep.log; exit 1; }
echo "  ✓ L3f2 通过"; PASS=$((PASS+1))

step "L3g 固定美元（cur_test）"
"$PY" tests/cur_test.py > /tmp/cur.log 2>&1 && tail -1 /tmp/cur.log || { echo "  ✗ 固定美元失败:"; tail -5 /tmp/cur.log; exit 1; }
echo "  ✓ L3g 通过"; PASS=$((PASS+1))

step "L3h 视觉/数值深度断言（visual_assert）"
"$PY" tests/visual_assert.py > /tmp/visual.log 2>&1 && tail -3 /tmp/visual.log || { echo "  ✗ 深度断言失败:"; tail -12 /tmp/visual.log; exit 1; }
echo "  ✓ L3h 通过"; PASS=$((PASS+1))

step "L3i 运行时性能实测（perf_trace）"
"$PY" tests/perf_trace.py > /tmp/perf.log 2>&1 && tail -8 /tmp/perf.log || { echo "  ✗ 性能实测失败:"; tail -12 /tmp/perf.log; exit 1; }
echo "  ✓ L3i 通过"; PASS=$((PASS+1))

step "L3j 视觉/响应式回归（visual_regression）"
"$PY" tests/visual_regression.py > /tmp/visreg.log 2>&1 && tail -14 /tmp/visreg.log || { echo "  ✗ 视觉/响应式回归失败:"; tail -20 /tmp/visreg.log; exit 1; }
echo "  ✓ L3j 通过"; PASS=$((PASS+1))

step "L3k 搜索/ESC 回归（search_esc_test）"
"$PY" tests/search_esc_test.py > /tmp/searchesc.log 2>&1 && tail -3 /tmp/searchesc.log || { echo "  ✗ 搜索/ESC 失败:"; tail -8 /tmp/searchesc.log; exit 1; }
echo "  ✓ L3k 通过"; PASS=$((PASS+1))

step "L3l 排行模式切换（rank_growth_test，T6）"
"$PY" tests/rank_growth_test.py > /tmp/rankg.log 2>&1 && tail -3 /tmp/rankg.log || { echo "  ✗ 排行模式切换失败:"; tail -12 /tmp/rankg.log; exit 1; }
echo "  ✓ L3l 通过"; PASS=$((PASS+1))

step "L3m 配色刻度切换（color_scale_test，T7）"
"$PY" tests/color_scale_test.py > /tmp/cscale.log 2>&1 && tail -3 /tmp/cscale.log || { echo "  ✗ 配色刻度失败:"; tail -12 /tmp/cscale.log; exit 1; }
echo "  ✓ L3m 通过"; PASS=$((PASS+1))

step "L3n 数据新鲜度标注（freshness_test，T8）"
"$PY" tests/freshness_test.py > /tmp/fresh.log 2>&1 && tail -3 /tmp/fresh.log || { echo "  ✗ 新鲜度标注失败:"; tail -12 /tmp/fresh.log; exit 1; }
echo "  ✓ L3n 通过"; PASS=$((PASS+1))

step "L3o 可信度/SEO 结构化数据（seo_methodology_test，T9）"
"$PY" tests/seo_methodology_test.py > /tmp/seo.log 2>&1 && tail -3 /tmp/seo.log || { echo "  ✗ SEO/方法论失败:"; tail -12 /tmp/seo.log; exit 1; }
echo "  ✓ L3o 通过"; PASS=$((PASS+1))

step "L3p 搜索键盘可达性（a11y_search_test，T10）"
"$PY" tests/a11y_search_test.py > /tmp/a11y.log 2>&1 && tail -3 /tmp/a11y.log || { echo "  ✗ 键盘可达性失败:"; tail -12 /tmp/a11y.log; exit 1; }
echo "  ✓ L3p 通过"; PASS=$((PASS+1))

step "L3v 年份标签/增长窗口（year_label_test，2026-10-24 P1 回归）"
"$PY" tests/year_label_test.py > /tmp/yearlabel.log 2>&1 && tail -1 /tmp/yearlabel.log || { echo "  ✗ 年份标签失败:"; tail -14 /tmp/yearlabel.log; exit 1; }
echo "  ✓ L3v 通过"; PASS=$((PASS+1))

step "L3u 顶栏单行化 + 品牌一体性（header_single_row_test）"
# 断言：≥1280px 顶栏保持单行（brand/metric-zone/tb-actions 同一行）、无横向溢出、
# 指标分区（核心 5 在 seg / 扩展 10 在下拉 / 工具 6）、品牌区存在、两个下拉可展开。
"$PY" tests/header_single_row_test.py > /tmp/header.log 2>&1 && tail -1 /tmp/header.log || { echo "  ✗ 顶栏布局失败:"; grep '❌' /tmp/header.log | head -8; exit 1; }
echo "  ✓ L3u 通过"; PASS=$((PASS+1))

step "L3q 嵌入模式 ?embed=1（embed_mode_test，T11）"
"$PY" tests/embed_mode_test.py > /tmp/embed.log 2>&1 && tail -3 /tmp/embed.log || { echo "  ✗ 嵌入模式失败:"; tail -12 /tmp/embed.log; exit 1; }
echo "  ✓ L3q 通过"; PASS=$((PASS+1))

step "L3r 欧盟多年序列+派生指标（eu_year_metric_test，浏览器实测）"
# 不信任文档：FEATURES.md/meta.js 长期写着欧盟「2023 单年」，但数据其实早就是 2000–2024
# 多年序列。这里在真实浏览器里验证年份切换生效、派生指标可用、排行榜能出结果。
"$PY" tests/eu_year_metric_test.py > /tmp/euym.log 2>&1 && tail -1 /tmp/euym.log || { echo "  ✗ 欧盟年份/派生指标失败:"; grep '❌' /tmp/euym.log | head -8; exit 1; }
echo "  ✓ L3r 通过"; PASS=$((PASS+1))

step "L3s 主页导出 CSV/PNG（export_test）"
# 导出此前只在 compare.html 有：主页排行/地图拿不到数据。断言落在生成的字节与渲染链路上。
"$PY" tests/export_test.py > /tmp/export.log 2>&1 && tail -1 /tmp/export.log || { echo "  ✗ 导出失败:"; grep '❌' /tmp/export.log | head -8; exit 1; }
echo "  ✓ L3s 通过"; PASS=$((PASS+1))

step "L3t 关系散点渲染（scatter_test，P3·C1）"
# 断言 ScatterChart 组件模型真创建 + 点进数据模型（吸取 visualMap「配置≠渲染」教训）
"$PY" tests/scatter_test.py > /tmp/scatter.log 2>&1 && tail -1 /tmp/scatter.log || { echo "  ✗ 散点失败:"; grep '❌' /tmp/scatter.log | head -8; exit 1; }
echo "  ✓ L3t 通过"; PASS=$((PASS+1))

echo ""
echo "════ 门禁结果: $PASS/$((PASS+FAIL)) 步通过 ════"
