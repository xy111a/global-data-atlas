#!/usr/bin/env python3
"""构建城市搜索索引 vendor/cn/city_index.js
   从省级 GeoJSON（vendor/cn/{adcode}.js, window.CN_PROV[adcode]）提取 {name, adcode, parent}
   与 CITY_METRICS 键求交，输出 window.CITY_INDEX = [[城市名, 市adcode, 省adcode, 省名], ...]
"""
import re, json, os, glob, tempfile, shutil, time

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

def main():
    # 1. 加载 CITY_METRICS 键（无名称）
    cm_src = open('vendor/cn/city_metrics.js', encoding='utf-8').read()
    cm_keys = set(re.findall(r'(\d{6}):\{', cm_src))
    print(f"CITY_METRICS 键数: {len(cm_keys)}")

    # 2. 加载所有省级 GeoJSON（window.CN_PROV[adcode] 格式）
    #    以及 100000.js 拿省名（window.CN_GEO）
    geo_src = open('vendor/cn/100000.js', encoding='utf-8').read()
    m = re.search(r'window\.CN_GEO=(\{.*\})', geo_src, re.S)
    cn_geo = json.loads(m.group(1))
    prov_name_by_adcode = {}
    for f in cn_geo['features']:
        p = f['properties']
        if p.get('level') == 'province':
            prov_name_by_adcode[str(p['adcode'])] = p['name'].replace('省', '').replace('市', '').replace('自治区', '').replace('特别行政区', '')
    print(f"省级数: {len(prov_name_by_adcode)}")

    # 3. 遍历省级 GeoJSON 收集城市 {name, adcode, parent_adcode}
    city_map = {}   # adcode -> (name, parent_adcode)
    for f in glob.glob('vendor/cn/[0-9][0-9][0-9][0-9][0-9][0-9].js'):
        adcode = os.path.basename(f)[:6]
        if adcode in ('100000', '810000', '820000'):
            continue   # 全国/港澳（港澳无 city_metrics）
        try:
            src = open(f, encoding='utf-8').read()
            mm = re.search(r"\[.']" + adcode + r"['\]]=(.*)", src, re.S)
            if not mm:
                mm = re.search(r'=\s*(\{.*\})', src, re.S)
            gj = json.loads(mm.group(1))
        except Exception as e:
            print(f"  WARN {adcode}: {e}")
            continue
        for feat in gj['features']:
            p = feat['properties']
            if p.get('level') != 'city':
                continue
            city_map[str(p['adcode'])] = (p['name'], str(p.get('parent', {}).get('adcode', '')))

    print(f"GeoJSON 城市总数: {len(city_map)}")

    # 4. 与 CITY_METRICS 求交
    index = []
    for adcode in sorted(cm_keys):
        if adcode not in city_map:
            continue
        name, parent = city_map[adcode]
        # 直辖市整体键（110000/120000/310000/500000）parent=100000，跳过（省搜索已覆盖）
        if parent == '100000':
            continue
        prov = prov_name_by_adcode.get(parent, '')
        index.append([name, int(adcode), int(parent), prov])

    print(f"索引条目: {len(index)}")

    # 5. 输出
    js = "/* 城市搜索索引（build_city_index.py 生成）：[城市名, 市adcode, 省adcode, 省名]\n"
    js += " * 来源：省级 GeoJSON（DataV）+ CITY_METRICS 求交；用于 doSearch 城市搜索 */\n"
    js += "window.CITY_INDEX = " + json.dumps(index, ensure_ascii=False, separators=(',', ':')) + ";\n"
    bak = atomic_write('vendor/cn/city_index.js', js)
    print(f"已写 vendor/cn/city_index.js ({len(js)} bytes)" + (f" · 备份 {bak}" if bak else ""))

    # 抽样验证
    for probe in ['广州', '杭州', '深圳', '成都']:
        hit = [x for x in index if probe in x[0]]
        print(f"  搜索'{probe}': {hit[:2] if hit else '无'}")

if __name__ == "__main__":
    main()
