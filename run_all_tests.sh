#!/bin/bash
# 全量测试门禁（L5）：语法 → 数据自洽 → 回归截图 → 对比 → EXT
# 用法: ./run_all_tests.sh   （任一步失败即退出非 0）
set -e
cd "$(dirname "$0")"
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
python3 tests/data_verify.py > /tmp/verify.log 2>&1 && tail -1 /tmp/verify.log || { echo "  ✗ 数据自洽失败:"; grep ✗ /tmp/verify.log | head -5; exit 1; }
echo "  ✓ L2 通过"; PASS=$((PASS+1))

step "L3a 回归截图（offline_test）"
python3 tests/offline_test.py > /tmp/offline.log 2>&1 && grep -c "OK" /tmp/offline.log || { echo "  ✗ 回归失败:"; grep -E "FAIL|Error" /tmp/offline.log | head -5; exit 1; }
echo "  ✓ L3a 通过"; PASS=$((PASS+1))

step "L3b 对比模式（cmp_test）"
python3 tests/test_compare.py > /tmp/cmp.log 2>&1 && tail -2 /tmp/cmp.log || { echo "  ✗ 对比失败:"; tail -5 /tmp/cmp.log; exit 1; }
echo "  ✓ L3b 通过"; PASS=$((PASS+1))

step "L3c 扩展指标（ext_test）"
python3 tests/ext_test.py > /tmp/ext.log 2>&1 && tail -2 /tmp/ext.log || { echo "  ✗ EXT 失败:"; tail -5 /tmp/ext.log; exit 1; }
echo "  ✓ L3c 通过"; PASS=$((PASS+1))

step "L3d 四维经济洞察（econ_insight）"
python3 tests/econ_insight_check.py > /tmp/econ.log 2>&1 && grep -q "人均GDP" /tmp/econ.log || { echo "  ✗ 四维洞察失败:"; tail -8 /tmp/econ.log; exit 1; }
echo "  ✓ L3d 通过"; PASS=$((PASS+1))

step "L3e 欧盟 NUTS2 下钻（eu_test）"
python3 tests/eu_test.py > /tmp/eu.log 2>&1 && grep -q "LEVEL=nuts" /tmp/eu.log || { echo "  ✗ 欧盟下钻失败:"; tail -8 /tmp/eu.log; exit 1; }
echo "  ✓ L3e 通过"; PASS=$((PASS+1))

step "L3f URL 状态持久化（url_state_test）"
python3 tests/url_state_test.py > /tmp/url.log 2>&1 && grep -q "restore: OK" /tmp/url.log || { echo "  ✗ URL 持久化失败:"; tail -8 /tmp/url.log; exit 1; }
echo "  ✓ L3f 通过"; PASS=$((PASS+1))
step "L3g 双币切换（cur_test）"
python3 tests/cur_test.py > /tmp/cur.log 2>&1 && tail -1 /tmp/cur.log || { echo "  ✗ 双币失败:"; tail -5 /tmp/cur.log; exit 1; }
echo "  ✓ L3g 通过"; PASS=$((PASS+1))

echo ""
echo "════ 门禁结果: $PASS/$((PASS+FAIL)) 步通过 ════"
