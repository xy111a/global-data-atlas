/* build_countries_multi.js
 * 从 World Bank API 拉取全量国家 GDP(当期USD$) / 人口 / 面积 的【多年度序列】，
 * 匹配 ECharts world.json 边界名，输出：
 *   vendor/countries_wb.js  ->  window.WB = { "<iso2>": {cn,en,iso2,lng,lat,years:{yyyy:{gdp,pop,area}}} }
 * 货币折算(CNY) 留给 HTML 运行时 (USD->CNY x7.2)，故文件内 GDP 仍为美元。
 *
 * 注意：本脚本只产出数据文件，不修改 global-data-atlas.html（HTML 由手动/脚本二次编辑）。
 */
const fs = require("fs");
const path = require("path");

const ROOT = __dirname;
const HTML = path.join(ROOT, "global-data-atlas.html");
const WORLD = path.join(ROOT, "vendor", "world.json");
const OUT_JS = path.join(ROOT, "vendor", "countries_wb.js");

const API = "https://api.worldbank.org/v2";
const YEAR_RANGE = "2000:2024";

// World Bank 国家名 -> ECharts world.json 名称 归一化（与旧 build 保持一致）
const NORMALIZE = {
  "Korea, Rep.": "Korea", "Egypt, Arab Rep.": "Egypt", "Iran, Islamic Rep.": "Iran",
  "Venezuela, RB": "Venezuela", "Yemen, Rep.": "Yemen", "Gambia, The": "Gambia",
  "Bahamas, The": "Bahamas", "Kyrgyz Republic": "Kyrgyzstan", "Lao PDR": "Laos",
  "Congo, Dem. Rep.": "Dem. Rep. Congo", "Congo, Rep.": "Congo", "Czechia": "Czech Rep.",
  "Slovak Republic": "Slovakia", "Syrian Arab Republic": "Syria", "Côte d'Ivoire": "Ivory Coast",
  "Cabo Verde": "Cape Verde", "Eswatini": "Swaziland", "Timor-Leste": "East Timor",
  "Brunei Darussalam": "Brunei", "Hong Kong SAR, China": "Hong Kong", "Macao SAR, China": "Macau",
  "Taiwan, China": "Taiwan"
};
function stripSuffix(n) {
  return n
    .replace(/, The$/, "").replace(/, Rep\.$/, "").replace(/, RB$/, "")
    .replace(/, Arab Rep\.$/, "").replace(/, Islamic Rep\.$/, "").replace(/, Dem\. Rep\.$/, "")
    .replace(/, Fed\. Sts\.$/, "").replace(/, P\. Rep\.$/, "").replace(/, D\. P\. R\.$/, "")
    .trim();
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function getJSON(url) {
  for (let attempt = 1; attempt <= 4; attempt++) {
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error("HTTP " + r.status);
      const j = await r.json();
      return j;
    } catch (e) {
      if (attempt === 4) throw e;
      await sleep(900 * attempt);
    }
  }
}
// 取某指标全量（分页），返回 iso3 -> { year: value }（保留所有年份）
async function fetchIndicator(indicator) {
  const map = {};
  let page = 1, pages = 1;
  while (page <= pages) {
    const url = `${API}/country/all/indicator/${indicator}?format=json&date=${YEAR_RANGE}&per_page=1000&page=${page}`;
    const j = await getJSON(url);
    if (!Array.isArray(j) || !j[1]) break;
    if (page === 1) pages = j[0].pages || 1;
    for (const row of j[1]) {
      const iso3 = row.countryiso3code || row.country.id;
      if (!iso3) continue;
      const v = row.value;
      if (v == null) continue;
      const yr = parseInt(row.date, 10);
      (map[iso3] = map[iso3] || {})[yr] = v;
    }
    page++;
    await sleep(350); // 礼貌限速，避免 429
  }
  return map;
}

