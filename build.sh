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
for f in global-data-atlas.html compare.html about.html 404.html robots.txt sitemap.xml favicon.svg favicon.ico _headers sw.js og-image.png; do
  if [ -f "$f" ]; then cp "$f" "dist/$f"; fi
done
cp global-data-atlas.html dist/index.html
# 嵌入专用入口：/embed.html（_headers 对其放开 frame-ancestors，跨域嵌入走此路径）
cp global-data-atlas.html dist/embed.html
# 兼容：about/compare 返回链接指向 index.html；保留 global-data-atlas.html 副本

echo "── 同步 vendor → dist/vendor ──"
mkdir -p dist/vendor
cp -R vendor/. dist/vendor/
# world.json 是构建源（build_*.js 读取），运行时地图由 world.js 提供，部署无需携带 → 剔除省 ~1MB
rm -f dist/vendor/world.json

echo "── md5 校验 ──"
ok=1
for f in global-data-atlas.html compare.html about.html 404.html robots.txt sitemap.xml favicon.svg favicon.ico _headers sw.js og-image.png; do
  [ -f "$f" ] || continue
  s=$(HASH "$f"); d=$(HASH "dist/$f")
  if [ "$s" = "$d" ]; then echo "  ✓ $f 一致"; else echo "  ✗ $f 漂移"; ok=0; fi
done
s=$(HASH global-data-atlas.html); d=$(HASH dist/index.html)
if [ "$s" = "$d" ]; then echo "  ✓ index.html 一致"; else echo "  ✗ index.html 漂移"; ok=0; fi
# vendor 关键文件抽查（HTML 按需加载的脚本/数据）
for f in vendor/app-core.js vendor/meta.js vendor/eu/eu_metrics.js vendor/world.js; do
  rel="${f#vendor/}"
  s=$(HASH "$f"); d=$(HASH "dist/vendor/$rel")
  if [ "$s" = "$d" ]; then echo "  ✓ $rel 一致"; else echo "  ✗ $rel 漂移"; ok=0; fi
done
[ "$ok" = 1 ] || { echo "dist 与 source 不一致，中止。"; exit 1; }

# 缓存失效：给 app-core.js / meta.js 的引用注入内容指纹（?v=md5前8位）——
# JS 内容变化后 URL 变化，绕过浏览器/CDN 4h 缓存。
# （meta.js 是 2026-10-12 补的：它随数据集最新年/构建日期变化，却没有指纹，
#   曾导致 atlas.huajun.wang 在部署后 4h 内仍提供旧 meta，about 新鲜度表显示过期年份。）
# 用 python3 做替换，兼容 toybox / macOS(BSD) / GNU sed 差异（toybox sed 无法正确解析 -i '' -E）
CORE_HASH=$(HASH vendor/app-core.js | cut -c1-8)
META_HASH=$(HASH vendor/meta.js | cut -c1-8)
for f in dist/global-data-atlas.html dist/index.html dist/embed.html dist/compare.html dist/about.html; do
  python3 - "$f" "$CORE_HASH" "$META_HASH" <<'PYEOF'
import sys, re
p, h, m = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(p, encoding='utf-8').read()
s = re.sub(r'src="vendor/app-core\.js(\?v=[a-f0-9]+)?"', 'src="vendor/app-core.js?v=' + h + '"', s)
s = re.sub(r'src="vendor/meta\.js(\?v=[a-f0-9]+)?"', 'src="vendor/meta.js?v=' + m + '"', s)
open(p, 'w', encoding='utf-8').write(s)
PYEOF
done
echo "  ↻ app-core.js?v=${CORE_HASH} · meta.js?v=${META_HASH}（缓存指纹已注入）"

if [ "$1" = "--deploy" ]; then
  echo "── 部署 Cloudflare Pages ──"
  # 绕过系统代理（本机代理会导致 fetch failed）
  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
    wrangler pages deploy dist --project-name=global-data-atlas --branch=main
else
  echo "dist 已同步（加 --deploy 发布上线）"
fi
