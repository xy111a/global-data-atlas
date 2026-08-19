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
import { LineChart, BarChart, MapChart } from 'echarts/charts';
import {
  GridComponent, TooltipComponent, LegendComponent,
  TitleComponent, AxisPointerComponent, DataZoomComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
echarts.use([
  LineChart, BarChart, MapChart,
  GridComponent, TooltipComponent, LegendComponent,
  TitleComponent, AxisPointerComponent, DataZoomComponent,
  CanvasRenderer,
]);
window.echarts = echarts;
`);

async function main() {
  const res = await esbuild.build({
    entryPoints: [ENTRY],
    bundle: true,
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
    format: { comments: false },
  });
  fs.writeFileSync(OUT, minified.code);
  console.log('echarts-custom.min.js:', (minified.code.length / 1024).toFixed(0), 'KB');
  console.log('window.echarts.init present:', /init:function|init=function|\.init=/.test(minified.code));
}

main().catch((e) => { console.error(e); process.exit(1); });
