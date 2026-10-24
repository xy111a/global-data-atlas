/* global-data-atlas 数据元信息：构建时间与各数据集最新年份
   由对应 build 脚本在重生成数据时更新 built 与各数据集 latest。
   用途：① 页脚「数据更新于」时间戳；② about.html「数据新鲜度」表格（由 ATLAS_META 渲染）。
   ⚠️ datasets[*].latest 受 tests/data_verify.py 与 tests/meta_freshness_test.py 双重断言保护：
      必须等于对应数据文件的实际最大年。
      2026-10-12 曾发现 us 写 2023（实际 2024）、japan 写 2021（实际 2022）的漂移，
      而当时 datasets 字段全仓零引用，故错误从未暴露。现已接入 about.html 并加门禁断言。
   注：键名加引号（合法 JSON），便于 data_verify / 校验脚本直接 json.loads，无需 eval。 */
window.ATLAS_META = {
  "built": "2026-10-12",
  "datasets": {
    "world": { "latest": 2024, "src": "World Bank",        "span": "2000–2024 逐年", "desc": "214 国 GDP/人口/面积 + 8 项扩展指标" },
    "china": { "latest": 2025, "src": "国家统计局 / 维基",   "span": "2000–2025 逐年", "desc": "31 省 GDP 序列（2025 初核）+ 人口 + 面积" },
    "us":    { "latest": 2024, "src": "BEA / Census",      "span": "2000–2024 逐年", "desc": "51 州 GDP 序列(至2024)；人口 2020–2025 逐年(Census PEP)" },
    "eu":    { "latest": 2024, "src": "Eurostat",          "span": "2000–2024 逐年", "desc": "27 国 242 个 NUTS2 大区 GDP 序列 + 人口 1990–2025" },
    "japan": { "latest": 2022, "src": "日本内阁府（ESRI）",  "span": "2011–2022 逐年", "desc": "47 都道府县 GDP 序列（JPY→USD 逐年）；人口 2023 / 面积单年" },
    "city":  { "latest": 2023, "src": "维基 / 公开整理",     "span": "2023 单年",      "desc": "321 地级市快照；其中 46 城另有 2009–2020 序列" }
  }
};
