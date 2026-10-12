/* 增长口径一致性门禁（L2b）· 真断言，失败即非 0 退出
 *
 * 背景（2026-10-12 发现的 P0）：EU NUTS2 / 中国省级 / 中国城市 三层的
 * `reg.growth()` 此前直接在「源数据币种」上计算增长，而页面展示的是 USD。
 * 源币种与展示币种之间的逐年汇率变动，会让"同屏显示的 USD 数值"与
 * "增长百分比"互不吻合：
 *   - 中国省级 31/31 区域偏差，中位 232pp、最大 383pp（西藏 2000→2025：
 *     CNY 口径 2450% vs USD 口径 2833%）
 *   - EU NUTS2 237/237 区域偏差，中位 33pp、最大 177pp（RO32：1076% vs 1253%）
 *   - 中国城市 34/36 城偏差，中位 4.0pp、最大 16.4pp
 * 与日本序列 P0 同源（展示币种 ≠ 计算币种），但此前只修了日本，另三层漏网。
 *
 * 本测试是该类问题的回归护栏：任何层的 growth(metric, base) 必须等于
 * 同一指标在两个端点上的**展示值**之比。
 *
 * 用法：node tests/growth_currency_test.js（cwd 必须是项目根）
 */
const fs = require('fs'), vm = require('vm'), path = require('path');

const ROOT = path.resolve(__dirname, '..');
global.window = global;                       // vendor 数据文件是浏览器全局脚本
const load = f => vm.runInThisContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), { filename: f });

load('vendor/countries_wb.js');
load('vendor/fxrate.js');
load('vendor/cn_prov_ts.js');
load('vendor/us_states_bea.js');
load('vendor/us_pop_ts.js');
load('vendor/jp_metrics.js');
load('vendor/jp_ts.js');
load('vendor/cn/city_metrics.js');
load('vendor/cn/city_ts.js');
load('vendor/eu/eu_metrics.js');
load('vendor/app-core.js');
global.dataYear = 2025;

let fail = 0, pass = 0;
const ck = (name, cond, info) => {
  if (cond) { pass++; console.log('  ✓ ' + name + (info ? '  ' + info : '')); }
  else { fail++; console.log('  ✗ ' + name + (info ? '  ' + info : '')); }
};
const fx = v => (v == null || !isFinite(v)) ? 'null' : v.toFixed(2) + '%';

console.log('── 1. 派生指标注册（人均GDP·现价 / 地均GDP）──');
ck('METRICS.gdppc 已注册', !!METRICS.gdppc);
ck('METRICS.gdpden 已注册', !!METRICS.gdpden);
ck('gdppc 全部层级可用（scope≠world）', metricScope('gdppc') === 'all', 'scope=' + metricScope('gdppc'));
ck('gdpden 全部层级可用（scope≠world）', metricScope('gdpden') === 'all', 'scope=' + metricScope('gdpden'));

console.log('\n── 2. 6 层均可算出人均 / 地均 ──');
const LAYER_CASES = [
  ['国家 CN',       () => regCountry('CN'),        5000, 200000],
  ['省 广东',       () => regProv('广东'),          3000, 200000],
  ['州 California', () => regUSState('California'),20000, 300000],
  ['县 东京都',     () => regJapanPref('东京都'),   10000, 300000],
  ['NUTS DE11',     () => regNUTS('DE11'),         10000, 300000],
];
for (const [nm, f, lo, hi] of LAYER_CASES) {
  const r = f();
  const pc = r ? regGet(r, 'gdppc', dataYear) : null;
  const dn = r ? regGet(r, 'gdpden', dataYear) : null;
  ck(nm + ' 人均/地均', pc != null && dn != null && pc > lo && pc < hi && dn > 0,
     `人均 $${pc != null ? pc.toFixed(0) : 'null'} · 地均 $${dn != null ? dn.toFixed(0) : 'null'}/km²`);
}
{ /* 城市层：pop 单年(2023)，gdp 按最近年回退，仍须可算且量级合理 */
  const ad = '440100';                       // 广州
  const r = regCity(CITY_METRICS[ad], ad);
  const pc = r ? regGet(r, 'gdppc', 2023) : null;
  const dn = r ? regGet(r, 'gdpden', 2023) : null;
  ck('城市 440100 人均/地均', pc != null && dn != null && pc > 3000 && pc < 200000 && dn > 0,
     `人均 $${pc != null ? pc.toFixed(0) : 'null'} · 地均 $${dn != null ? dn.toFixed(0) : 'null'}/km²`);
}

