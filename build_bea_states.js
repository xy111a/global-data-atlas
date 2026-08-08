// 拉取 BEA 州级 GDP 多年序列 (SAGDP1 = 现价 GDP by state, 百万美元)
// 输出 vendor/us_states_bea.js -> window.US_TS = { "<州全名>": { years: { "2000": 1784320.6, ... } } }
// 注: BEA 不含人口, 人口/面积沿用 global-data-atlas.html 内 US_STATES_GDP 的单年值
const fs = require("fs");
// BEA API key 从环境变量读取，避免硬编码泄露到版本库。
// 使用： export BEA_KEY=你的密钥  再运行 node build_bea_states.js
const KEY = process.env.BEA_KEY;
if (!KEY) {
  console.error("ERROR: 未设置 BEA API 密钥。请先执行： export BEA_KEY=你的密钥");
  process.exit(1);
}
const OUT = "vendor/us_states_bea.js";

async function fetchBEA(tbl, line, years) {
  const url = `https://apps.bea.gov/api/data/?UserID=${KEY}&method=GetData&datasetname=Regional&TableName=${tbl}&LineCode=${line}&GeoFips=STATE&Year=${years}&ResultFormat=JSON`;
  const r = await fetch(url);
  const j = await r.json();
  const res = j.BEAAPI && j.BEAAPI.Results;
  if (!res || res.Error) throw new Error("BEA: " + (res && res.Error && res.Error.APIErrorDescription));
  return res.Data;
}

(async () => {
  console.log("拉取 BEA SAGDP1 (现价州GDP, 2000-2024, 逐年) ...");
  const out = {};
  let minY = 9999, maxY = 0;
  for (let y = 2000; y <= 2024; y++) {
    const rows = await fetchBEA("SAGDP1", 1, String(y));
    for (const r of rows) {
      const name = r.GeoName;
      const v = r.DataValue != null ? Math.round(Number(r.DataValue) * 10) / 10 : null; // 百万美元
      if (!name || v == null) continue;
      if (!out[name]) out[name] = { years: {} };
      out[name].years[String(y)] = v;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    if ((y - 2000) % 5 === 0 || y === 2024) console.log(`  ${y} 完成 (累计 ${Object.keys(out).length} 地区)`);
  }

  const names = Object.keys(out);
  console.log(`覆盖州/地区: ${names.length} 个, 年份范围: ${minY}-${maxY}`);

  // 校验
  for (const n of ["California", "New York", "District of Columbia", "Puerto Rico"]) {
    if (!out[n]) { console.log("  缺失:", n); continue; }
    const yrs = out[n].years;
    const yk = Object.keys(yrs);
    console.log(`  ${n}: ${yk.length} 年, ${yk[0]}=${yrs[yk[0]]}M$, ${yk[yk.length-1]}=${yrs[yk[yk.length-1]]}M$`);
  }

  fs.writeFileSync(OUT, "window.US_TS = " + JSON.stringify(out) + ";\n");
  console.log(`✅ 已写出 ${OUT}  (${(fs.statSync(OUT).size / 1024).toFixed(0)} KB)`);
})().catch(e => { console.error("BUILD FAILED:", e.message); process.exit(1); });
