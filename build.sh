#!/bin/bash
# 构建+部署门禁：source → dist 同步 → md5 校验 → （可选）Cloudflare Pages 部署
# 用法:
#   ./build.sh           # 只同步 dist 并校验（防漂移门禁）
#   ./build.sh --deploy  # 同步 + 校验 + 部署上线
set -e
cd "$(dirname "$0")"

# 可移植 md5（macOS /sbin/md5、Linux md5sum、通用 openssl）
# ⚠️ 2026-10-12：原兜底用 shasum -a 1（SHA1），当构建机既无 md5 也无 md5sum 时，
#   ?v= 会变成 sha1 前 8 位而非 md5（实测 dist 引用 app-core.js?v=2314f7a7 即 sha1[:8]），
#   跨机算法漂移。改为优先 openssl dgst -md5，保证 ?v 恒为 md5；shasum 仅作最后兜底。
if command -v md5 >/dev/null 2>&1; then
  HASH() { md5 -q "$1"; }
elif command -v md5sum >/dev/null 2>&1; then
  HASH() { md5sum "$1" | awk '{print $1}'; }
elif command -v openssl >/dev/null 2>&1; then
  HASH() { openssl dgst -md5 "$1" 2>/dev/null | awk '{print $NF}'; }
else
  HASH() { shasum -a 1 "$1" | awk '{print $1}'; }
fi

echo "── 同步 source → dist ──"
for f in global-data-atlas.html compare.html about.html 404.html robots.txt sitemap.xml favicon.svg favicon.ico _headers sw.js og-image.png og-image.jpg; do
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
for f in global-data-atlas.html compare.html about.html 404.html robots.txt sitemap.xml favicon.svg favicon.ico _headers sw.js og-image.png og-image.jpg; do
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

# 动态资源指纹清单（#4, 2026-10-12）：walk dist/vendor 全部 .js → md5[:8]，把 window.VHASH 内联
# 注入引用了 app-core 的页面。loadScript()/loadCnProvGeo() 运行时按「原始路径」查表注 ?v，
# 覆盖静态 <script src> 之外的动态拼接路径（ext_indicators / japan / us-states / cn·eu 边界等），
# 使这些文件内容刷新后也能即时到达用户（此前只能靠 _headers max-age=0 回源兜底）。
python3 - <<'PYEOF'
import os, json, hashlib
def h8(p): return hashlib.md5(open(p, 'rb').read()).hexdigest()[:8]
vhash = {}
for root, _, files in os.walk('dist/vendor'):
    for fn in files:
        if fn.endswith('.js'):
            full = os.path.join(root, fn)
            vhash[full[len('dist/'):] if full.startswith('dist/') else full] = h8(full)   # 键形如 vendor/eu/de.js
blob = "<script>window.VHASH=" + json.dumps(vhash, separators=(',', ':'), ensure_ascii=False) + ";</script>"
targets = ["dist/global-data-atlas.html", "dist/index.html", "dist/embed.html", "dist/compare.html", "dist/about.html"]
marker = 'src="vendor/app-core.js'
n = 0
for p in targets:
    if not os.path.exists(p):
        continue
    s = open(p, encoding='utf-8').read()
    if 'window.VHASH=' in s:          # 幂等（dist 每次从源码重 cp，正常不命中）
        continue
    i = s.find(marker)
    if i == -1:
        continue
    j = s.rfind('<script', 0, i)      # 定位该 <script> 标签起始，插到它前面
    if j == -1:
        j = i
    open(p, 'w', encoding='utf-8').write(s[:j] + blob + s[j:])
    n += 1
print("  ↻ 已内联 window.VHASH（%d 个动态资源指纹）于 %d 个页面" % (len(vhash), n))
PYEOF

# 缓存失效（A2, 2026-10-12）：给所有「静态 <script src=vendor/*.js>」引用注入 ?v=<md5前8位>。
# 内容变→URL变→同时绕过 浏览器强缓存 / CDN(_headers max-age) / Service Worker(cache-first 键含 ?query)。
# 用 Python hashlib.md5：跨机确定，顺带根治 build 机缺 md5/md5sum 时 ?v 落到 sha1 的漂移（P3）。
# 动态 loadScript() 拼接的资源(如 vendor/eu/<cc>.js)无法静态改写 → 靠 _headers 的 max-age=0 强制回源兜底。
# 旧实现只给 app-core/meta 注指纹，导致数据文件刷新后靠 URL 恒定滞留边缘缓存（本次审计 P1/P2 根因）。
python3 - <<'PYEOF'
import re, os, hashlib
def h8(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()[:8]
targets = ["dist/global-data-atlas.html", "dist/index.html", "dist/embed.html",
           "dist/compare.html", "dist/about.html"]
pat = re.compile(r'src="(vendor/[^"?\s]+\.js)"')   # 仅匹配未带 ?query 的静态引用；dist 每次从源码重 cp，无历史 ?v → 幂等
changed = 0
for p in targets:
    if not os.path.exists(p):
        continue
    s = open(p, encoding='utf-8').read()
    def repl(m):
        rel = m.group(1)
        fp = os.path.join("dist", rel)
        if not os.path.exists(fp):
            return m.group(0)                       # 文件不存在则原样保留，不误伤
        return 'src="%s?v=%s"' % (rel, h8(fp))
    new = pat.sub(repl, s)
    if new != s:
        open(p, 'w', encoding='utf-8').write(new)
        changed += 1
print("  ↻ 已给 %d 个 dist HTML 的全部静态 vendor 引用注入 ?v 指纹" % changed)
PYEOF

if [ "$1" = "--deploy" ]; then
  echo "── 部署 Cloudflare Pages ──"
  # 绕过系统代理（本机代理会导致 fetch failed）
  env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy -u ALL_PROXY -u all_proxy \
    wrangler pages deploy dist --project-name=global-data-atlas --branch=main
else
  echo "dist 已同步（加 --deploy 发布上线）"
fi
