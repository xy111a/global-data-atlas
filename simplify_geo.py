#!/usr/bin/env python3
"""将地理边界文件（FeatureCollection）的坐标精度从 15 位有效数字降到 4 位小数（≈11m）。
   仅四舍五入 coordinates / center / centroid 内的浮点，其余数值（id/adcode 等）原样保留。
   保留文件前缀（window.X_GEO = 或 (window.CN_PROV||{})['ad'] = ）与编码（UTF-8 中文名）。
   用法：
     python3 simplify_geo.py            # 处理全部 vendor 下 FeatureCollection 文件
     python3 simplify_geo.py vendor/world.js   # 仅处理指定文件
   安全性：先用 git 管理，可 git checkout 还原。
"""
import json, glob, os, sys, tempfile, shutil, time

TARGET_KEYS = ("coordinates", "center", "centroid")

def atomic_write(path, content, backup=True):
    """写前自动备份到 /tmp；临时文件 + os.replace 原子替换；失败回滚到备份。"""
    bak = None
    if backup and os.path.exists(path):
        bak = f"/tmp/{os.path.basename(path)}.bak.{int(time.time())}"
        shutil.copy2(path, bak)
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".js")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        if bak and os.path.exists(path):
            shutil.copy2(bak, path)
        raise
    return bak

def round_num(x):
    if isinstance(x, bool):
        return x
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, int):
        return x
    return x

def round_coords(value):
    """递归：对 list 中所有浮点四舍五入；dict 仅对 TARGET_KEYS 递归处理内部坐标。"""
    if isinstance(value, list):
        return [round_coords(e) for e in value]
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in TARGET_KEYS:
                out[k] = _round_all(v)
            else:
                out[k] = round_coords(v)
        return out
    return value

def _round_all(x):
    if isinstance(x, list):
        return [_round_all(e) for e in x]
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, int):
        return x
    return x

def process(path):
    raw = open(path, encoding="utf-8").read()
    # 定位 FeatureCollection 对象的起始花括号：从 "type":"FeatureCollection" 向左找最外层 {
    marker = '"type":"FeatureCollection"'
    ti = raw.find(marker)
    if ti < 0:
        return None, "非 FeatureCollection"
    # 向左扫描找到该对象的最外层 {
    depth = 0
    i = -1
    k = ti
    while k >= 0:
        if raw[k] == "}":
            depth += 1
        elif raw[k] == "{":
            if depth == 0:
                i = k
                break
            depth -= 1
        k -= 1
    if i < 0:
        return None, "未找到对象起点"
    # 从该 { 向右扫描匹配 }
    depth = 0
    end = -1
    for j in range(i, len(raw)):
        if raw[j] == "{":
            depth += 1
        elif raw[j] == "}":
            depth -= 1
            if depth == 0:
                end = j + 1
                break
    if end < 0:
        return None, "括号不匹配"
    prefix = raw[:i]
    json_str = raw[i:end]
    trailing = raw[end:]
    # 解析
    try:
        obj = json.loads(json_str)
    except Exception as e:
        return None, f"JSON 解析失败: {e}"
    obj = round_coords(obj)
    new_json = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    out = prefix + new_json + ";" + ("\n" if "\n" in trailing else "")
    before = len(raw.encode("utf-8"))
    after = len(out.encode("utf-8"))
    atomic_write(path, out)
    return (before, after), None

def main():
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = []
        for pat in ("vendor/*.js", "vendor/eu/*.js", "vendor/cn/*.js"):
            files += glob.glob(pat)
    total_b = total_a = 0
    ok = 0
    for fp in sorted(files):
        if not os.path.isfile(fp):
            continue
        try:
            r = open(fp, encoding="utf-8").read()
        except Exception:
            continue
        if "FeatureCollection" not in r:
            continue
        res, err = process(fp)
        if res is None:
            print(f"⚠️ 跳过 {fp}: {err}")
            continue
        b, a = res
        total_b += b; total_a += a
        ok += 1
        print(f"✅ {fp}: {b//1024}KB → {a//1024}KB  (-{100*(1-a/b):.1f}%)")
    print(f"\n处理 {ok} 个文件：{total_b//1024}KB → {total_a//1024}KB，共省 {(total_b-total_a)//1024}KB ({100*(1-total_a/total_b):.1f}%)")

if __name__ == "__main__":
    main()
