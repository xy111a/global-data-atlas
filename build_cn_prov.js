// 从中文维基抓取中国省级 GDP 多年序列 (2000/2010/2020-2024 + 2025), 离线嵌入 vendor/cn_prov_ts.js
// 输出 window.CN_TS = { "<省名>": { gdpRMB:{yyyy:元}, rg25:实际增幅%, pop:{2023:人}, area:km2 } }
// 数据: 中文维基「中华人民共和国省级行政区地区生产总值列表」(基于第五次全国经济普查修订)
const fs = require("fs");
const path = require("path");
const ROOT = __dirname, HTML = path.join(ROOT, "global-data-atlas.html");
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function getText(u){ for(let a=1;a<=4;a++){ try{ const r=await fetch(u); if(!r.ok) throw 0; return await r.text(); }catch(e){ if(a===4) throw e; await sleep(800*a);} } }
async function wikiWT(title){
  const u=`https://zh.wikipedia.org/w/api.php?action=parse&page=${encodeURIComponent(title)}&prop=wikitext&format=json`;
  const j=JSON.parse(await getText(u));
  if(!j.parse) throw new Error("no parse: "+JSON.stringify(j).slice(0,150));
  return j.parse.wikitext["*"];
}
const num = s => { if(s==null) return null; const m=String(s).replace(/,/g,"").match(/-?\d+(\.\d+)?/); return m?parseFloat(m[0]):null; };
// 维基显示名别名归一（表1用「内蒙」、表2用「内蒙古」，须合并到同一省）
const NORM = {"内蒙":"内蒙古"};
function normShort(s){ return (NORM[s]||s).trim(); }
// 取某段 wikitext 内第一个 wikitable 到 |} 的内容
function firstTable(wt){
  const i=wt.indexOf("wikitable"); if(i<0) return "";
  const end=wt.indexOf("|}", i); return end>i? wt.slice(i, end) : wt.slice(i, i+20000);
}
// 从一行提取省名 ([[X|Y]] -> Y) 与所有数字
function parseRow(line){
  const nm = line.match(/\[\[([^\]|]+)\|([^\]|]+)\]\]/) || line.match(/\[\[([^\]|]+)\]\]/);
  if(!nm) return null;
  const name = normShort((nm[2]||nm[1]).trim());
  const nums = (line.match(/[\d,]+\.?\d*/g)||[]).map(s=>num(s)).filter(v=>v!=null && v>0);
  return {name, nums};
}

(async () => {
  const wt = await wikiWT("中华人民共和国省级行政区地区生产总值列表");
  const tables = [];
  let p = wt.indexOf("wikitable");
  while(p!==-1){ const e=wt.indexOf("|}", p); tables.push(e>p?wt.slice(p,e):wt.slice(p,p+20000)); p=wt.indexOf("wikitable", p+1); }
  console.log("wikitable 数量:", tables.length);

  const CN_TS = {};

  // 表1: 2025 各省 (百万人民币) + 实际增幅%
  const t1 = tables[0];
  for(const line of t1.split("\n")){
    if(!line.includes("[[") || !line.includes("||")) continue;
    const r = parseRow(line); if(!r || r.nums.length<4) continue;
    // 列: GDP(百万RMB) | GDP(百万$) | 占比 | 实际增幅 | 名义增幅
    const g25 = r.nums[0]*1e6;
    const rg25 = r.nums[3]!=null ? r.nums[3] : null; // 实际增幅(%) -> 存小数
    if(!CN_TS[r.name]) CN_TS[r.name] = { gdpRMB:{}, rg25:null, pop:{}, area:null };
    CN_TS[r.name].gdpRMB["2025"] = g25;
    CN_TS[r.name].rg25 = (rg25!=null)? rg25/100 : null;
  }
  console.log("表1(2025) 解析省数:", Object.keys(CN_TS).length);

  // 表2: 主要年份 2024/2023/2022/2021/2020/2010/2000 (百万人民币)
  const yrs = ["2024","2023","2022","2021","2020","2010","2000"];
  const t2 = tables[1];
  for(const line of t2.split("\n")){
    if(!line.includes("[[") || !line.includes("||")) continue;
    const r = parseRow(line); if(!r) continue;
    if(r.nums.length < 7) continue;
    if(!CN_TS[r.name]) CN_TS[r.name] = { gdpRMB:{}, rg25:null, pop:{}, area:null };
    yrs.forEach((y,i)=> CN_TS[r.name].gdpRMB[y] = r.nums[i]*1e6);
  }
  console.log("表2(主要年份) 解析省数:", Object.keys(CN_TS).filter(k=>CN_TS[k].gdpRMB["2000"]).length);

  // 面积 + 人口(2023常住人口, 万人->人) 沿用 HTML 内 CN
  const html = fs.readFileSync(HTML,"utf8");
  const m = html.match(/const CN = \{([\s\S]*?)\};/);
  const cnKeys = new Set();
  if(m){ for(const r of m[1].match(/"([^"]*)":\{gdp:[\d.]+,pop:([\d.]+),area:([\d.]+)/g)||[]){
    const mm=r.match(/"([^"]*)":\{gdp:[\d.]+,pop:([\d.]+),area:([\d.]+)/);
    if(mm){ cnKeys.add(mm[1]); if(CN_TS[mm[1]]){ CN_TS[mm[1]].area=+mm[3]; CN_TS[mm[1]].pop={"2023": num(mm[2])*1e4}; } }
  }}
  // 清理：仅保留 HTML 内 CN 列表中的省，去掉「中国大陆/香港」等无 adcode 项；并去无 GDP 残留
  for(const k of Object.keys(CN_TS)){
    if(!cnKeys.has(k) || (!CN_TS[k].gdpRMB["2000"] && !CN_TS[k].gdpRMB["2025"])) delete CN_TS[k];
  }

  fs.writeFileSync(path.join(ROOT,"vendor","cn_prov_ts.js"), "window.CN_TS = "+JSON.stringify(CN_TS)+";\n");
  const sz=(fs.statSync(path.join(ROOT,"vendor","cn_prov_ts.js")).size/1024).toFixed(0);
  console.log(`✅ 写出 vendor/cn_prov_ts.js (${sz}KB), 省级数: ${Object.keys(CN_TS).length}`);

  // 校验
  for(const nm of ["广东","江苏","浙江","内蒙古"]){
    const o=CN_TS[nm]; if(!o){console.log("  缺失:",nm);continue;}
    const g=o.gdpRMB;
    console.log(`  ${nm}: 2000=${(g["2000"]/1e12).toFixed(2)}万亿 2023=${(g["2023"]/1e12).toFixed(2)}万亿 2024=${(g["2024"]/1e12).toFixed(2)}万亿 2025=${(g["2025"]/1e12).toFixed(2)}万亿 | 实际增幅2025=${(o.rg25!=null?(o.rg25*100).toFixed(1)+'%':'-')} | 面积=${o.area} | pop2023=${o.pop["2023"]}`);
  }
})().catch(e=>{ console.error("BUILD FAILED:", e); process.exit(1); });
