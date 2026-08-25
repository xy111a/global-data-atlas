#!/usr/bin/env python3
"""拉取 World Bank 新维度数据（国家层 2000-2024），生成 vendor/ext_indicators.js
   指标：trade(贸易占GDP%) / health(医疗支出占GDP%) / edu(教育支出占GDP%) /
         life(预期寿命岁) / gdpcap(人均GDP 2015不变价 USD)
   输出结构 window.EXT = { [iso2]: { [metric]: { [year]: value } } }

   安全加固（P2-9）：
   - 解析 countries_wb.js 改用 json.loads（不再 eval）
   - 写入 vendor/ext_indicators.js 前自动备份到 /tmp，并用临时文件 + os.replace 原子替换
   - 任一步骤失败回滚到备份，避免“一键跑坏数据”"""
import json, urllib.request, time, os, re, tempfile, shutil

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(3)

# 指标代码
IND = {
    "trade":  "NE.TRD.GNFS.ZS",    # 贸易占GDP %
    "health": "SH.XPD.CHEX.GD.ZS", # 医疗支出占GDP %
    "edu":    "SE.XPD.TOTL.GD.ZS", # 教育支出占GDP %
    "life":   "SP.DYN.LE00.IN",    # 预期寿命
    "gdpcap": "NY.GDP.PCAP.KD",    # 人均GDP 2015不变价USD
    "unemp":  "SL.UEM.TOTL.ZS",    # 失业率%（Phase F2）
    "internet":"IT.NET.USER.ZS",   # 互联网普及率%（Phase F2）
    "military":"MS.MIL.XPND.GD.ZS",# 军费占GDP%（Phase F2）
}

def parse_wb(src):
    """稳健解析 countries_wb.js 的 window.WB（双引号 JSON，json.loads 直读，不 eval）"""
    m = re.search(r'window\.WB\s*=\s*(\{[\s\S]*\})', src)
    if not m:
        raise RuntimeError("countries_wb.js 未找到 window.WB 定义")
    return json.loads(m.group(1))

def atomic_write(path, content):
    """写前自动备份到 /tmp；临时文件 + os.replace 原子替换；失败回滚到备份。"""
    backup = None
    if os.path.exists(path):
        ts = time.strftime("%Y%m%d-%H%M%S")
        backup = f"/tmp/ext_indicators.js.bak.{ts}"
        shutil.copy2(path, backup)
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)),
                                   prefix=".ext_", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)   # 原子替换（POSIX 保证）
        tmp = None
    except Exception:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
        if backup and os.path.exists(path):
            shutil.copy2(backup, path)   # 回滚
        raise
    finally:
        if tmp and os.path.exists(tmp):
            try: os.remove(tmp)
            except OSError: pass
    return backup

def main():
    # 从 countries_wb.js 读国家 iso2 列表
    src = open('vendor/countries_wb.js', encoding='utf-8').read()
    WB = parse_wb(src)
    iso2s = sorted(WB.keys())
    print(f"国家数: {len(iso2s)}")

    out = {}
    total = len(IND)
    for mi, (name, code) in enumerate(IND.items(), 1):
        # 每次请求 32 国，分批（WB API per_page 上限）
        batches = [iso2s[i:i+32] for i in range(0, len(iso2s), 32)]
        got = 0
        for bi, batch in enumerate(batches):
            cc = ";".join(batch)
            url = f"https://api.worldbank.org/v2/country/{cc}/indicator/{code}?format=json&per_page=1000&date=2000:2024"
            try:
                d = fetch(url)
                rows = d[1] if isinstance(d, list) and len(d) > 1 else []
            except Exception as e:
                print(f"  {name} 批次{bi} 失败: {e}")
                continue
            for r in rows:
                iso = r.get('countryiso3code') or (r.get('country') or {}).get('id')
                # WB 返回 iso3，需要映射。先用 country.id（可能是 ISO3）
                if not iso:
                    continue
                # 存临时：iso3 -> val
                out.setdefault(iso, {}).setdefault(name, {})[r['date']] = r.get('value')
            got += len(rows)
        print(f"[{mi}/{total}] {name} ({code}): {got} 条")
        time.sleep(1)

    # 需要 iso3 -> iso2 映射：从 WB 的国家列表获取
    print("获取 ISO3→ISO2 映射...")
    cc_map = {}
    try:
        d = fetch("https://api.worldbank.org/v2/country?format=json&per_page=400")
        for c in d[1]:
            if c.get('iso2Code') and c.get('id') and len(c['id']) == 3:
                cc_map[c['id']] = c['iso2Code']
    except Exception as e:
        print("映射获取失败:", e)

    # 重组为 iso2 键
    final = {}
    for iso3, mets in out.items():
        iso2 = cc_map.get(iso3, iso3)
        final[iso2] = {k: {y: v for y, v in mv.items() if v is not None}
                       for k, mv in mets.items()}
    # 只保留有数据的
    final = {k: v for k, v in final.items() if v}
    print(f"有数据国家: {len(final)}")

    js = "/* 扩展指标（World Bank）：trade贸易占GDP% / health医疗支出占GDP% / edu教育支出占GDP% / life预期寿命 / gdpcap人均GDP(2015不变价USD) */\n"
    js += "window.EXT = " + json.dumps(final, ensure_ascii=False, separators=(',', ':')) + ";\n"
    backup = atomic_write('vendor/ext_indicators.js', js)
    print(f"已写入 vendor/ext_indicators.js ({os.path.getsize('vendor/ext_indicators.js')} bytes)")
    if backup:
        print(f"自动备份: {backup}")

if __name__ == "__main__":
    main()
