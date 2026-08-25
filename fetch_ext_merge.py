#!/usr/bin/env python3
"""拉取 3 个新指标（unemp/internet/military）追加进 vendor/ext_indicators.js
   读现有 EXT（iso2 键）→ 新数据按 iso2 追加 → 写回，不破坏旧 8 指标。

   安全加固（P2-9）：写入前自动备份到 /tmp，临时文件 + os.replace 原子替换，失败回滚。"""
import json, urllib.request, time, re, os, tempfile, shutil

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
        os.replace(tmp, path)
        tmp = None
    except Exception:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
        if backup and os.path.exists(path):
            shutil.copy2(backup, path)
        raise
    finally:
        if tmp and os.path.exists(tmp):
            try: os.remove(tmp)
            except OSError: pass
    return backup

NEW = {"unemp": "SL.UEM.TOTL.ZS", "internet": "IT.NET.USER.ZS", "military": "MS.MIL.XPND.GD.ZS"}

def main():
    # 读现有 EXT
    old_src = open('vendor/ext_indicators.js', encoding='utf-8').read()
    EXT = json.loads(re.search(r'window\.EXT\s*=\s*(\{[\s\S]*\})', old_src).group(1))
    print(f"现有 EXT: {len(EXT)} 国")

    # iso3→iso2 映射（WB 国家列表）
    cc_map = {}
    try:
        d = fetch("https://api.worldbank.org/v2/country?format=json&per_page=400")
        for c in d[1]:
            if c.get('iso2Code') and c.get('id') and len(c['id']) == 3:
                cc_map[c['id']] = c['iso2Code']
    except Exception as e:
        print("映射失败:", e)
    print(f"iso3→iso2 映射: {len(cc_map)}")

    # 拉新指标（按 iso2 直接存）
    for name, code in NEW.items():
        got = 0
        # 需要 iso2 列表 → 用 cc_map 反查
        iso2s = sorted(set(cc_map.values()))
        for bi, batch in enumerate([iso2s[i:i+40] for i in range(0, len(iso2s), 40)]):
            cc = ";".join(b.lower() for b in batch)
            try:
                d = fetch(f"https://api.worldbank.org/v2/country/{cc}/indicator/{code}?format=json&per_page=1000&date=2000:2024")
                rows = d[1] if isinstance(d, list) and len(d) > 1 else []
            except Exception as e:
                print(f"  {name} 批{bi} 失败: {e}")
                continue
            for r in rows:
                iso3 = r.get('countryiso3code')
                if not iso3 or r.get('value') is None:
                    continue
                iso2 = cc_map.get(iso3)
                if not iso2:
                    continue
                EXT.setdefault(iso2, {}).setdefault(name, {})[r['date']] = r['value']
                got += 1
        print(f"  {name}: {got} 条")
        time.sleep(2)

    # 清理 None + 空指标
    final = {}
    for iso2, mets in EXT.items():
        cleaned = {k: {y: v for y, v in mv.items() if v is not None} for k, mv in mets.items() if mv}
        if cleaned:
            final[iso2] = cleaned

    js = "/* 扩展指标（World Bank）：trade贸易占GDP% / health医疗支出占GDP% / edu教育支出占GDP% / life预期寿命 / gdpcap人均GDP(2015不变价USD) / unemp失业率% / internet互联网普及率% / military军费占GDP% */\n"
    js += "window.EXT = " + json.dumps(final, ensure_ascii=False, separators=(',', ':')) + ";\n"
    backup = atomic_write('vendor/ext_indicators.js', js)
    print(f"已写 vendor/ext_indicators.js ({len(js)} bytes, {len(final)} 国)")
    if backup:
        print(f"自动备份: {backup}")

    # 验证 CN
    cn = final.get('CN', {})
    print("CN 指标:", {k: len(v) for k, v in cn.items()})

if __name__ == "__main__":
    main()
