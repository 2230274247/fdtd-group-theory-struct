const palette = {
  primary: "#0B7B6B",
  primary2: "#00746F",
  blue: "#2563EB",
  orange: "#D97706",
  red: "#D92D20",
  grid: "#E4ECEA",
  text: "#4B5563",
};

function prep(canvas) {
  if (!canvas) return null;
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  const width = Math.max(1, Math.floor(rect.width * ratio));
  const height = Math.max(1, Math.floor(rect.height * ratio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);
  return { ctx, width: rect.width, height: rect.height };
}

function range(values, fallback = [0, 1]) {
  const nums = values.map(Number).filter(Number.isFinite);
  if (!nums.length) return fallback;
  let min = Math.min(...nums);
  let max = Math.max(...nums);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  return [min, max];
}

function drawAxes(ctx, box, xLabel, yLabel) {
  ctx.strokeStyle = palette.grid;
  ctx.lineWidth = 1;
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(box.x, box.y);
  ctx.lineTo(box.x, box.y + box.h);
  ctx.lineTo(box.x + box.w, box.y + box.h);
  ctx.stroke();
  ctx.fillStyle = palette.text;
  ctx.font = "12px Microsoft YaHei, system-ui";
  ctx.textAlign = "right";
  ctx.fillText(xLabel, box.x + box.w, box.y + box.h + 34);
  ctx.save();
  ctx.translate(16, box.y + Math.min(92, box.h - 12));
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "left";
  ctx.fillText(yLabel, 0, 0);
  ctx.restore();
  ctx.textAlign = "left";
}

export function drawLine(canvas, series, options = {}) {
  const p = prep(canvas);
  if (!p) return;
  const { ctx, width, height } = p;
  const box = { x: 54, y: 22, w: width - 76, h: height - 68 };
  const data = (series || []).filter((d) => Number.isFinite(Number(d.x)) && Number.isFinite(Number(d.y)));
  drawAxes(ctx, box, options.xLabel || "λ (nm)", options.yLabel || "T");
  if (!data.length) {
    ctx.fillStyle = palette.text;
    ctx.fillText("暂无可绘制谱线", box.x + 20, box.y + 42);
    return;
  }
  const [xmin, xmax] = range(data.map((d) => d.x));
  const [ymin, ymax] = range(data.map((d) => d.y));
  const sx = (v) => box.x + ((v - xmin) / (xmax - xmin)) * box.w;
  const sy = (v) => box.y + box.h - ((v - ymin) / (ymax - ymin)) * box.h;
  ctx.strokeStyle = options.color || palette.primary;
  ctx.lineWidth = 2;
  ctx.beginPath();
  data.forEach((d, idx) => {
    const x = sx(Number(d.x));
    const y = sy(Number(d.y));
    if (idx) ctx.lineTo(x, y);
    else ctx.moveTo(x, y);
  });
  ctx.stroke();
  ctx.fillStyle = palette.text;
  ctx.fillText(`${xmin.toFixed(0)}-${xmax.toFixed(0)} nm`, box.x, box.y + box.h + 32);
}

export function drawTrend(canvas, rows, xKey = "delta", yKey = "score") {
  const data = (rows || []).map((row, index) => ({
    x: Number(row[xKey] ?? index),
    y: Number(row[yKey] ?? row.score ?? row.q ?? row.max_t),
  }));
  drawLine(canvas, data, { xLabel: xKey, yLabel: yKey, color: palette.blue });
}

export function drawHeatmap(canvas, matrix) {
  const p = prep(canvas);
  if (!p) return;
  const { ctx, width, height } = p;
  const box = { x: 72, y: 30, w: width - 148, h: height - 94 };
  const rows = matrix?.values || [];
  if (!rows.length) {
    drawAxes(ctx, box, "λ (nm)", "扰动 δ");
    ctx.fillStyle = palette.text;
    ctx.fillText("暂无热图数据", box.x + 20, box.y + 42);
    return;
  }
  const rCount = rows.length;
  const cCount = Math.max(...rows.map((r) => r.length));
  const cellW = box.w / Math.max(1, cCount);
  const cellH = box.h / Math.max(1, rCount);
  ctx.fillStyle = "#F8FAFB";
  ctx.fillRect(box.x, box.y, box.w, box.h);
  rows.forEach((row, r) => {
    row.forEach((value, c) => {
      const raw = Number(value);
      const v = Math.max(0, Math.min(1, Number.isFinite(raw) ? raw : 0));
      const hue = 188 - v * 178;
      ctx.fillStyle = `hsl(${hue} 76% ${62 - v * 16}%)`;
      ctx.fillRect(box.x + c * cellW, box.y + r * cellH, Math.ceil(cellW) + 1, Math.ceil(cellH) + 1);
    });
  });
  ctx.strokeStyle = "rgba(16, 24, 40, 0.08)";
  ctx.lineWidth = 1;
  ctx.setLineDash([3, 5]);
  for (let i = 1; i < 4; i += 1) {
    const x = box.x + (box.w * i) / 4;
    ctx.beginPath();
    ctx.moveTo(x, box.y);
    ctx.lineTo(x, box.y + box.h);
    ctx.stroke();
    const y = box.y + (box.h * i) / 4;
    ctx.beginPath();
    ctx.moveTo(box.x, y);
    ctx.lineTo(box.x + box.w, y);
    ctx.stroke();
  }
  ctx.setLineDash([]);
  drawAxes(ctx, box, matrix?.x_axis_label || matrix?.x_label || "λ (nm)", matrix?.y_axis_label || matrix?.y_label || "扰动 δ");
  const lambdas = (matrix?.lambda_grid || []).map(Number).filter(Number.isFinite);
  const deltas = (matrix?.deltas || []).map(Number).filter(Number.isFinite);
  ctx.fillStyle = palette.text;
  ctx.font = "11px Microsoft YaHei, system-ui";
  if (lambdas.length) {
    ctx.textAlign = "left";
    ctx.fillText(lambdas[0].toFixed(0), box.x, box.y + box.h + 18);
    ctx.textAlign = "center";
    ctx.fillText(lambdas[Math.floor(lambdas.length / 2)].toFixed(0), box.x + box.w / 2, box.y + box.h + 18);
    ctx.textAlign = "right";
    ctx.fillText(lambdas[lambdas.length - 1].toFixed(0), box.x + box.w, box.y + box.h + 18);
    ctx.textAlign = "left";
  }
  if (deltas.length) {
    ctx.textAlign = "right";
    ctx.fillText(deltas[0].toPrecision(3), box.x - 8, box.y + 12);
    ctx.fillText(deltas[Math.floor(deltas.length / 2)].toPrecision(3), box.x - 8, box.y + box.h / 2 + 4);
    ctx.fillText(deltas[deltas.length - 1].toPrecision(3), box.x - 8, box.y + box.h);
    ctx.textAlign = "left";
  }
  const legendX = box.x + box.w + 20;
  const legendY = box.y;
  const legendH = Math.min(150, box.h);
  for (let i = 0; i < legendH; i += 2) {
    const v = 1 - i / legendH;
    const hue = 188 - v * 178;
    ctx.fillStyle = `hsl(${hue} 76% ${62 - v * 16}%)`;
    ctx.fillRect(legendX, legendY + i, 12, 2);
  }
  ctx.fillStyle = palette.text;
  ctx.fillText("T 高", legendX + 18, legendY + 10);
  ctx.fillText("T 低", legendX + 18, legendY + legendH);
  if (Number.isFinite(Number(matrix?.raw_min)) && Number.isFinite(Number(matrix?.raw_max))) {
    ctx.fillStyle = palette.muted;
    ctx.fillText(`${Number(matrix.raw_max).toPrecision(3)}`, legendX + 18, legendY + 26);
    ctx.fillText(`${Number(matrix.raw_min).toPrecision(3)}`, legendX + 18, legendY + legendH - 16);
  }
}

export function drawDonut(canvas, value) {
  const p = prep(canvas);
  if (!p) return;
  const { ctx, width, height } = p;
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) / 2 - 6;
  const v = Math.max(0, Math.min(1, Number(value) || 0));
  ctx.lineWidth = 8;
  ctx.strokeStyle = "#E6F4F1";
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.stroke();
  ctx.strokeStyle = palette.primary;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * v);
  ctx.stroke();
  ctx.fillStyle = palette.primary;
  ctx.font = "700 13px Microsoft YaHei, system-ui";
  ctx.textAlign = "center";
  ctx.fillText(`${Math.round(v * 100)}%`, cx, cy + 5);
}
