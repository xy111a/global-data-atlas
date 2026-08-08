#!/usr/bin/env python3
"""日本都道府县边界转换：japan.geojson → vendor/japan.js
   输出 window.JP_GEO = FeatureCollection（features 的 properties.name 改为中文名）
   中文名映射：日文常用汉字与中文一致，仅少数不同（県→县、東京→东京、大阪→大阪、神奈川→神奈川等）
"""
import json, re

# 日文→中文映射（47 都道府县）
NAME_MAP = {
    "北海道": "北海道", "青森県": "青森县", "岩手県": "岩手县", "宮城県": "宫城县",
    "秋田県": "秋田县", "山形県": "山形县", "福島県": "福岛县", "茨城県": "茨城县",
    "栃木県": "栃木县", "群馬県": "群马县", "埼玉県": "埼玉县", "千葉県": "千叶县",
    "東京都": "东京都", "神奈川県": "神奈川县", "新潟県": "新潟县", "富山県": "富山县",
    "石川県": "石川县", "福井県": "福井县", "山梨県": "山梨县", "長野県": "长野县",
    "岐阜県": "岐阜县", "静岡県": "静冈县", "愛知県": "爱知县", "三重県": "三重县",
    "滋賀県": "滋贺县", "京都府": "京都府", "大阪府": "大阪府", "兵庫県": "兵库县",
    "奈良県": "奈良县", "和歌山県": "和歌山县", "鳥取県": "鸟取县", "島根県": "岛根县",
    "岡山県": "冈山县", "広島県": "广岛县", "山口県": "山口县", "徳島県": "德岛县",
    "香川県": "香川县", "愛媛県": "爱媛县", "高知県": "高知县", "福岡県": "福冈县",
    "佐賀県": "佐贺县", "長崎県": "长崎县", "熊本県": "熊本县", "大分県": "大分县",
    "宮崎県": "宫崎县", "鹿児島県": "鹿儿岛县", "沖縄県": "冲绳县",
}

def main():
    gj = json.load(open('/tmp/japan.geojson', encoding='utf-8'))
    print(f"features: {len(gj['features'])}")

    # 改名 + 存 id
    mapped = 0
    for f in gj['features']:
        p = f['properties']
        ja = p.get('nam_ja', '')
        p['name'] = NAME_MAP.get(ja, ja)
        p['name_ja'] = ja
        p['jp_id'] = p.get('id')
        if ja in NAME_MAP:
            mapped += 1
    print(f"中文名映射: {mapped}/47")

    # 输出 vendor/japan.js
    js = "/* 日本都道府县边界（dataofjapan/land, 47 县，properties.name 为中文名） */\n"
    js += "window.JP_GEO = " + json.dumps(gj, ensure_ascii=False, separators=(',', ':')) + ";\n"
    with open('vendor/japan.js', 'w', encoding='utf-8') as f:
        f.write(js)
    print(f"已写 vendor/japan.js ({len(js)/1024:.0f} KB)")

    # 抽查
    for f in gj['features'][:5]:
        p = f['properties']
        print(f"  {p['jp_id']}: {p['name']} ({p['name_ja']})")

if __name__ == "__main__":
    main()
