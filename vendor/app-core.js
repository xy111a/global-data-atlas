/* ============== app-core.js 核心数据/逻辑层（两页共享） ==============
   从 global-data-atlas.html 抽取：指标注册表 METRICS / 区域统一接口 reg* /
   数据取数 / 格式化 / 常量。对比页 compare.html 与主页面共用。
   依赖：vendor/ 数据文件（world.js, countries_wb.js, fxrate.js, ext_indicators.js,
   cn_prov_ts.js, us_states_bea.js, jp_metrics.js, cn/city_metrics.js, eu/eu_metrics.js）
   需在数据文件之后加载。
   ⚠️ 修改此处后需同步主页面；用 extract_core.py 重新生成时勿手工编辑此文件。 */
window.COUNTRIES = Object.values(window.WB || {}).map(o => [o.cn, o.en, o.iso2, o.lng, o.lat]);
window.BY_EN = {};
window.EN_ALIAS = {
  "Côte d'Ivoire":"Cote d'Ivoire", "S. Sudan":"South Sudan", "Faeroe Is.":"Faroe Islands",
  "N. Mariana Is.":"Northern Mariana Islands", "St. Vin. and Gren.":"St. Vincent and the Grenadines",
  "Turks and Caicos Is.":"Turks and Caicos Islands", "Marshall Is.":"Marshall Islands",
  "Br. Virgin Is.":"British Virgin Islands", "St. Kitts-Nevis":"St. Kitts and Nevis",
  "U.S. Virgin Is.":"Virgin Islands (U.S.)", "Congo, Dem. Rep.":"Congo, Dem. Rep.",
  "Dem. Rep. Congo":"Congo, Dem. Rep.", "Macedonia":"North Macedonia", "Swaziland":"Eswatini",
  "Congo":"Congo, Rep.", "Korea":"Korea, Rep.", "Dem. Rep. Korea":"Korea, Dem. People's Rep.",
  "Nauru":"Naoero", "Macau":"Macao SAR, China", "Hong Kong":"Hong Kong SAR, China",
  "Curaçao":"Curacao", "Palestine":"West Bank and Gaza", "Jersey":"Channel Islands"
};
window.METRICS = {
  gdp: {
    label:"GDP", fmt:fmtGDP, unit:"人民币元",
    near(o,year){ return (o&&o.get)?o.get("gdp",year):null; },
    series(o){ return (o&&o.gdpSeries)?o.gdpSeries():null; },
    growth(o,base){ return (o&&o.growth)?o.growth("gdp",base):null; }
  },
  pop: {
    label:"人口", fmt:fmtPop, unit:"人",
    near(o,year){ return (o&&o.get)?o.get("pop",year):null; },
    series(){ return null; }, growth(){ return null; }
  },
  area: {
    label:"面积", fmt:fmtArea, unit:"km²",
    near(o,year){ return (o&&o.get)?o.get("area",year):null; },
    series(){ return null; }, growth(){ return null; }
  },
  /* ===== 扩展指标（World Bank EXT，国家层） =====
     通用取数器：reg.ext(m, year) 返回最近可得值，缺失返回 null。
     省/州/市 reg 无 ext → 自动显示"暂无"，无需各自实现。 */
  trade: {
    scope:"world",
    label:"贸易占GDP", fmt:v=>fmtPct(v), unit:"% (出口+进口)/GDP",
    near(o,year){ return (o&&o.ext)?o.ext("trade",year):null; },
    series(){ return null; }, growth(){ return null; }
  },
  health: {
    scope:"world",
    label:"医疗支出", fmt:v=>fmtPct(v), unit:"% GDP",
    near(o,year){ return (o&&o.ext)?o.ext("health",year):null; },
    series(){ return null; }, growth(){ return null; }
  },
  edu: {
    scope:"world",
    label:"教育支出", fmt:v=>fmtPct(v), unit:"% GDP",
    near(o,year){ return (o&&o.ext)?o.ext("edu",year):null; },
    series(){ return null; }, growth(){ return null; }
  },
  life: {
    scope:"world",
    label:"预期寿命", fmt:v=>v!=null?v.toFixed(1)+" 岁":null, unit:"岁",
    near(o,year){ return (o&&o.ext)?o.ext("life",year):null; },
    series(){ return null; }, growth(){ return null; }
  },
  gdpcap: {
    scope:"world",
    label:"人均GDP", fmt:v=>v!=null?"$"+v.toFixed(0):null, unit:"USD(2015不变价)",
    near(o,year){ return (o&&o.ext)?o.ext("gdpcap",year):null; },
    series(){ return null; }, growth(){ return null; }
  },
  /* ===== Phase F2 新增指标 ===== */
  unemp: {
    scope:"world",
    label:"失业率", fmt:v=>fmtPct(v), unit:"% 劳动力",
    near(o,year){ return (o&&o.ext)?o.ext("unemp",year):null; },
    series(){ return null; }, growth(){ return null; }
  },
  internet: {
    scope:"world",
    label:"互联网普及", fmt:v=>fmtPct(v), unit:"% 人口",
    near(o,year){ return (o&&o.ext)?o.ext("internet",year):null; },
    series(){ return null; }, growth(){ return null; }
  },
  military: {
    scope:"world",
    label:"军费", fmt:v=>fmtPct(v), unit:"% GDP",
    near(o,year){ return (o&&o.ext)?o.ext("military",year):null; },
    series(){ return null; }, growth(){ return null; }
  }
};
window.USD_CNY = 7.2;
window.CN = {
  "广东":{pop:12706,area:179725,"adcode":440000},
  "江苏":{pop:8526,area:107200,"adcode":320000},
  "山东":{pop:10123,area:155800,"adcode":370000},
  "浙江":{pop:6627,area:105500,"adcode":330000},
  "河南":{pop:9815,area:167000,"adcode":410000},
  "四川":{pop:8368,area:486000,"adcode":510000},
  "湖北":{pop:5838,area:185900,"adcode":420000},
  "福建":{pop:4183,area:124000,"adcode":350000},
  "湖南":{pop:6568,area:211800,"adcode":430000},
  "安徽":{pop:6121,area:140100,"adcode":340000},
  "上海":{pop:2487,area:6340,"adcode":310000},
  "河北":{pop:7393,area:188800,"adcode":130000},
  "北京":{pop:2186,area:16410,"adcode":110000},
  "陕西":{pop:3956,area:205600,"adcode":610000},
  "江西":{pop:4515,area:166900,"adcode":360000},
  "重庆":{pop:3191,area:82400,"adcode":500000},
  "辽宁":{pop:4182,area:148000,"adcode":210000},
  "云南":{pop:4673,area:383100,"adcode":530000},
  "广西":{pop:5027,area:237600,"adcode":450000},
  "山西":{pop:3466,area:156700,"adcode":140000},
  "内蒙古":{pop:2396,area:1183000,"adcode":150000},
  "贵州":{pop:3856,area:176100,"adcode":520000},
  "新疆":{pop:2598,area:1660000,"adcode":650000},
  "天津":{pop:1363,area:11966,"adcode":120000},
  "黑龙江":{pop:3099,area:473000,"adcode":230000},
  "吉林":{pop:2339,area:187400,"adcode":220000},
  "甘肃":{pop:2465,area:425800,"adcode":620000},
  "海南":{pop:1043,area:35400,"adcode":460000},
  "宁夏":{pop:729,area:66400,"adcode":640000},
  "青海":{pop:594,area:722300,"adcode":630000},
  "西藏":{pop:365,area:1228400,"adcode":540000}
};
window.PROV_ADCODE = {};
window.US_STATES_GDP = {
  "California":{gdp:3.9,pop:38965193,area:423967},
  "Texas":{gdp:2.6,pop:30503301,area:695662},
  "New York":{gdp:2.1,pop:19571216,area:141297},
  "Florida":{gdp:1.5,pop:22610726,area:170312},
  "Illinois":{gdp:1.0,pop:12549689,area:149995},
  "Pennsylvania":{gdp:0.99,pop:12961683,area:119280},
  "Ohio":{gdp:0.86,pop:11785935,area:116098},
  "Washington":{gdp:0.78,pop:7812880,area:184661},
  "New Jersey":{gdp:0.77,pop:9290841,area:22591},
  "Georgia":{gdp:0.74,pop:11029227,area:153910},
  "North Carolina":{gdp:0.73,pop:10835491,area:139391},
  "Massachusetts":{gdp:0.70,pop:7001399,area:27336},
  "Virginia":{gdp:0.68,pop:8715698,area:110787},
  "Michigan":{gdp:0.64,pop:10037261,area:250487},
  "Arizona":{gdp:0.48,pop:7431344,area:295234},
  "Colorado":{gdp:0.48,pop:5877610,area:269601},
  "Maryland":{gdp:0.47,pop:6180253,area:32131},
  "Tennessee":{gdp:0.47,pop:7126489,area:109153},
  "Indiana":{gdp:0.47,pop:6862199,area:94326},
  "Minnesota":{gdp:0.44,pop:5737915,area:225163},
  "Wisconsin":{gdp:0.41,pop:5910955,area:169635},
  "Missouri":{gdp:0.40,pop:6196156,area:180540},
  "Connecticut":{gdp:0.32,pop:3617176,area:14357},
  "Oregon":{gdp:0.32,pop:4233358,area:254799},
  "South Carolina":{gdp:0.30,pop:5373555,area:82933},
  "Louisiana":{gdp:0.28,pop:4573749,area:135659},
  "Alabama":{gdp:0.27,pop:5108468,area:135767},
  "Utah":{gdp:0.27,pop:3417734,area:219882},
  "Oklahoma":{gdp:0.25,pop:4053824,area:181037},
  "Iowa":{gdp:0.25,pop:3207004,area:145746},
  "Nevada":{gdp:0.24,pop:3194176,area:286380},
  "Kentucky":{gdp:0.23,pop:4526154,area:104656},
  "Kansas":{gdp:0.22,pop:2940546,area:213100},
  "Arkansas":{gdp:0.18,pop:3067732,area:137732},
  "Nebraska":{gdp:0.17,pop:1978379,area:200330},
  "District of Columbia":{gdp:0.16,pop:678972,area:177},
  "Mississippi":{gdp:0.15,pop:2939690,area:125438},
  "New Mexico":{gdp:0.13,pop:2114371,area:314917},
  "Idaho":{gdp:0.12,pop:1964726,area:216443},
  "Puerto Rico":{gdp:0.12,pop:3205691,area:9104},
  "New Hampshire":{gdp:0.11,pop:1402054,area:24214},
  "Hawaii":{gdp:0.10,pop:1435138,area:28313},
  "Delaware":{gdp:0.095,pop:1031890,area:6446},
  "Maine":{gdp:0.09,pop:1395722,area:91633},
  "West Virginia":{gdp:0.09,pop:1770071,area:62756},
  "Rhode Island":{gdp:0.08,pop:1095962,area:4001},
  "Wyoming":{gdp:0.05,pop:584057,area:253335},
  "Vermont":{gdp:0.04,pop:647464,area:24906},
  "Montana":{gdp:0.07,pop:1132812,area:380831},
  "South Dakota":{gdp:0.07,pop:919318,area:199729},
  "North Dakota":{gdp:0.07,pop:783926,area:183108},
  "Alaska":{gdp:0.063,pop:733406,area:1723337}
};
window.RATE23 = (window.FXRATE && window.FXRATE["2023"]) || USD_CNY;

