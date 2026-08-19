#!/bin/bash
# 构建+部署门禁：source → dist 同步 → md5 校验 → （可选）Cloudflare Pages 部署
# 用法:
#   ./build.sh           # 只同步 dist 并校验（防漂移门禁）
#   ./build.sh --deploy  # 同步 + 校验 + 部署上线
set -e
cd "$(dirname "$0")"

# 可移植 md5（macOS /sbin/md5、Linux md5sum、通用 shasum）
if command -v md5 >/dev/null 2>&1; then
  HASH() { md5 -q "$1"; }
elif command -v md5sum >/dev/null 2>&1; then
  HASH() { md5sum "$1" | awk '{print $1}'; }
else
  HASH() { shasum -a 1 "$1" | awk '{print $1}'; }
fi

echo "── 同步 source → dist ──"
for f in global-data-atlas.html compare.html about.html; do
  cp "$f" "dist/$f"
done
cp global-data-atlas.html dist/index.html

echo "── 同步 vendor → dist/vendor ──"
mkdir -p dist/vendor
cp -R vendor/. dist/vendor/

echo "── md5 校验 ──"
ok=1
for f in global-data-atlas.html compare.html about.html; do
  s=$(HASH "$f"); d=$(HASH "dist/$f")
  if [ "$s" = "$d" ]; then echo "  ✓ $f 一致"; else echo "  ✗ $f 漂移"; ok=0; fi
done
s=$(HASH global-data-atlas.html); d=$(HASH dist/index.html)
if [ "$s" = "$d" ]; then echo "  ✓ index.html 一致"; else echo "  ✗ index.html 漂移"; ok=0; fi
# vendor 关键文件抽查（HTML 按需加载的脚本/数据）
for f in vendor/app-core.js vendor/eu/eu_metrics.js vendor/world.js; do
  rel="${f#vendor/}"
  s=$(HASH "$f"); d=$(HASH "dist/vendor/$rel")
  if [ "$s" = "$d" ]; then echo "  ✓ $rel 一致"; else echo "  ✗ $rel 漂移"; ok=0; fi
done
[ "$ok" = 1 ] || { echo "dist 与 source 不一致，中止。"; exit 1; }

# 缓存失效：给 app-core.js 引用注入内容指纹（?v=md5前8位）——JS 内容变化后 URL 变化，绕过浏览器/CDN 4h 缓存
CORE_HASH=$(HASH vendor/app-core.js | cut -c1-8)
for f in dist/global-data-atlas.html dist/index.html dist/compare.html; do
  sed -i '' "s|src=\"vendor/app-core.js\"|src=\"vendor/app-core.js?v=${CORE_HASH}\"|" "$f"
done
echo "  ↻ app-core.js?v=${CORE_HASH}（缓存指纹已注入）"

if [ "$1" = "--deploy" ]; then
  echo "── 部署 Cloudflare Pages ──"
  # 绕过系统代理（本机代理会导致 fetch failed）
  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
    wrangler pages deploy dist --project-name=global-data-atlas --branch=main
else
  echo "dist 已同步（加 --deploy 发布上线）"
fi
