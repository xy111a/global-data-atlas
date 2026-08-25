#!/usr/bin/env python3
"""补全 _enmap.json 国家中文名：把 139 个英文 cn 替换为标准中文译名，并统一写法。

数据源：ISO 3166 标准中文译名（外交部/新华社常用译法）。
用法：python3 patch_cn_names.py
"""
import json, re, shutil, os, tempfile, time

SRC = "_enmap.json"
OUT = "_enmap.json"

def atomic_write(path, content, backup=True):
    """写前自动备份到 /tmp；临时文件 + os.replace 原子替换；失败回滚到备份。"""
    bak = None
    if backup and os.path.exists(path):
        bak = f"/tmp/{os.path.basename(path)}.bak.{int(time.time())}"
        shutil.copy2(path, bak)
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".json")
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

# ISO2 -> 标准中文名（仅列出当前 cn 仍为英文/需修正的）
CN_FIX = {
    "AD": "安道尔", "AG": "安提瓜和巴布达", "AL": "阿尔巴尼亚", "AM": "亚美尼亚",
    "AS": "美属萨摩亚", "AW": "阿鲁巴", "AZ": "阿塞拜疆", "BA": "波斯尼亚和黑塞哥维那",
    "BB": "巴巴多斯", "BF": "布基纳法索", "BG": "保加利亚", "BH": "巴林",
    "BI": "布隆迪", "BJ": "贝宁", "BM": "百慕大", "BN": "文莱",
    "BO": "玻利维亚", "BS": "巴哈马", "BT": "不丹", "BW": "博茨瓦纳",
    "BY": "白俄罗斯", "BZ": "伯利兹", "CF": "中非共和国", "CG": "刚果（布）",
    "CI": "科特迪瓦", "CM": "喀麦隆", "CR": "哥斯达黎加", "CV": "佛得角",
    "CY": "塞浦路斯", "DJ": "吉布提", "DM": "多米尼克", "DO": "多米尼加共和国",
    "EC": "厄瓜多尔", "EE": "爱沙尼亚", "ER": "厄立特里亚", "FJ": "斐济",
    "FM": "密克罗尼西亚联邦", "FO": "法罗群岛", "GA": "加蓬", "GD": "格林纳达",
    "GE": "格鲁吉亚", "GH": "加纳", "GL": "格陵兰", "GM": "冈比亚",
    "GN": "几内亚", "GQ": "赤道几内亚", "GT": "危地马拉", "GU": "关岛",
    "GW": "几内亚比绍", "GY": "圭亚那", "HN": "洪都拉斯", "HR": "克罗地亚",
    "HT": "海地", "IM": "马恩岛", "IS": "冰岛", "JM": "牙买加",
    "JO": "约旦", "KG": "吉尔吉斯斯坦", "KH": "柬埔寨", "KI": "基里巴斯",
    "KM": "科摩罗", "KN": "圣基茨和尼维斯", "KP": "朝鲜", "KY": "开曼群岛",
    "LA": "老挝", "LB": "黎巴嫩", "LC": "圣卢西亚", "LI": "列支敦士登",
    "LK": "斯里兰卡", "LR": "利比里亚", "LS": "莱索托", "LT": "立陶宛",
    "LU": "卢森堡", "LV": "拉脱维亚", "LY": "利比亚", "MC": "摩纳哥",
    "MD": "摩尔多瓦", "ME": "黑山", "MG": "马达加斯加", "MH": "马绍尔群岛",
    "MK": "北马其顿", "ML": "马里", "MN": "蒙古", "MO": "中国澳门",
    "MP": "北马里亚纳群岛", "MR": "毛里塔尼亚", "MT": "马耳他", "MU": "毛里求斯",
    "MV": "马尔代夫", "MW": "马拉维", "MZ": "莫桑比克", "NA": "纳米比亚",
    "NC": "新喀里多尼亚", "NE": "尼日尔", "NI": "尼加拉瓜", "NP": "尼泊尔",
    "NR": "瑙鲁", "OM": "阿曼", "PA": "巴拿马", "PF": "法属波利尼西亚",
    "PG": "巴布亚新几内亚", "PR": "波多黎各", "PW": "帕劳", "PY": "巴拉圭",
    "RS": "塞尔维亚", "RW": "卢旺达", "SB": "所罗门群岛", "SC": "塞舌尔",
    "SI": "斯洛文尼亚", "SL": "塞拉利昂", "SM": "圣马力诺", "SN": "塞内加尔",
    "SO": "索马里", "SR": "苏里南", "SS": "南苏丹", "ST": "圣多美和普林西比",
    "SV": "萨尔瓦多", "SY": "叙利亚", "SZ": "斯威士兰", "TC": "特克斯和凯科斯群岛",
    "TD": "乍得", "TG": "多哥", "TJ": "塔吉克斯坦", "TL": "东帝汶",
    "TM": "土库曼斯坦", "TN": "突尼斯", "TO": "汤加", "TT": "特立尼达和多巴哥",
    "TV": "图瓦卢", "UY": "乌拉圭", "UZ": "乌兹别克斯坦", "VC": "圣文森特和格林纳丁斯",
    "VG": "英属维尔京群岛", "VI": "美属维尔京群岛", "VU": "瓦努阿图",
    "WS": "萨摩亚", "XK": "科索沃", "ZM": "赞比亚", "ZW": "津巴布韦",
    # 已有中文但写法需统一
    "HK": "中国香港", "CD": "刚果（金）", "TZ": "坦桑尼亚", "MM": "缅甸",
    "SD": "苏丹", "UG": "乌干达", "AF": "阿富汗", "YE": "也门", "AO": "安哥拉",
}

def has_cn(s):
    return any('\u4e00' <= c <= '\u9fff' for c in s)

def main():
    emap = json.load(open(SRC, encoding="utf-8"))
    fixed, skipped = [], []
    for iso, v in emap.items():
        if iso in CN_FIX:
            old = v.get("cn", "")
            v["cn"] = CN_FIX[iso]
            fixed.append((iso, old, CN_FIX[iso]))
        elif not has_cn(v.get("cn", "")):
            skipped.append((iso, v.get("en"), v.get("cn")))
    atomic_write(OUT, json.dumps(emap, ensure_ascii=False, indent=2))
    print(f"✅ 修正 {len(fixed)} 个中文名")
    for iso, old, new in fixed:
        print(f"  {iso}: {old!r} -> {new!r}")
    if skipped:
        print(f"⚠️ 仍有 {len(skipped)} 个未覆盖（需手工补充）:")
        for iso, en, cn in skipped:
            print(f"  {iso} en={en!r} cn={cn!r}")

if __name__ == "__main__":
    main()
