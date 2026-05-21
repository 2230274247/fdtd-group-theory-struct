(() => {
  const $ = (id) => document.getElementById(id);
  const qs = new URLSearchParams(location.search);
  const state = {
    runId: qs.get('run_id') || '',
    payload: null,
    selectedUid: qs.get('sample_id') || '',
    compact: localStorage.getItem('spectralCompact') === '1',
    lastRows: [],
  };

  function bestRunIdFromGlobal(data) {
    const rankings = data?.rankings || {};
    const rows = rankings[targetKey()] || rankings.overall || [];
    const first = rows.find((row) => row.run_id);
    if (first?.run_id) return first.run_id;
    return data?.runs?.[0]?.run?.id || '';
  }

  const TARGET_LABELS = {
    overall: '综合',
    auto: '自动推荐',
    notch: 'notch',
    passband: 'passband',
    fano: 'Fano',
    q_mode: 'high-Q',
    edge: 'edge',
    broadband_high: '宽带高透',
    broadband_low: '宽带低透',
    flat: '平坦',
    custom: 'custom',
  };

  const COLORS = ['#0f766e', '#2563eb', '#16a34a', '#b45309', '#7c3aed', '#dc2626', '#475569', '#0891b2'];
  const PLOTLY_CONFIG = {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
  };

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[ch]));
  }

  function fmt(value, digits = 3) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '不可可靠计算';
    if (Math.abs(n) >= 1000) return n.toFixed(1);
    if (Math.abs(n) >= 10) return n.toFixed(2);
    return n.toFixed(digits);
  }

  function fileUrl(id) {
    return `/api/file?id=${encodeURIComponent(id)}`;
  }

  function targetKey() {
    const value = $('targetSelect').value;
    return value === 'auto' ? 'overall' : value;
  }

  function setStatus(text, kind = '') {
    const el = $('statusBar');
    el.textContent = text;
    el.className = `status-bar ${kind}`.trim();
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) throw new Error(data.error || `${res.status} ${res.statusText}`);
    return data;
  }

  async function load(refresh = false) {
    const target = $('targetSelect').value;
    const params = new URLSearchParams();
    if (state.runId) params.set('run_id', state.runId);
    if (target) params.set('target', target);
    if (refresh) params.set('refresh', '1');
    setStatus(state.runId ? '正在分析当前 run 的光谱...' : '正在生成全局光谱排行榜...');
    try {
      state.payload = await fetchJson(`/api/spectral-diagnostics?${params.toString()}`);
      if (!state.runId && state.payload?.mode === 'global') {
        const autoRunId = bestRunIdFromGlobal(state.payload);
        if (autoRunId) {
          state.runId = autoRunId;
          const url = new URL(location.href);
          url.searchParams.set('run_id', autoRunId);
          history.replaceState(null, '', url.toString());
          const runParams = new URLSearchParams({ run_id: autoRunId, target });
          if (refresh) runParams.set('refresh', '1');
          state.payload = await fetchJson(`/api/spectral-diagnostics?${runParams.toString()}`);
        }
      }
      if (state.payload.mode === 'run') {
        state.selectedUid = state.selectedUid || state.payload.summary?.best_uid || state.payload.items?.[0]?.uid || '';
      }
      render();
      setStatus(state.payload.mode === 'run' ? '单 run 诊断已完成。' : '全局诊断已完成。');
    } catch (err) {
      setStatus(`诊断失败：${err.message}`, 'bad');
      $('overviewCards').innerHTML = '';
    }
  }

  function render() {
    const data = state.payload;
    if (!data) return;
    $('app').classList.toggle('compact', state.compact);
    $('compactBtn').textContent = state.compact ? '舒适' : '紧凑';
    $('compactBtn').setAttribute('aria-pressed', state.compact ? 'true' : 'false');
    if (data.mode === 'run') {
      renderRun(data);
    } else {
      renderGlobal(data);
    }
  }

  function card(label, value, cls = '', sub = '') {
    return `<div class="metric-tile ${cls}"><span>${esc(label)}</span><b>${esc(value)}</b>${sub ? `<span>${esc(sub)}</span>` : ''}</div>`;
  }

  function renderOverview(summary, mode) {
    if (mode === 'global') {
      $('overviewCards').innerHTML = [
        card('run 数', summary.run_count || 0),
        card('谱线总数', summary.spectrum_count || 0),
        card('有效谱线', summary.valid_spectrum_count || 0, 'good'),
        card('高价值候选', summary.high_value_count || 0, 'good'),
        card('异常谱线', summary.abnormal_spectrum_count || 0, summary.abnormal_spectrum_count ? 'bad' : ''),
        card('缺场图 run', summary.missing_field_runs || 0, summary.missing_field_runs ? 'warn' : ''),
      ].join('');
      return;
    }
    $('overviewCards').innerHTML = [
      card('谱线数量', summary.spectrum_count || 0),
      card('有效谱线', summary.valid_spectrum_count || 0, 'good'),
      card('异常谱线', summary.abnormal_spectrum_count || 0, summary.abnormal_spectrum_count ? 'bad' : ''),
      card('高价值候选', summary.high_value_count || 0, 'good'),
      card('最佳分数', fmt(summary.best_score, 2), Number(summary.best_score) >= 60 ? 'good' : ''),
      card('推荐目标', TARGET_LABELS[summary.best_target] || summary.best_target || '-'),
      card('λ0', summary.best_lambda_nm ? `${fmt(summary.best_lambda_nm, 2)} nm` : '-'),
      card('Q', summary.best_q ? fmt(summary.best_q, 1) : '不可可靠计算'),
    ].join('');
  }

  function dataCompleteness(availability, globalSummary) {
    if (!availability && globalSummary) {
      return [
        `<div class="data-row ${globalSummary.missing_reflection_runs ? 'missing' : 'ok'}"><span>缺 R 谱 run</span><b>${esc(globalSummary.missing_reflection_runs || 0)}</b></div>`,
        `<div class="data-row ${globalSummary.missing_field_runs ? 'missing' : 'ok'}"><span>缺场图 run</span><b>${esc(globalSummary.missing_field_runs || 0)}</b></div>`,
      ].join('');
    }
    const labels = {
      transmission: 'T 谱',
      reflection: 'R 谱',
      absorption: 'A 谱',
      field: '场图',
      phase: '相位',
      poynting: 'Poynting',
    };
    return Object.entries(labels).map(([key, label]) => {
      const row = availability?.[key] || {};
      return `<div class="data-row ${row.present ? 'ok' : 'missing'}"><span>${label}</span><b>${row.present ? `${row.count || 0}` : '缺失'}</b></div>`;
    }).join('');
  }

  function selectedItem() {
    return (state.payload?.items || []).find((item) => String(item.uid) === String(state.selectedUid)) || state.payload?.items?.[0] || null;
  }

  function renderRun(data) {
    const run = data.run || {};
    $('runLabel').textContent = run.relative_path || run.name || '单 run 模式';
    renderOverview(data.summary || {}, 'run');
    $('dataCompleteness').innerHTML = dataCompleteness(data.availability);
    renderSelectedSummary(selectedItem());
    renderRanking(data.rankings?.[targetKey()] || data.rankings?.overall || [], 'run');
    renderRunCharts(data);
    renderMechanisms(data.mechanism_summary?.top || []);
    renderSupportData(data.availability, data.missing_data || []);
    renderActions(data.suggestions || []);
  }

  function renderGlobal(data) {
    $('runLabel').textContent = `全局模式 / ${data.root || ''}`;
    renderOverview(data.summary || {}, 'global');
    $('dataCompleteness').innerHTML = dataCompleteness(null, data.summary || {});
    $('selectedSummary').innerHTML = `全局候选 ${fmt(data.summary?.high_value_count || 0, 0)} 个；当前目标：${esc(TARGET_LABELS[targetKey()] || targetKey())}`;
    renderRanking(data.rankings?.[targetKey()] || data.rankings?.overall || [], 'global');
    renderGlobalCharts(data);
    renderMechanisms([]);
    renderGlobalSupport(data);
    renderActions(globalActions(data));
  }

  function renderSelectedSummary(item) {
    if (!item) {
      $('selectedSummary').textContent = '没有可分析谱线。';
      return;
    }
    const m = item.metrics || {};
    const rec = item.recommendation || {};
    const flags = (m.quality_flags || []).map((flag) => flag.message).slice(0, 3).join('；') || '未见硬性质量风险';
    const lambda = m.center_lambda_nm;
    const runId = state.payload?.run?.id || state.runId || '';
    const html = `
      <b>${esc(item.name || item.uid)}</b>
      <span>推荐：${esc(TARGET_LABELS[rec.target] || rec.target || '-')} / 置信度 ${fmt(rec.confidence || 0, 2)}</span>
      <span>λ0 ${fmt(m.center_lambda_nm, 2)} nm，FWHM ${fmt(m.line_width_nm, 3)} nm，Q ${fmt(m.q, 1)}</span>
      <span>Tmax/Tmin ${fmt(m.t_max, 4)} / ${fmt(m.t_min, 4)}，背景 ${fmt(m.background_mean, 4)}</span>
      <span>${esc(flags)}</span>
      <span class="mini-actions">
        <a class="mini-btn" href="/field_phase_poynting_viewer.html?run_id=${encodeURIComponent(runId)}&sample_id=${encodeURIComponent(item.uid || '')}&lambda_nm=${encodeURIComponent(lambda || '')}&target=${encodeURIComponent(rec.target || targetKey())}">场图查看</a>
        <a class="mini-btn" href="/spectral_compare.html?run_id=${encodeURIComponent(runId)}&sample_id=${encodeURIComponent(item.uid || '')}&target=${encodeURIComponent(rec.target || targetKey())}">加入对比</a>
        <a class="mini-btn" href="/report_preview_print.html?run_id=${encodeURIComponent(runId)}&sample_id=${encodeURIComponent(item.uid || '')}&target=${encodeURIComponent(rec.target || targetKey())}">报告</a>
      </span>
    `;
    $('selectedSummary').innerHTML = html;
    if ($('candidateQuickInfo')) $('candidateQuickInfo').innerHTML = html;
  }

  function rowRisk(row) {
    return /severe|too_few|unreliable|parse_failed|nan_ratio_high/.test(String(row.flags || ''));
  }

  function filteredRows(rows, mode) {
    const keyword = $('searchInput')?.value.trim().toLowerCase() || '';
    const scoreMin = Number($('scoreMin')?.value || 0);
    const qMin = Number($('qMin')?.value || 0);
    const hideRisk = Boolean($('hideRisk')?.checked);
    const onlyMissing = Boolean($('onlyMissing')?.checked);
    return rows.filter((row) => {
      const text = JSON.stringify(row).toLowerCase();
      if (keyword && !text.includes(keyword)) return false;
      if (Number(row.score || row.overall || 0) < scoreMin) return false;
      if (Number(row.q || 0) < qMin) return false;
      if (hideRisk && rowRisk(row)) return false;
      if (onlyMissing && mode === 'global' && !/field|reflection|absorption|missing|缺/.test(text)) return false;
      return true;
    });
  }

  function renderRanking(rows, mode) {
    const filtered = filteredRows(rows || [], mode);
    state.lastRows = filtered;
    $('rankingTitle').textContent = mode === 'global' ? '全局排行榜' : '当前 run 排行榜';
    $('rankingMeta').textContent = `${filtered.length} / ${(rows || []).length} 条；目标 ${TARGET_LABELS[targetKey()] || targetKey()}`;
    const global = mode === 'global';
    $('rankingHead').innerHTML = `<tr>
      ${global ? '<th>run</th>' : ''}
      <th>样本</th><th>目标</th><th>score</th><th>λ0 nm</th><th>FWHM nm</th><th>Q</th><th>Tmax</th><th>Tmin</th><th>质量</th><th>操作</th>
    </tr>`;
    $('rankingBody').innerHTML = filtered.slice(0, 200).map((row) => {
      const active = String(row.uid) === String(state.selectedUid);
      const risk = rowRisk(row);
      const scoreClass = Number(row.score || row.overall || 0) >= 60 ? 'score-pill' : 'neutral-pill';
      return `<tr class="${active ? 'active' : ''}" data-uid="${esc(row.uid || '')}" data-run-id="${esc(row.run_id || '')}">
        ${global ? `<td title="${esc(row.run_path || '')}">${esc(row.run_name || row.perturbation || '-')}</td>` : ''}
        <td title="${esc(row.file_name || '')}">${esc(row.name || row.uid || '-')}</td>
        <td>${esc(TARGET_LABELS[row.target] || row.target || '-')}</td>
        <td><span class="${scoreClass}">${fmt(row.score ?? row.overall, 1)}</span></td>
        <td class="num">${fmt(row.center_lambda_nm, 2)}</td>
        <td class="num">${fmt(row.fwhm_nm, 3)}</td>
        <td class="num">${fmt(row.q, 1)}</td>
        <td class="num">${fmt(row.t_max, 4)}</td>
        <td class="num">${fmt(row.t_min, 4)}</td>
        <td>${risk ? '<span class="risk-pill">风险</span>' : '<span class="neutral-pill">可用</span>'}</td>
        <td>${global && row.run_id ? `<a class="mini-btn" href="/spectral_physics_diagnostics.html?run_id=${encodeURIComponent(row.run_id)}&sample_id=${encodeURIComponent(row.uid || '')}&target=${encodeURIComponent(row.target || targetKey())}">诊断</a>` : `<a class="mini-btn" href="/field_phase_poynting_viewer.html?run_id=${encodeURIComponent(state.runId)}&sample_id=${encodeURIComponent(row.uid || '')}&lambda_nm=${encodeURIComponent(row.center_lambda_nm || '')}&target=${encodeURIComponent(row.target || targetKey())}">场图</a>`}</td>
      </tr>`;
    }).join('') || `<tr><td colspan="${global ? 11 : 10}">没有符合筛选条件的候选。</td></tr>`;
    $('rankingBody').querySelectorAll('tr[data-uid]').forEach((tr) => {
      tr.addEventListener('click', (event) => {
        if (event.target.closest('a')) return;
        if (mode === 'global') {
          const runId = tr.dataset.runId;
          if (runId) window.open(`/spectral_physics_diagnostics.html?run_id=${encodeURIComponent(runId)}`, '_blank', 'noopener');
          return;
        }
        state.selectedUid = tr.dataset.uid;
        renderRun(state.payload);
      });
    });
  }

  function plotlyLayout(title, xTitle, yTitle) {
    return {
      title: { text: title || '', font: { size: 14 } },
      margin: { l: 64, r: 28, t: title ? 48 : 24, b: 56 },
      paper_bgcolor: '#fff',
      plot_bgcolor: '#fff',
      xaxis: { title: xTitle, gridcolor: '#e9eef5', zeroline: false, tickformat: '.0f', automargin: true },
      yaxis: { title: yTitle, gridcolor: '#e9eef5', zeroline: false, automargin: true },
      legend: { orientation: 'h', y: 1.14, x: 0 },
      hovermode: 'x unified',
      font: { family: '"Microsoft YaHei", "Segoe UI", Arial, sans-serif', size: 11, color: '#20242c' },
    };
  }

  function renderLineChart(el, traces, layout) {
    if (!traces.length) {
      el.innerHTML = '<div class="empty-chart">暂无可绘制数据。</div>';
      return;
    }
    renderSvgLines(el, traces, layout);
    return;
    if (window.Plotly && !window.__plotlyLoadFailed) {
      traces.forEach((trace) => {
        if (!trace.hovertemplate) trace.hovertemplate = '%{fullData.name}<br>λ=%{x:.2f} nm<br>值=%{y:.5g}<extra></extra>';
      });
      try {
        const result = Plotly.react(el, traces, layout, PLOTLY_CONFIG);
        if (result && typeof result.catch === 'function') {
          result.catch(() => renderSvgLines(el, traces, layout));
        }
      } catch (err) {
        renderSvgLines(el, traces, layout);
      }
    } else {
      renderSvgLines(el, traces, layout);
    }
  }

  function renderSvgLines(el, traces, layout) {
    const width = Math.max(360, el.clientWidth || 640);
    const height = Math.max(220, el.clientHeight || 260);
    const pad = { l: 48, r: 18, t: 22, b: 36 };
    const allX = traces.flatMap((t) => t.x || []).map(Number).filter(Number.isFinite);
    const allY = traces.flatMap((t) => t.y || []).map(Number).filter(Number.isFinite);
    if (!allX.length || !allY.length) {
      el.innerHTML = '<div class="empty-chart">暂无可绘制数据。</div>';
      return;
    }
    const xmin = Math.min(...allX), xmax = Math.max(...allX);
    const ymin = Math.min(...allY), ymax = Math.max(...allY);
    const xspan = xmax - xmin || 1;
    const yspan = ymax - ymin || 1;
    const sx = (x) => pad.l + ((x - xmin) / xspan) * (width - pad.l - pad.r);
    const sy = (y) => height - pad.b - ((y - ymin) / yspan) * (height - pad.t - pad.b);
    const lines = traces.map((trace, idx) => {
      const pts = (trace.x || []).map((x, i) => [Number(x), Number(trace.y[i])]).filter((p) => Number.isFinite(p[0]) && Number.isFinite(p[1]));
      const d = pts.map((p) => `${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join(' ');
      return `<polyline fill="none" stroke="${trace.line?.color || COLORS[idx % COLORS.length]}" stroke-width="2" points="${d}"><title>${esc(trace.name || '')}</title></polyline>`;
    }).join('');
    el.innerHTML = `<svg class="fallback-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(layout?.title?.text || 'chart')}">
      <rect x="0" y="0" width="${width}" height="${height}" fill="#fff"/>
      <line x1="${pad.l}" y1="${height - pad.b}" x2="${width - pad.r}" y2="${height - pad.b}" stroke="#cbd5e1"/>
      <line x1="${pad.l}" y1="${pad.t}" x2="${pad.l}" y2="${height - pad.b}" stroke="#cbd5e1"/>
      ${lines}
      <text x="${pad.l}" y="${height - 8}" fill="#64748b" font-size="11">${esc(layout?.xaxis?.title || '')}</text>
      <text x="8" y="${pad.t + 10}" fill="#64748b" font-size="11">${esc(layout?.yaxis?.title || '')}</text>
      <text x="${width - pad.r - 92}" y="${pad.t + 10}" fill="#64748b" font-size="10">SVG fallback</text>
    </svg>`;
  }

  function renderRunCharts(data) {
    const item = selectedItem();
    renderSelectedSummary(item);
    if (!item) {
      ['singleSpectrum', 'traOverlay', 'multiSpectrum', 'heatmap', 'trendChart'].forEach((id) => { $(id).innerHTML = '<div class="empty-chart">没有可绘制谱线。</div>'; });
      return;
    }
    const points = item.points || [];
    $('lineMeta').textContent = `${item.file_name || item.name} / ${TARGET_LABELS[item.recommendation?.target] || item.recommendation?.target || ''}`;
    const m = item.metrics || {};
    const annotations = [];
    const shapes = [];
    if (Number.isFinite(Number(m.center_lambda_nm))) {
      shapes.push({ type: 'line', x0: m.center_lambda_nm, x1: m.center_lambda_nm, yref: 'paper', y0: 0, y1: 1, line: { color: '#dc2626', width: 1.5, dash: 'dot' } });
      annotations.push({ x: m.center_lambda_nm, yref: 'paper', y: 1.04, text: `λ0 ${fmt(m.center_lambda_nm, 2)} nm`, showarrow: false, font: { color: '#dc2626', size: 11 } });
    }
    const singleLayout = plotlyLayout('透射谱 T(λ) — 当前样本', '波长 λ (nm)', '透射率 T');
    singleLayout.shapes = shapes;
    singleLayout.annotations = annotations;
    renderLineChart($('singleSpectrum'), [{
      x: points.map((p) => p[0]),
      y: points.map((p) => p[1]),
      mode: 'lines',
      name: '透射率 T',
      line: { color: '#0f766e', width: 2 },
    }], singleLayout);
    const overlayTraces = [{
      x: points.map((p) => p[0]),
      y: points.map((p) => p[1]),
      mode: 'lines',
      name: '透射率 T',
      line: { color: '#0f766e', width: 2 },
    }];
    const overlayLayout = plotlyLayout('T / R / A 能量分布', '波长 λ (nm)', '透射率 T / 反射率 R / 吸收 A');
    if (!data.availability?.reflection?.present || !data.availability?.absorption?.present) {
      overlayLayout.annotations = [{
        xref: 'paper', yref: 'paper', x: 0.02, y: 0.96, showarrow: false, align: 'left',
        text: 'R/A 数据未导出：无法判断透射谷来自反射还是吸收。建议下一轮导出 reflection / absorption monitor。',
        font: { color: '#b45309', size: 11 },
        bgcolor: '#fff7ed',
        bordercolor: '#fed7aa',
        borderpad: 6,
      }];
    }
    renderLineChart($('traOverlay'), overlayTraces, overlayLayout);
    const topRows = (data.rankings?.[targetKey()] || data.rankings?.overall || []).slice(0, 10);
    const topItems = topRows.map((row) => data.items.find((x) => String(x.uid) === String(row.uid))).filter(Boolean);
    renderLineChart($('multiSpectrum'), topItems.map((row, idx) => ({
      x: (row.points || []).map((p) => p[0]),
      y: (row.points || []).map((p) => p[1]),
      mode: 'lines',
      name: row.name || row.uid,
      line: { color: COLORS[idx % COLORS.length], width: 1.6 },
    })), plotlyLayout('Top 候选透射谱叠加', '波长 λ (nm)', '透射率 T'));
    renderHeatmap(data.items || [], data.scan_axis || {});
    renderTrendCharts(data.items || [], data.scan_axis || {});
  }

  function interpolate(points, x) {
    if (!points?.length) return null;
    if (x <= points[0][0]) return points[0][1];
    for (let i = 1; i < points.length; i += 1) {
      if (x <= points[i][0]) {
        const [x0, y0] = points[i - 1];
        const [x1, y1] = points[i];
        const t = (x - x0) / (x1 - x0 || 1);
        return y0 + (y1 - y0) * t;
      }
    }
    return points[points.length - 1][1];
  }

  function renderHeatmap(items, axis) {
    const spectra = items.filter((item) => item.points?.length);
    if (spectra.length < 2) {
      $('heatmap').innerHTML = '<div class="empty-chart">至少需要 2 条谱线才能生成热图。</div>';
      $('heatmapMeta').textContent = '';
      return;
    }
    const xmin = Math.max(...spectra.map((item) => item.points[0][0]));
    const xmax = Math.min(...spectra.map((item) => item.points[item.points.length - 1][0]));
    if (!(xmax > xmin)) {
      $('heatmap').innerHTML = '<div class="empty-chart">谱线波长范围没有重叠。</div>';
      return;
    }
    const steps = 160;
    const x = Array.from({ length: steps }, (_, i) => xmin + (xmax - xmin) * i / (steps - 1));
    const sorted = spectra.slice().sort((a, b) => Number(a.scan_value ?? a.index ?? 0) - Number(b.scan_value ?? b.index ?? 0));
    const z = sorted.map((item) => x.map((xx) => interpolate(item.points, xx)));
    const y = sorted.map((item) => item.scan_value ?? item.index ?? item.name);
    $('heatmapMeta').textContent = `${axis.name || 'index'} / ${spectra.length} 条`;
    renderHeatmapSvg($('heatmap'), x, y, z);
    return;
    if (window.Plotly && !window.__plotlyLoadFailed) {
      try {
        const heatmapResult = Plotly.react($('heatmap'), [{
        type: 'heatmap',
        x, y, z,
        colorscale: [[0, '#f8fafc'], [0.35, '#93c5fd'], [0.7, '#0f766e'], [1, '#166534']],
        colorbar: { title: '透射率 T' },
        hovertemplate: '扫描参数=%{y}<br>波长 λ=%{x:.2f} nm<br>透射率 T=%{z:.5g}<extra></extra>',
      }], {
        margin: { l: 76, r: 28, t: 24, b: 56 },
        xaxis: { title: '波长 λ (nm)' },
        yaxis: { title: `扫描参数：${axis.name || 'index'}${axis.unit ? ` (${axis.unit})` : ''}` },
        font: { family: '"Microsoft YaHei", "Segoe UI", Arial, sans-serif', size: 11 },
      }, PLOTLY_CONFIG);
        if (heatmapResult && typeof heatmapResult.catch === 'function') {
          heatmapResult.catch(() => renderHeatmapSvg($('heatmap'), x, y, z));
        }
      } catch (err) {
        renderHeatmapSvg($('heatmap'), x, y, z);
      }
    } else {
      renderHeatmapSvg($('heatmap'), x, y, z);
    }
  }

  function renderHeatmapSvg(el, x, y, z) {
    const width = Math.max(360, el.clientWidth || 640);
    const height = Math.max(220, el.clientHeight || 260);
    const pad = { l: 48, r: 12, t: 12, b: 30 };
    const vals = z.flat().map(Number).filter(Number.isFinite);
    if (!vals.length) {
      el.innerHTML = '<div class="empty-chart">热图数据为空，无法绘制 SVG fallback。</div>';
      return;
    }
    const min = Math.min(...vals), max = Math.max(...vals);
    const cellW = (width - pad.l - pad.r) / x.length;
    const cellH = (height - pad.t - pad.b) / y.length;
    const color = (v) => {
      const t = (v - min) / (max - min || 1);
      if (t < 0.35) return '#bfdbfe';
      if (t < 0.7) return '#5eead4';
      return '#16a34a';
    };
    const rects = z.map((row, j) => row.map((v, i) => `<rect x="${pad.l + i * cellW}" y="${pad.t + j * cellH}" width="${Math.ceil(cellW)}" height="${Math.ceil(cellH)}" fill="${color(v)}"/>`).join('')).join('');
    el.innerHTML = `<svg class="fallback-svg" viewBox="0 0 ${width} ${height}"><rect width="${width}" height="${height}" fill="#fff"/>${rects}<text x="${pad.l}" y="${height - 8}" fill="#64748b" font-size="11">波长 λ (nm)</text><text x="${width - 104}" y="22" fill="#64748b" font-size="10">SVG fallback</text></svg>`;
  }

  function renderTrendCharts(items, axis) {
    const metrics = [
      ['center_lambda_nm', 'λ0', 'nm'],
      ['line_width_nm', 'FWHM', 'nm'],
      ['q', 'Q', ''],
      ['score', 'score', ''],
    ];
    $('trendMeta').textContent = axis.name ? `横轴：${axis.name}${axis.unit ? ` (${axis.unit})` : ''}` : '';
    $('trendChart').innerHTML = metrics.map((m, i) => `<div class="mini-chart" id="trendMini${i}"></div>`).join('');
    const x = items.map((item, idx) => Number(item.scan_value ?? item.index ?? idx));
    metrics.forEach(([key, label, unit], idx) => {
      const y = items.map((item) => key === 'score' ? Number(item.scores?.overall) : Number(item.metrics?.[key]));
      renderLineChart($(`trendMini${idx}`), [{
        x, y, mode: 'lines+markers', name: label, line: { color: COLORS[idx % COLORS.length], width: 2 },
      }], plotlyLayout(`${label} vs 扫描参数`, `扫描参数：${axis.name || 'index'}${axis.unit ? ` (${axis.unit})` : ''}`, unit || label));
    });
  }

  function renderGlobalCharts(data) {
    const rows = (data.rankings?.overall || []).slice(0, 30);
    const first = rows.find((row) => row.run_id);
    $('singleSpectrum').innerHTML = first ? `
      <div class="empty-chart">
        <b>全局模式显示排行榜摘要。</b>
        <p>当前最高候选：${esc(first.run_name || first.name || first.uid || '-')}，Score ${fmt(first.overall || first.score, 1)}，λ0 ${fmt(first.center_lambda_nm, 2)} nm。</p>
        <a class="mini-btn" href="/spectral_physics_diagnostics.html?run_id=${encodeURIComponent(first.run_id)}&sample_id=${encodeURIComponent(first.uid || '')}&target=${encodeURIComponent(first.target || targetKey())}">打开该 run 的谱线诊断</a>
      </div>` : '<div class="empty-chart">暂无全局候选。</div>';
    renderLineChart($('traOverlay'), [{
      x: rows.map((_, i) => i + 1),
      y: rows.map((row) => Number(row.overall || row.score || 0)),
      mode: 'lines+markers',
      name: 'overall',
      line: { color: '#0f766e', width: 2 },
    }], plotlyLayout('全局候选评分趋势', '排行榜序号', '综合评分 Score'));
    renderLineChart($('multiSpectrum'), [{
      x: rows.map((_, i) => i + 1),
      y: rows.map((row) => Number(row.q || 0)),
      mode: 'lines+markers',
      name: 'Q',
      line: { color: '#2563eb', width: 2 },
    }], plotlyLayout('全局候选 Q 值趋势', '排行榜序号', '品质因子 Q'));
    $('heatmap').innerHTML = first ? `
      <div class="empty-chart">
        <b>热图需要单个 run 的扫描序列。</b>
        <p>建议先进入最高评分 run，再查看随扰动变化的透射谱热图。</p>
        <a class="mini-btn" href="/spectral_physics_diagnostics.html?run_id=${encodeURIComponent(first.run_id)}&sample_id=${encodeURIComponent(first.uid || '')}&target=${encodeURIComponent(first.target || targetKey())}">进入单 run 热图</a>
      </div>` : '<div class="empty-chart">暂无可生成热图的候选。</div>';
    $('heatmapMeta').textContent = '';
    $('trendChart').innerHTML = `
      <div class="mini-chart" id="globalScoreMini"></div>
      <div class="mini-chart" id="globalQMini"></div>
    `;
    renderLineChart($('globalScoreMini'), [{
      x: rows.map((_, i) => i + 1),
      y: rows.map((row) => Number(row.overall || row.score || 0)),
      mode: 'lines+markers',
      name: 'Score',
      line: { color: '#0f766e', width: 2 },
    }], plotlyLayout('全局 Score 排名趋势', '排行榜序号', 'Score'));
    renderLineChart($('globalQMini'), [{
      x: rows.map((_, i) => i + 1),
      y: rows.map((row) => Number(row.q || 0)),
      mode: 'lines+markers',
      name: 'Q',
      line: { color: '#2563eb', width: 2 },
    }], plotlyLayout('全局 Q 排名趋势', '排行榜序号', 'Q'));
  }

  function renderMechanisms(list) {
    if (!list.length) {
      $('mechanisms').innerHTML = '<div class="mechanism-card"><b>等待单 run 证据</b><p>全局模式只给排行榜；进入单 run 后显示机制 Top 3。</p></div>';
      return;
    }
    $('mechanisms').innerHTML = list.map((row) => `
      <div class="mechanism-card">
        <b>${esc(row.claim || row.name)} <span class="neutral-pill">置信度 ${fmt(row.confidence || 0, 2)}</span></b>
        <p><strong>支持：</strong>${esc((row.supporting_evidence || []).join('；') || '暂无')}</p>
        <p><strong>缺失：</strong>${esc((row.missing_evidence || []).join('；') || '暂无')}</p>
        <p><strong>验证：</strong>${esc((row.next_steps || []).join('；') || '暂无')}</p>
      </div>
    `).join('');
  }

  function renderSupportData(availability, missing) {
    const labels = {
      reflection: '反射谱 R',
      absorption: '吸收/损耗 A',
      field: '场图',
      phase: '相位',
      poynting: 'Poynting',
    };
    const missingByKey = new Map((missing || []).map((row) => [row.key, row]));
    $('supportData').innerHTML = Object.entries(labels).map(([key, label]) => {
      const row = availability?.[key] || {};
      const miss = missingByKey.get(key);
      return `<div class="support-card ${row.present ? 'ok' : 'missing'}">
        <b>${esc(label)} ${row.present ? `<span class="score-pill">${row.count || 0}</span>` : '<span class="missing-pill">缺失</span>'}</b>
        <p>${esc(row.present ? '已识别，可作为下一阶段联动分析入口。' : (miss?.why || '该类数据尚未导出。'))}</p>
        <p>${esc(row.present ? (row.files || []).slice(0, 2).map((f) => f.name).join('；') : (miss?.next || '建议下一轮补充导出。'))}</p>
      </div>`;
    }).join('');
  }

  function renderGlobalSupport(data) {
    $('supportData').innerHTML = `
      <div class="support-card missing"><b>缺 R 谱 run <span class="missing-pill">${esc(data.summary?.missing_reflection_runs || 0)}</span></b><p>补 R 谱后可区分反射型共振与吸收型共振。</p></div>
      <div class="support-card missing"><b>缺场图 run <span class="missing-pill">${esc(data.summary?.missing_field_runs || 0)}</span></b><p>补场图后机制判断会更可靠。</p></div>
    `;
  }

  function renderActions(actions) {
    $('nextActions').innerHTML = (actions || []).map((row) => {
      const p = String(row.priority || 'P3').toLowerCase();
      return `<div class="action-row ${p}">
        <b>[${esc(row.priority || 'P3')}] ${esc(row.title || '')}</b>
        <p>${esc(row.reason || '')}</p>
        <p>${esc(row.detail || '')}</p>
      </div>`;
    }).join('') || '<div class="action-row p3"><b>暂无建议</b><p>当前数据不足。</p></div>';
  }

  function globalActions(data) {
    return [
      { priority: 'P1', title: '优先查看全局 Top 候选', reason: '排行榜已按目标函数汇总所有 run。', detail: '从高分候选进入单 run 页面，检查谱线、FWHM/Q 与缺失证据。' },
      { priority: 'P2', title: '补齐共性缺失数据', reason: `当前缺 R 谱 run ${data.summary?.missing_reflection_runs || 0} 个，缺场图 run ${data.summary?.missing_field_runs || 0} 个。`, detail: '优先对高分且缺证据的候选补 R/A/场图/相位/Poynting。' },
    ];
  }

  async function exportCurrent() {
    $('exportPanel').hidden = false;
    $('exportMeta').textContent = '正在生成...';
    $('exportLinks').innerHTML = '';
    try {
      const body = { run_id: state.runId, target: $('targetSelect').value };
      const data = await fetchJson('/api/spectral-export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      $('exportMeta').textContent = data.mode === 'run' ? '已写入该 run 的 12_analysis_summary' : '已写入全局汇总目录';
      $('exportLinks').innerHTML = Object.entries(data.files || {}).map(([key, id]) => `
        <div class="export-link"><span>${esc(key)}</span><a href="${fileUrl(id)}" target="_blank" rel="noopener">打开</a></div>
      `).join('') || '<div class="export-link">没有返回导出文件。</div>';
    } catch (err) {
      $('exportMeta').textContent = `导出失败：${err.message}`;
    }
  }

  function modalShell(title, body, foot = '') {
    return `<section class="spectral-modal" role="dialog" aria-modal="true">
      <div class="spectral-modal-head">
        <div><strong>${esc(title)}</strong><div class="root-path">基于当前真实诊断结果，缺失证据会保守提示。</div></div>
        <button class="btn" type="button" data-close-spectral-modal>关闭</button>
      </div>
      <div class="spectral-modal-body">${body}</div>
      <div class="spectral-modal-foot">${foot || '<button class="btn primary" type="button" data-close-spectral-modal>确定</button>'}</div>
    </section>`;
  }

  function openModal(title, body, foot = '') {
    const layer = $('spectralModal');
    if (!layer) return;
    layer.innerHTML = modalShell(title, body, foot);
    layer.classList.add('open');
    layer.setAttribute('aria-hidden', 'false');
    layer.querySelectorAll('[data-close-spectral-modal]').forEach((button) => button.addEventListener('click', closeModal));
  }

  function closeModal() {
    const layer = $('spectralModal');
    if (!layer) return;
    layer.classList.remove('open');
    layer.setAttribute('aria-hidden', 'true');
  }

  function openDrawer(title, body, foot = '') {
    const layer = $('spectralDrawer');
    if (!layer) return;
    layer.innerHTML = modalShell(title, body, foot);
    layer.classList.add('open');
    layer.setAttribute('aria-hidden', 'false');
    layer.querySelectorAll('[data-close-spectral-modal]').forEach((button) => button.addEventListener('click', closeDrawer));
  }

  function closeDrawer() {
    const layer = $('spectralDrawer');
    if (!layer) return;
    layer.classList.remove('open');
    layer.setAttribute('aria-hidden', 'true');
  }

  async function openConfigModal() {
    openModal('目标函数 / 评分规则配置', '<div class="empty-chart">正在读取配置...</div>');
    try {
      const data = await fetchJson('/api/spectral-config');
      const cfg = data.config || {};
      const targets = ['notch', 'passband', 'fano', 'q_mode', 'edge', 'broadband_high', 'broadband_low', 'flat', 'custom'];
      const body = `<div class="spectral-config-grid">
        ${targets.map((target) => `<div class="spectral-config-card">
          <strong>${esc(TARGET_LABELS[target] || target)}</strong>
          <p>${esc(JSON.stringify(cfg.targets?.[target] || cfg.scoring?.[target] || {}, null, 2) || '使用默认启发式权重。')}</p>
        </div>`).join('')}
      </div>`;
      openModal('目标函数 / 评分规则配置', body, '<button class="btn" type="button" data-close-spectral-modal>取消</button><button class="btn primary" type="button" data-close-spectral-modal>应用并重算</button>');
    } catch (err) {
      openModal('配置读取失败', `<div class="action-row p1"><b>${esc(err.message)}</b><p>请确认 server.py 正在运行。</p></div>`);
    }
  }

  function openMechanismModal() {
    const list = state.payload?.mechanism_summary?.top || [];
    if (!list.length) {
      openDrawer('物理机制判断详情', '<div class="mechanism-card"><b>全局模式暂无机制详情</b><p>进入单 run 后会显示支持证据、缺失证据和验证建议。</p></div>');
      return;
    }
    const body = `<div class="mechanism-list">${list.map((row, idx) => `
      <div class="mechanism-card">
        <b>${idx + 1}. ${esc(row.claim || row.name)} <span class="neutral-pill">置信度 ${fmt((row.confidence || 0) * 100, 0)}%</span></b>
        <p><strong>支持证据：</strong>${esc((row.supporting_evidence || []).join('；') || '暂无')}</p>
        <p><strong>缺失证据：</strong>${esc((row.missing_evidence || []).join('；') || '暂无')}</p>
        <p><strong>下一步验证：</strong>${esc((row.next_steps || []).join('；') || '暂无')}</p>
      </div>
    `).join('')}</div>`;
    openDrawer('物理机制判断详情', body);
  }

  function bind() {
    $('refreshBtn').addEventListener('click', () => load(true));
    $('targetSelect').addEventListener('change', () => load(false));
    $('compactBtn').addEventListener('click', () => {
      state.compact = !state.compact;
      localStorage.setItem('spectralCompact', state.compact ? '1' : '0');
      render();
    });
    $('exportBtn').addEventListener('click', exportCurrent);
    $('configBtn')?.addEventListener('click', openConfigModal);
    $('mechanismBtn')?.addEventListener('click', openMechanismModal);
    $('spectralModal')?.addEventListener('click', (event) => {
      if (event.target.id === 'spectralModal') closeModal();
    });
    $('spectralDrawer')?.addEventListener('click', (event) => {
      if (event.target.id === 'spectralDrawer') closeDrawer();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeModal();
        closeDrawer();
      }
    });
    ['searchInput', 'scoreMin', 'qMin', 'hideRisk', 'onlyMissing'].forEach((id) => {
      const input = $(id);
      if (!input) return;
      input.addEventListener('input', () => render());
      input.addEventListener('change', () => render());
    });
  }

  bind();
  load(false);
})();
