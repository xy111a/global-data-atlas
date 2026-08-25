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

echo "── 同步 vendor → dist/vendor ──"
mkdir -p dist/vendor
cp -R vendor/. dist/vendor/
# world.json 是构建源（build_*.js 读取），运行时地图由 world.js 提供，部署无需携带 → 剔除省 ~1MB
rm -f dist/vendor/world.json

echo "── md5 校验 ──"
ok=1
for f in global-data-atlas.html compare.html about.html; do
  s=$(md5 -q "$f"); d=$(md5 -q "dist/$f")
  if [ "$s" = "$d" ]; then echo "  ✓ $f 一致"; else echo "  ✗ $f 漂移"; ok=0; fi
done
s=$(md5 -q global-data-atlas.html); d=$(md5 -q dist/index.html)
if [ "$s" = "$d" ]; then echo "  ✓ index.html 一致"; else echo "  ✗ index.html 漂移"; ok=0; fi
# vendor 关键文件抽查（HTML 按需加载的脚本/数据）
for f in vendor/app-core.js vendor/eu/eu_metrics.js vendor/world.js; do
  rel="${f#vendor/}"
  s=$(md5 -q "$f"); d=$(md5 -q "dist/vendor/$rel")
  if [ "$s" = "$d" ]; then echo "  ✓ $rel 一致"; else echo "  ✗ $rel 漂移"; ok=0; fi
done
[ "$ok" = 1 ] || { echo "dist 与 source 不一致，中止。"; exit 1; }

# 缓存失效：给 app-core.js 引用注入内容指纹（?v=md5前8位）——JS 内容变化后 URL 变化，绕过浏览器/CDN 4h 缓存
CORE_HASH=$(md5 -q vendor/app-core.js | cut -c1-8)
for f in dist/global-data-atlas.html dist/index.html dist/compare.html; do
  sed -i '' -E "s|src=\"vendor/app-core.js(\\?v=[a-f0-9]+)?\"|src=\"vendor/app-core.js?v=${CORE_HASH}\"|g" "$f"
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
