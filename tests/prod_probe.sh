#!/bin/bash
# A3 线上探针（2026-10-12，补门禁盲区）：门禁全在本地对文件断言，抓不到「部署→边缘缓存→SW」这条
# 真实分发链路（本次审计的 P1/P2 根因即在此）。本脚本打生产 URL，断言关键数据集真的把最新内容送到了用户。
# 用法: ./tests/prod_probe.sh [BASE_URL]     （默认 https://atlas.huajun.wang；任一断言失败退出非 0，可直接进 CI）
set -e
BASE="${1:-https://atlas.huajun.wang}"
cd "$(dirname "$0")/.."
FAIL=0
note() { echo "  $1"; }
check() { if eval "$2"; then echo "  ✓ $1"; else echo "  ✗ $1"; FAIL=1; fi; }

echo "════ 线上探针：$BASE ════"

# 1) 首页可达
check "首页 HTTP 200" "curl -m 25 -sS -o /dev/null -w '%{http_code}' '$BASE/' | grep -q '^200$'"

# 2) 关键安全头在位（CSP / nosniff）
HDR="$(curl -m 25 -sS -D - -o /dev/null "$BASE/" 2>/dev/null || true)"
check "响应含 Content-Security-Policy" "printf '%s' '$HDR' | grep -qi 'content-security-policy'"
check "响应含 X-Content-Type-Options: nosniff" "printf '%s' '$HDR' | grep -qi 'x-content-type-options: *nosniff'"

# 3) 数据文件指纹已生效：从生产首页解析 us_pop_ts.js 的引用 URL
POPREF="$(printf '%s' "$HDR" >/dev/null 2>&1; curl -m 25 -sS "$BASE/" 2>/dev/null | grep -oE 'vendor/us_pop_ts\.js(\?v=[a-f0-9]+)?' | head -1 || true)"
note "首页解析到的引用: ${POPREF:-（空）}"
# 3a) 该引用应带 ?v=（证明部署的是新版 A2 构建，而非旧的裸 URL）
check "us_pop_ts.js 引用带 ?v= 内容指纹" "printf '%s' '$POPREF' | grep -q '?v='"

# 4) 取该 URL 的实际内容，断言是「逐年」新数据（含 2023/2024，而非旧的仅 2020+2025）
POPJSON="$(curl -m 30 -sS "$BASE/${POPREF}" 2>/dev/null || true)"
check "线上 us_pop_ts.js 含 2024 逐年数据(非陈旧)" "printf '%s' '$POPJSON' | grep -q '\"2024\"'"
check "线上 us_pop_ts.js 含 2023 逐年数据(非陈旧)" "printf '%s' '$POPJSON' | grep -q '\"2023\"'"

echo "────────────────────────"
if [ "$FAIL" = 0 ]; then echo "线上探针: 全部通过 ✅"; else echo "线上探针: 存在失败 ❌"; exit 1; fi