console.log('\n── 3. 增长口径一致性（P0 回归护栏）：growth 必须等于展示值之比 ──');
function consistency(label, reg, m, base) {
  if (!reg) { ck(label, false, 'reg=null'); return; }
  const g = reg.growth(m, base);
  if (g == null) { ck(label, false, 'growth 为 null（本用例应有值）'); return; }
  const v0 = regGet(reg, m, base), v1 = regGet(reg, m, dataYear);
  const exp = (v1 != null && v0 != null && v0 !== 0) ? (v1 / v0 - 1) : null;
  const ok = exp != null && Math.abs(g - exp) < 1e-9;
  ck(label, ok, `growth=${(g * 100).toFixed(2)}% · 展示值算得=${exp != null ? (exp * 100).toFixed(2) + '%' : 'null'}`);
}
for (const sh of ['西藏', '广东', '江苏', '黑龙江'])
  consistency(`省 ${sh} 2000→${dataYear}`, regProv(sh), 'gdp', 2000);
for (const nid of ['RO32', 'DE11', 'BG41', 'LT01'])
  consistency(`NUTS ${nid} 2000→${dataYear}`, regNUTS(nid), 'gdp', 2000);
/* 仅取「序列 ≥2 年」的城市：单年城市（如 130200 唐山只有 2020）growth 返回 null 是正确行为 */
const cityMulti = Object.keys(CITY_TS).filter(ad => Object.keys(CITY_TS[ad]).length >= 2).slice(0, 4);
ck('存在 ≥2 年的城市序列样本', cityMulti.length >= 3, cityMulti.length + ' 个');
for (const ad of cityMulti) {
  const c = CITY_METRICS[ad]; if (!c) continue;
  consistency(`城市 ${ad} 2009→${dataYear}`, regCity(c, ad), 'gdp', 2009);
}
for (const st of ['California', 'Texas'])
  consistency(`州 ${st} 2000→${dataYear}`, regUSState(st), 'gdp', 2000);
for (const pf of ['东京都', '北海道'])
  consistency(`县 ${pf} 2011→${dataYear}`, regJapanPref(pf), 'gdp', 2011);

console.log('\n── 4. 增长方向性（防口径回归把方向搞反）──');
{
  const g = regJapanPref('北海道').growth('gdp', 2011);
  ck('北海道 2011→2022 美元口径为负（日元贬值）', g != null && g < 0, fx(g * 100));
  const d = regNUTS('DE11').growth('gdp', 2000);
  ck('DE11 斯图加特 2000→2024 为正', d != null && d > 0, fx(d * 100));
  const t = regProv('西藏').growth('gdp', 2000);
  ck('西藏 2000→2025 为正', t != null && t > 0, fx(t * 100));
}

console.log('\n── 5. 国家层仍走不变价（有意设计，不得被动到）──');
for (const iso of ['CN', 'US']) {
  const r = regCountry(iso);
  const g = r.growth('gdp', 2000);
  const nominal = (() => { const a = regGet(r, 'gdp', 2000), b = regGet(r, 'gdp', dataYear);
    return (a && b) ? b / a - 1 : null; })();
  ck(`国家 ${iso} growth 非 null 且与现价不同（=不变价口径）`,
     g != null && isFinite(g) && nominal != null && Math.abs(g - nominal) > 1e-6,
     `不变价=${fx(g * 100)} · 现价=${fx(nominal * 100)}`);
}

console.log('\n' + (fail ? `✗ ${pass} 通过 / ${fail} 失败` : `✓ 全部通过（${pass} 项断言）`));
process.exit(fail ? 1 : 0);