(async () => {
  // 1) 国家列表
  const cl = await getJSON(`${API}/country?format=json&per_page=400`);
  const countries = cl[1].filter((c) => c.region && c.region.value !== "Aggregates");
  console.log(`国家列表: ${countries.length} 个（已过滤 Aggregates）`);

  // 2) 三项指标（多年度）
  console.log("拉取 GDP ...");
  const gdp = await fetchIndicator("NY.GDP.MKTP.CD");
  console.log("拉取 人口 ...");
  const pop = await fetchIndicator("SP.POP.TOTL");
  console.log("拉取 面积(地表) ...");
  const area = await fetchIndicator("AG.SRF.TOTL.K2");
  console.log("拉取 不变价GDP(2015基, 美元) ...");
  const gdpKd = await fetchIndicator("NY.GDP.MKTP.KD");
  console.log("拉取 PPP不变价GDP(2017基, 国际元) ...");
  const gdpPpKd = await fetchIndicator("NY.GDP.MKTP.PP.KD");
  console.log("拉取 USD/CNY 年均汇率 ...");
  const fx = await fetchIndicator("PA.NUS.FCRF");
  console.log(`GDP: ${Object.keys(gdp).length} / 人口: ${Object.keys(pop).length} / 面积: ${Object.keys(area).length} / KD: ${Object.keys(gdpKd).length} / PP.KD: ${Object.keys(gdpPpKd).length} / 汇率iso3: ${Object.keys(fx).length} 有数据`);

  // 3) world.json 名称集合
  const wj = JSON.parse(fs.readFileSync(WORLD, "utf8"));
  const wjNames = new Set(wj.features.map((f) => f.properties.name));

  // 4) 复用 dist 旧版对齐的国名映射（cn/en 按 iso2），不再依赖 HTML 内联数组
  const ENMAP = JSON.parse(fs.readFileSync(path.join(ROOT, "_enmap.json"), "utf8"));
  const cnByIso2 = {}, enByIso2 = {};
  for (const k in ENMAP) {
    if (ENMAP[k].cn) cnByIso2[k] = ENMAP[k].cn;
    if (ENMAP[k].en) enByIso2[k] = ENMAP[k].en;
  }
  console.log(`国名映射: cn ${Object.keys(cnByIso2).length} / en ${Object.keys(enByIso2).length} 个`);

  // 5) 组装 window.WB
  const out = {};
  const unmatched = [];
  for (const c of countries) {
    const iso3 = c.id, iso2 = c.iso2Code;
    const lng = parseFloat(c.longitude), lat = parseFloat(c.latitude);
    if (isNaN(lng) || isNaN(lat)) continue;
    const g = gdp[iso3] || {}, p = pop[iso3] || {}, a = area[iso3] || {};
    const gk = gdpKd[iso3] || {}, gp = gdpPpKd[iso3] || {};
    if (!Object.keys(g).length && !Object.keys(p).length && !Object.keys(a).length) continue;
    const yrs = new Set([...Object.keys(g), ...Object.keys(p), ...Object.keys(a), ...Object.keys(gk), ...Object.keys(gp)].map(Number));
    if (!yrs.size) continue;
    const years = {};
    for (const y of yrs) {
      const gv = g[y], pv = p[y], av = a[y], kv = gk[y], ppv = gp[y];
      if (gv == null && pv == null && av == null && kv == null && ppv == null) continue;
      years[y] = {
        gdp: gv != null ? Math.round(gv) : null,
        pop: pv != null ? Math.round(pv) : null,
        area: av != null ? Math.round(av) : null,
        // 不变价序列存「十亿美元」以压缩体积；比率计算不受缩放影响
        gdpKd: kv != null ? Math.round(kv / 1e8) / 10 : null,
        gdpPpKd: ppv != null ? Math.round(ppv / 1e8) / 10 : null
      };
    }
    if (!Object.keys(years).length) continue;
    // 匹配 world.json 名称
    let wname = NORMALIZE[c.name] || null;
    if (!wname || !wjNames.has(wname)) {
      const cand = [c.name, stripSuffix(c.name), stripSuffix(c.name) + "s", stripSuffix(c.name).replace(/y$/, "ia")];
      wname = cand.find((x) => wjNames.has(x)) || null;
    }
    if (!wname && !enByIso2[iso2]) unmatched.push(c.name);
    // 优先使用现有 COUNTRIES 中已校对、与 world.json 对齐的 en 名称，避免破坏地图匹配
    const EN_FIX = { "HK": "Hong Kong", "MO": "Macau", "KP": "Dem. Rep. Korea", "SO": "Somalia" };
    const en = EN_FIX[iso2] || enByIso2[iso2] || wname || c.name;
    const cn = cnByIso2[iso2] || c.name;
    out[iso2] = { cn, en, iso2, lng, lat, years };
  }
  console.log(`组装完成: ${Object.keys(out).length} 个国家; 未匹配 world.json 边界: ${unmatched.length}`);
  if (unmatched.length) console.log("未匹配名单:", unmatched.join(", "));

  // 6) 输出 JS（window.WB）
  fs.writeFileSync(OUT_JS, "window.WB = " + JSON.stringify(out) + ";\n");
  console.log(`✅ 已写出 ${OUT_JS}  (${(fs.statSync(OUT_JS).size / 1024).toFixed(0)} KB)`);

  // 6.5) 输出逐年汇率 window.FXRATE（China 年均汇率 元/美元，与 WB GDP 口径自洽）
  const fxCHN = fx["CHN"] || {};
  const fxOut = {};
  for (const y in fxCHN) if (fxCHN[y] != null) fxOut[y] = Math.round(fxCHN[y] * 1e4) / 1e4;
  const FX_JS = path.join(ROOT, "vendor", "fxrate.js");
  fs.writeFileSync(FX_JS, "window.FXRATE = " + JSON.stringify(fxOut) + ";\n");
  console.log(`✅ 已写出 ${FX_JS}  (${Object.keys(fxOut).length} 年汇率)`);
})().catch((e) => {
  console.error("BUILD FAILED:", e);
  process.exit(1);
});
