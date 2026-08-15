#!/bin/bash
# 构建+部署门禁：source → dist 同步 → md5 校验 → （可选）Cloudflare Pages 部署
# 用法:
#   ./build.sh           # 只同步 dist 并校验（防漂移门禁）
#   ./build.sh --deploy  # 同步 + 校验 + 部署上线
set -e
cd "$(dirname "$0")"

echo "── 同步 source → dist ──"
for f in global-data-atlas.html compare.html about.html; do
  cp "$f" "dist/$f"
done
cp global-data-atlas.html dist/index.html

echo "── md5 校验 ──"
ok=1
for f in global-data-atlas.html compare.html about.html; do
  s=$(md5 -q "$f"); d=$(md5 -q "dist/$f")
  if [ "$s" = "$d" ]; then echo "  ✓ $f 一致"; else echo "  ✗ $f 漂移"; ok=0; fi
done
s=$(md5 -q global-data-atlas.html); d=$(md5 -q dist/index.html)
if [ "$s" = "$d" ]; then echo "  ✓ index.html 一致"; else echo "  ✗ index.html 漂移"; ok=0; fi
[ "$ok" = 1 ] || { echo "dist 与 source 不一致，中止。"; exit 1; }

if [ "$1" = "--deploy" ]; then
  echo "── 部署 Cloudflare Pages ──"
  # 绕过系统代理（本机代理会导致 fetch failed）
  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
    wrangler pages deploy dist --project-name=global-data-atlas --branch=main
else
  echo "dist 已同步（加 --deploy 发布上线）"
fi