function enToWb(nm){ if(BY_EN[nm]) return nm; return EN_ALIAS[nm] || null; }
function wbForMapName(nm){ const k=enToWb(nm); return k ? BY_EN[k] : null; }
function fmtPct(v){ return v==null?null:v.toFixed(1)+"%"; }
function esc(s){
  return String(s==null?"":s).replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function metricLabel(m){ return (METRICS[m]||{}).label || m; }
function metricFmt(m,v){ if(v==null||isNaN(v)) return "—"; const f=(METRICS[m]||{}).fmt; return f?f(v):v; }
function metricScope(m){ return (METRICS[m]&&METRICS[m].scope==="world")?"world":"all"; }
function metricUnavailableMsg(m){ return `当前指标「${metricLabel(m)}」仅国家层可用（World Bank），省级/州级无此数据。请切换回 GDP / 人口 / 面积。`; }
function cMetric(iso2, m, year){
  const o = window.WB && window.WB[iso2]; if(!o || !o.years) return null;   // 无数据返回 null（此前返回 0 会误渲染）
  year = year || dataYear;
  const yk = Object.keys(o.years).map(Number);
  const has = y => o.years[y] && (m==="area" ? o.years[y].area!=null : o.years[y][m]!=null);
  let pick = null;
  if(has(year)) pick = year;
  if(pick==null){
    const b = yk.filter(y=>y<=year && has(y)).sort((a,b)=>b-a)[0];
    const a = yk.filter(y=>y>year && has(y)).sort((a,b)=>a-b)[0];
    pick = (b!=null) ? b : (a!=null ? a : null);
  }
  if(pick==null) return null;
  let v = m==="gdp" ? o.years[pick].gdp : m==="pop" ? o.years[pick].pop : o.years[pick].area;
  if(v==null) return null;
  if(m==="gdp"){ const rate = (window.FXRATE && window.FXRATE[pick]) || USD_CNY; v = v * rate; }   // USD → CNY(元)，按实际采用年份的逐年平均市场汇率
  return v;
}
function cYear(iso2){
  const o = window.WB && window.WB[iso2]; if(!o || !o.years) return dataYear;
  const m = metric, year = dataYear;
  const yk = Object.keys(o.years).map(Number);
  const has = y => o.years[y] && (m==="area" ? o.years[y].area!=null : o.years[y][m]!=null);
  if(has(year)) return year;
  const b = yk.filter(y=>y<=year && has(y)).sort((a,b)=>b-a)[0];
  const a = yk.filter(y=>y>year && has(y)).sort((a,b)=>a-b)[0];
  return (b!=null) ? b : (a!=null ? a : year);
}
function cGrowth(iso2, base, key){
  const o = window.WB && window.WB[iso2]; if(!o || !o.years) return null;
  const yk = Object.keys(o.years).map(Number);
  const has = y => o.years[y] && o.years[y][key]!=null;
  function near(yr){ if(has(yr)) return yr;
    const b=yk.filter(y=>y<=yr&&has(y)).sort((a,b)=>b-a)[0];
    const a=yk.filter(y=>y>yr&&has(y)).sort((a,b)=>a-b)[0];
    return (b!=null)?b:(a!=null?a:null); }
  const yb=near(base), ys=near(dataYear);
  if(yb==null||ys==null) return null;
  const vb=o.years[yb][key], vs=o.years[ys][key];
  if(!vb) return null;
  return vs/vb - 1;
}
function fmtGrowth(g){
  if(g==null) return "—";
  return (g>=0?"+":"") + (g*100).toFixed(1) + "%";
}
function fmtGrowthFor(m, g){
  if(g==null) return "—";
  if(m==="life") return (g>=0?"+":"") + g.toFixed(1) + " 岁";
  return (g>=0?"+":"") + (g*100).toFixed(1) + "%";
}
function usGdpUsdM(name, year){            // 返回 USD 百万 (number) 或 null
  const ts = window.US_TS && window.US_TS[name];
  if(!ts) return null;
  const ys = ts.years;
  if(ys[year]!=null) return ys[year];
  const avail = Object.keys(ys).map(Number).sort((a,b)=>a-b);
  if(!avail.length) return null;
  let best = avail[0], bd = Math.abs(avail[0]-year);
  for(const y of avail){ const d=Math.abs(y-year); if(d<bd){bd=d;best=y;} }
  return ys[best];
}
function usGdpY(name, year){               // 返回 人民币元 (按逐年汇率折算)
  const m = usGdpUsdM(name, year);
  if(m==null) return null;
  const y = usGdpYear(name, year);         // 实际采用的年份（回退后），汇率随实际年份
  const r = (window.FXRATE && window.FXRATE[y]) || USD_CNY;
  return m * r * 1e6;
}
function usGdpYear(name, year){            // 实际采用的年份（usGdpUsdM 回退后）
  const ts = window.US_TS && window.US_TS[name];
  if(!ts || !ts.years) return year;
  if(ts.years[year]!=null) return year;
  const avail = Object.keys(ts.years).map(Number).sort((a,b)=>a-b);
  if(!avail.length) return year;
  let best = avail[0], bd = Math.abs(avail[0]-year);
  for(const y of avail){ const d=Math.abs(y-year); if(d<bd){bd=d;best=y;} }
  return best;
}
function usGdpUsdT(name, year){            // 返回 美元 万亿 (用于悬浮提示)
  const m = usGdpUsdM(name, year);
  return m==null ? null : m/1e6;
}
function usNominalGrowth(name, baseYear){  // 较基准年 名义(现价)增长, 返回小数, 缺失返回 null
  const b = usGdpUsdM(name, baseYear), e = usGdpUsdM(name, dataYear);
  if(b==null || e==null || b===0) return null;
  return e/b - 1;
}
function cnGdpRMB(short, year){            // 返回 人民币元 (number) 或 null
  const o = window.CN_TS && window.CN_TS[short]; if(!o || !o.gdpRMB) return null;
  const ys = o.gdpRMB; if(ys[year]!=null) return ys[year];
  const avail = Object.keys(ys).map(Number).sort((a,b)=>a-b);
  if(!avail.length) return null;
  let best = avail[0], bd = Math.abs(avail[0]-year);
  for(const y of avail){ const d=Math.abs(y-year); if(d<bd){bd=d;best=y;} }
  return ys[best];
}
function cnGdpYear(short, year){           // cnGdpRMB 实际采用的年份（稀疏年份诚实标注）
  const o = window.CN_TS && window.CN_TS[short]; if(!o || !o.gdpRMB) return year;
  if(o.gdpRMB[year]!=null) return year;
  const avail = Object.keys(o.gdpRMB).map(Number).sort((a,b)=>a-b);
  if(!avail.length) return year;
  let best = avail[0], bd = Math.abs(avail[0]-year);
  for(const y of avail){ const d=Math.abs(y-year); if(d<bd){bd=d;best=y;} }
  return best;
}
function cnNominalGrowth(short, baseYear){ // 较基准年 名义(现价)增长, 返回小数, 缺失返回 null
  const b = cnGdpRMB(short, baseYear), e = cnGdpRMB(short, dataYear);
  if(b==null || e==null || b===0) return null;
  return e/b - 1;
}
function fmtGDP(v){ if(v==null||isNaN(v)) return "—"; if(v>=1e12)return "¥"+(v/1e12).toFixed(2)+" 万亿"; if(v>=1e8)return "¥"+(v/1e8).toFixed(2)+" 亿"; if(v>=1e4)return "¥"+(v/1e4).toFixed(1)+" 万"; return "¥"+v.toFixed(0); }
function fmtPop(v){ if(v==null||isNaN(v)) return "—"; if(v>=1e8)return (v/1e8).toFixed(2)+" 亿人"; if(v>=1e4)return (v/1e4).toFixed(2)+" 万人"; return v.toLocaleString()+" 人"; }
function fmtArea(v){ if(v==null||isNaN(v)) return "—"; if(v>=1e4)return (v/1e4).toFixed(2)+" 万平方千米"; return v.toLocaleString()+" 平方千米"; }
function normProv(n){ return n.replace(/(省|市|自治区|特别行政区|壮族|回族|维吾尔)/g,"").trim(); }
function regCountry(iso2){
  const o=window.WB&&window.WB[iso2]; if(!o) return null;
  return {
    name:o.cn, en:o.en, iso2,
    years:()=>Object.keys(o.years).map(Number).sort((a,b)=>a-b),
    get(m,year){ return cMetric(iso2,m,year); },
    /* 扩展指标（EXT）：按最近可得年份取数，缺失返回 null */
    ext(m,year){
      const d=window.EXT&&window.EXT[iso2]&&window.EXT[iso2][m];
      if(!d) return null;
      year=year||dataYear;
      if(d[year]!=null) return d[year];
      const avail=Object.keys(d).map(Number).sort((a,b)=>a-b);
      if(!avail.length) return null;
      let best=avail[0], bd=Math.abs(avail[0]-year);
      for(const y of avail){ const dd=Math.abs(y-year); if(dd<bd){bd=dd;best=y;} }
      return d[best];
    },
    /* EXT 实际采用年份（M6）：与 ext() 同口径，供 UI 诚实标注 */
    extYear(m,year){
      const d=window.EXT&&window.EXT[iso2]&&window.EXT[iso2][m];
      if(!d) return null;
      year=year||dataYear;
      if(d[year]!=null) return year;
      const avail=Object.keys(d).map(Number).sort((a,b)=>a-b);
      if(!avail.length) return null;
      let best=avail[0], bd=Math.abs(avail[0]-year);
      for(const y of avail){ const dd=Math.abs(y-year); if(dd<bd){bd=dd;best=y;} }
      return best;
    },
    growth(m,base){
      if(m==="gdp") return cGrowth(iso2,base,"gdpKd");  // 国家用不变价（真实增长）
      if(m==="pop") return cGrowth(iso2,base,"pop");    // 人口增长（WB pop 序列）
      if(m==="area") return cGrowth(iso2,base,"area");  // 面积变化（WB area 序列：测量修订/填海/领土变更）
      // EXT 扩展指标：trade/health/edu/life/gdpcap 较 base 年变化
      const d=window.EXT&&window.EXT[iso2]&&window.EXT[iso2][m];
      if(!d) return null;
      const ks=Object.keys(d).map(Number).sort((a,b)=>a-b);
      const near=yr=>{ if(d[yr]!=null)return yr; const b=ks.filter(y=>y<=yr&&d[y]!=null).pop(); const a=ks.filter(y=>y>yr&&d[y]!=null)[0]; return b!=null?b:(a!=null?a:null); };
      const yb=near(base), ys=near(dataYear);
      if(yb==null||ys==null) return null;
      const vb=d[yb], vs=d[ys];
      if(vb==null) return null;
      if(m==="life") return vs - vb;   // 预期寿命：绝对变化（岁）
      if(vb===0) return null;
      return vs/vb - 1;   // 相对增长率（trade/health/edu/gdpcap）
    },
    gdpSeries(){ const tr=countryTrend(iso2); return tr?{name:o.cn,years:tr.years,values:tr.values}:null; },
    /* 趋势随维度：gdp→WB序列(人民币元)；pop/area→WB 多年；EXT 指标→按年（≥2 点才有趋势） */
    series(m){
      if(m==="gdp"){ const tr=countryTrend(iso2); return tr?{name:o.cn,years:tr.years,values:tr.values}:null; }
      if(m==="pop"||m==="area"){
        const ys=(o.years&&Object.keys(o.years))||[];
        const pairs=ys.map(Number).sort((a,b)=>a-b).map(y=>[y,o.years[y]&&o.years[y][m]]).filter(p=>p[1]!=null);
        return pairs.length>=2?{name:o.cn,years:pairs.map(p=>p[0]),values:pairs.map(p=>p[1])}:null;
      }
      const ed=window.EXT&&window.EXT[iso2]&&window.EXT[iso2][m];
      if(ed&&typeof ed==="object"){
        const yrs=Object.keys(ed).map(Number).sort((a,b)=>a-b);
        if(yrs.length>=2) return {name:o.cn,years:yrs,values:yrs.map(y=>ed[y])};
      }
      return null;
    }
  };
}
function regProv(short){
  return {
    name:short, cn:short,
    years:()=>Object.keys((window.CN_TS&&window.CN_TS[short]&&window.CN_TS[short].gdpRMB)||{}).map(Number).sort((a,b)=>a-b),
    ext(){ return null; },   // 省级无 World Bank 扩展指标
    get(m,year){
      if(m==="gdp") return cnGdpRMB(short,year);
      const o=window.CN_TS&&window.CN_TS[short];
      if(m==="pop") return (o&&o.pop&&o.pop["2023"])||(CN[short]&&CN[short].pop*1e4)||null;
      if(m==="area") return (o&&o.area!=null)?o.area:(CN[short]&&CN[short].area)||null;
      return null;
    },
    growth(m,base){ return m==="gdp"?cnNominalGrowth(short,base):null; },
    gdpSeries(){ const tr=provTrend(short); return tr?{name:short,years:tr.years,values:tr.values}:null; },
    series(m){ return m==="gdp"?this.gdpSeries():null; }   // 省 pop 单年/area 单值，无趋势
  };
}
function regUSState(nm){
  return {
    name:nm, cn:nm,
    years:()=>Object.keys((window.US_TS&&window.US_TS[nm]&&window.US_TS[nm].years)||{}).map(Number).sort((a,b)=>a-b),
    ext(){ return null; },   // 州级无 World Bank 扩展指标
    get(m,year){
      const s=US_STATES_GDP[nm]; if(!s) return null;
      if(m==="gdp"){ const y=usGdpY(nm,year); return y!=null?y:s.gdp; }
      if(m==="pop") return s.pop;
      if(m==="area") return s.area;
      return null;
    },
    growth(m,base){ return m==="gdp"?usNominalGrowth(nm,base):null; },
    gdpSeries(){ const tr=usTrend(nm); return tr?{name:nm,years:tr.years,values:tr.values}:null; },
    series(m){ return m==="gdp"?this.gdpSeries():null; }   // 州仅 GDP 多年序列（人口 Census 单年）
  };
}
function regCity(cm, adcode){
  if(!cm) return null;
  /* 多年序列（Phase E）：CITY_TS[adcode] = {年份: 亿元} */
  const ts = adcode && window.CITY_TS && window.CITY_TS[String(adcode)];
  const ylist = ts ? Object.keys(ts).map(Number).sort((a,b)=>a-b) : [];
  return {
    name:cm.name||"", cn:cm.name||"",
    years:()=>ylist.slice(),   // 无序列城市返回 []
    ext(){ return null; },   // 城市无 World Bank 扩展指标
    get(m, year){
      if(m==="gdp"){
        if(ts){
          if(!year || year==="2023") return cm.gdp;          // 默认/2023 → 单年值（已折算元）
          const y=+year;
          if(ts[y]!=null) return ts[y]*1e8;                  // 序列年 → 亿元×1e8=元
          const near = ylist.length? ylist.reduce((a,b)=>Math.abs(b-y)<Math.abs(a-y)?b:a) : null;
          return near!=null && ts[near]!=null ? ts[near]*1e8 : cm.gdp;
        }
        return cm.gdp;
      }
      return m==="pop"?cm.pop:(m==="area"?cm.area:null);
    },
    growth(m, base){
      if(m!=="gdp" || !ts || ylist.length<2) return null;
      const b=base==null?ylist[0]:+base;
      const lo=ylist[0], hi=ylist[ylist.length-1];
      const bv=ts[b]!=null?ts[b]:(b<lo?ts[lo]:ts[hi]);
      if(bv==null) return null;
      return (ts[hi]-bv)/bv;
    },
    gdpSeries(){ if(!ts) return null;
      return {years:ylist, values:ylist.map(y=>ts[y]*1e8)}; },
    series(m){ return m==="gdp"?this.gdpSeries():null; }   // 城市仅 GDP 序列（city_ts 46 城）
  };
}
function regJapanPref(nm){
  const d=window.JP_METRICS&&window.JP_METRICS[nm]; if(!d) return null;
  return {
    name:nm, cn:nm,
    years:()=>[],   // 县级无多年序列（单年数据）
    ext(){ return null; },
    get(m){ return m==="gdp"?d.gdp:m==="pop"?d.pop:(m==="area"?d.area:null); },
    growth(){ return null; }, gdpSeries(){ return null; }
  };
}
function regNUTS(nid){
  const d=window.EU_METRICS&&window.EU_METRICS[nid]; if(!d) return null;
  return {
    name:d.name, cn:d.name, cc:d.cc,
    years:()=>[d.year],   // 单年快照
    ext(){ return null; },
    get(m){ return m==="gdp"?d.gdp:m==="pop"?d.pop:(m==="area"?d.area:null); },
    growth(){ return null; }, gdpSeries(){ return null; }, series(){ return null; }
  };
}
function regGet(reg, m, year){ return METRICS[m] && reg ? METRICS[m].near(reg, year) : null; }
function countryTrend(iso2){
  const o=window.WB&&window.WB[iso2]; if(!o||!o.years) return null;
  const ys=Object.keys(o.years).map(Number).filter(y=>o.years[y].gdp!=null).sort((a,b)=>a-b);
  if(ys.length<2) return null;
  const vals=ys.map(y=>o.years[y].gdp*((window.FXRATE&&window.FXRATE[y])||USD_CNY));
  return {years:ys, values:vals};
}
function provTrend(short){
  const o=window.CN_TS&&window.CN_TS[short]; if(!o||!o.gdpRMB) return null;
  const ys=Object.keys(o.gdpRMB).map(Number).sort((a,b)=>a-b);
  if(ys.length<2) return null;
  return {years:ys, values:ys.map(y=>o.gdpRMB[y])};
}
function usTrend(name){
  const ts=window.US_TS&&window.US_TS[name]; if(!ts||!ts.years) return null;
  const ys=Object.keys(ts.years).map(Number).filter(y=>ts.years[y]!=null).sort((a,b)=>a-b);
  if(ys.length<2) return null;
  return {years:ys, values:ys.map(y=>ts.years[y]*((window.FXRATE&&window.FXRATE[y])||USD_CNY)*1e6)};
}
function currencyTag(m){
  if(m==="gdp") return "货币：人民币(CNY)";
  if(m==="gdpcap") return "货币：USD(2015不变价)";
  return "";   // pop/area/%/岁 等无量纲指标不标货币
}
function getCityMetric(adcode, parentAdcode){
  let cm = window.CITY_METRICS && window.CITY_METRICS[adcode];
  if(!cm && parentAdcode) cm = window.CITY_METRICS[parentAdcode];
  return cm;
}
function euCCName(cc){ const d=DRILLABLE[cc]; return d?d.label:cc; }
function fmtBy(v,m){ m=m||metric; return metricFmt(m,v); }
function usVal(nm,m){ const s=US_STATES_GDP[nm]; if(!s) return 0; m=m||metric;
  if(m==="gdp"){ const y=usGdpY(nm,dataYear); return y==null? s.gdp : y; }
  return m==="pop"?s.pop : s.area; }
function cmpGetData(it){
  const y=dataYear;
  let base={};
  if(it.t==="country"){ base={g:cMetric(it.k,"gdp",y), p:cMetric(it.k,"pop",y), a:cMetric(it.k,"area",y)}; }
  else if(it.t==="prov"){ const g=cnGdpRMB(it.k,y), o=window.CN_TS&&window.CN_TS[it.k];
    base={g, p:(o&&o.pop&&o.pop["2023"])?o.pop["2023"]:null, a:(o&&o.area)||null}; }
  else if(it.t==="usstate"){ base={g:usGdpY(it.k,y), p:(US_STATES_GDP[it.k]||{}).pop, a:(US_STATES_GDP[it.k]||{}).area}; }
  else if(it.t==="jppref"){ const d=window.JP_METRICS&&window.JP_METRICS[it.k]; if(!d) return null;
    base={g:d.gdp, p:d.pop, a:d.area}; }
  else if(it.t==="nutspref"){ const d=window.EU_METRICS&&window.EU_METRICS[it.k]; if(!d) return null;
    base={g:d.gdp, p:d.pop, a:d.area}; }
  else if(it.t==="city"){ const cm=getCityMetric(it.k, it.pa); if(!cm) return null;
    base={g:cm.gdp, p:cm.pop, a:cm.area}; }   // 数据已由 city_metrics.js 折算为元/人（L5: 传 parentAdcode 支持直辖市兜底）
  else return null;
  // 当前维度值：gdp/pop/area 用对应值；EXT 系指标（trade/health/edu/life/gdpcap）仅国家层有
  if(metric==="gdp") base.v=base.g;
  else if(metric==="pop") base.v=base.p;
  else if(metric==="area") base.v=base.a;
  else base.v = (it.t==="country"&&window.EXT&&window.EXT[it.k]&&window.EXT[it.k][metric]) ? (function(){const d=window.EXT[it.k][metric],yy=String(y);if(d[yy]!=null)return d[yy];const ks=Object.keys(d).map(Number).sort((a,b)=>a-b);if(!ks.length)return null;let best=ks[0],bd=Math.abs(ks[0]-y);for(const k of ks){const dd=Math.abs(k-y);if(dd<bd){bd=dd;best=k;}}return d[String(best)];})() : null;   // L6: 与 reg.ext 同口径（最近年份）
  return base;
}
