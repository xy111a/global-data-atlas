/* global-data-atlas 数据元信息：构建时间与各数据集最新年份
   由对应 build 脚本在重生成数据时更新 built 与各数据集 latest。
   仅用于页面展示（footer 时间戳 / 数据新鲜度提示），不影响计算逻辑。 */
window.ATLAS_META = {
  built: "2026-10-11",
  datasets: {
    world: { latest: 2024, src: "World Bank" },
    china: { latest: 2025, src: "国家统计局 / 维基" },
    us:    { latest: 2023, src: "BEA" },
    eu:    { latest: 2024, src: "Eurostat" },
    japan: { latest: 2021, src: "日本内阁府" },
    city:  { latest: 2023, src: "维基" }
  }
};
