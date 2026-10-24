// 生成 echarts 模块化精简构建：仅打包全局数据地图用到的图表/组件/渲染器
// 产出：echarts-custom.min.js（<script> 全局引入，暴露 window.echarts）
// 仅用 echarts/core 按需注册，避免全量包重复注册。
const path = require('path');
const fs = require('fs');
const esbuild = require('esbuild');
const { minify } = require('terser');

const ENTRY = path.join(__dirname, '_entry.js');
const OUT = path.join(__dirname, 'echarts-custom.min.js');

fs.writeFileSync(ENTRY, `
import * as echarts from 'echarts/core';
import { LineChart, BarChart, MapChart, ScatterChart } from 'echarts/charts';
import {
  GridComponent, TooltipComponent, LegendComponent,
  TitleComponent, AxisPointerComponent, DataZoomComponent,
  // ⚠️ 2026-10-12 审计修复：地图 choropleth 的 visualMap（颜色刻度图例）此前从未渲染，
  //    原因是定制构建漏了 VisualMapComponent，浏览器控制台持续报
  //    "[ECharts] Component visualMap is used but not imported"，用户看不到颜色↔数值对应关系。
  //    （既有测试只断言 getOption().visualMap 的配置对象，未验证渲染，故长期未被发现。）
  VisualMapComponent, VisualMapPiecewiseComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
echarts.use([
  LineChart, BarChart, MapChart, ScatterChart,
  GridComponent, TooltipComponent, LegendComponent,
  TitleComponent, AxisPointerComponent, DataZoomComponent,
  VisualMapComponent, VisualMapPiecewiseComponent,
  CanvasRenderer,
]);
window.echarts = echarts;
`);

async function main() {
  // 允许从 NODE_PATH（受管 node workspace）解析 echarts/esbuild/terser，
  // 避免在项目目录留下 node_modules（本项目是零构建仓库，不入库依赖）。
  const nodePaths = (process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean);
  const res = await esbuild.build({
    entryPoints: [ENTRY],
    bundle: true,
    nodePaths,
    format: 'iife',
    minify: false,
    write: false,
    platform: 'browser',
    target: 'es2018',
  });
  const bundled = res.outputFiles[0].text;
  const withLicense = `/*\n * Licensed to the Apache Software Foundation (ASF) under one\n * or more contributor license agreements.  Apache ECharts\n */\n` + bundled;
  const minified = await minify(withLicense, {
    compress: true,
    mangle: true,
    format: { comments: /Licensed to the Apache Software Foundation|Apache ECharts/ },
  });
  fs.writeFileSync(OUT, minified.code);
  console.log('echarts-custom.min.js:', (minified.code.length / 1024).toFixed(0), 'KB');
  console.log('window.echarts.init present:', /init:function|init=function|\.init=/.test(minified.code));
}

main().catch((e) => { console.error(e); process.exit(1); });
