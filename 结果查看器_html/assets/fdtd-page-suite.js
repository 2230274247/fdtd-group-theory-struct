(() => {
  const $ = (id) => document.getElementById(id);
  const qs = new URLSearchParams(location.search);

  const PAGE_META = {
    spectral_compare: {
      title: '多谱线对比分析',
      desc: '叠加候选谱线、比较关键指标，并把可疑参数区间沉淀为对比集。',
      crumb: '光谱诊断 / 多谱线对比',
      active: 'compare',
      run: true,
    },
    field_viewer: {
      title: '场图 / 相位 / Poynting 联动查看',
      desc: '以候选共振波长为锚点，联动查看场图、相位和能流数据；缺失数据会给出补导出建议。',
      crumb: '光谱诊断 / 场图联动',
      active: 'field',
      run: true,
    },
    global_leaderboard: {
      title: '全局排行榜 / 结构库探索',
      desc: '跨 run 汇总评分、Q、FWHM、数据完整度和机制线索，快速找到值得组会展示的候选。',
      crumb: '结果探索 / 全局排行榜',
      active: 'leaderboard',
      run: false,
    },
    missing_repair: {
      title: '缺失数据诊断与补算中心',
      desc: '定位缺失的 R/A/field/phase/Poynting 数据，按影响等级生成下一轮补算建议。',
      crumb: '任务中心 / 缺失补算',
      active: 'missing',
      run: false,
    },
    batch_tasks: {
      title: '批量补算任务中心',
      desc: '查看当前后台任务、补算优先队列、资源使用占位和失败原因摘要。',
      crumb: '任务中心 / 批量补算',
      active: 'tasks',
      run: false,
    },
    report_preview: {
      title: '报告预览与打印',
      desc: '把当前诊断结果整理为组会报告结构，支持触发后端 Markdown/CSV/JSON 导出。',
      crumb: '报告 / 预览与打印',
      active: 'report',
      run: true,
    },
    compare_sets: {
      title: '对比集管理',
      desc: '保存、复用和管理谱线对比集合，后续可扩展为团队共享状态。',
      crumb: '光谱诊断 / 对比集管理',
      active: 'sets',
      run: false,
    },
    data_quality: {
      title: '数据完整性与质量审计',
      desc: '审计结构、光谱、场图、命名和异常谱线质量，给出一键修复前的清单。',
      crumb: '数据治理 / 质量审计',
      active: 'quality',
      run: false,
    },
    resource_browser: {
      title: '原始文件与导出资源浏览器',
      desc: '按 run 浏览已注册的谱线、图片和分析输出文件，快速跳转到原始资源。',
      crumb: '资源 / 文件浏览器',
      active: 'resources',
      run: true,
    },
  };

  const TARGET_LABELS = {
    overall: '综合评分',
    auto: '自动推荐',
    notch: 'notch 陷波',
    passband: 'passband 带通',
    fano: 'Fano',
    q_mode: 'high-Q',
    edge: 'edge',
    broadband_high: '宽带高透',
    broadband_low: '宽带低透',
    flat: '平坦响应',
    custom: '自定义',
  };

  const COLORS = ['#006b68', '#2563eb', '#16a34a', '#f59e0b', '#dc2626', '#64748b', '#0ea5e9', '#7c3aed'];
  const PLOTLY_CONFIG = {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
  };

  const state = {
    page: document.body.dataset.page || 'global_leaderboard',
    global: null,
    run: null,
    jobs: null,
    selectedUid: '',
    selectedRows: [],
    target: qs.get('target') || 'overall',
    query: '',
  };

  let loadVersion = 0;
  let currentController = null;

  const meta = PAGE_META[state.page] || PAGE_META.global_leaderboard;

  function esc(value) {
    return String(value &#39318;&#39029; '').replace(/[&<>"']/g, (ch) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[ch]));
  }

  function fmt(value, digits = 2) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '-';
    if (Math.abs(n) >= 100000) return n.toExponential(2);
    if (Math.abs(n) >= 1000) return n.toFixed(1);
    if (Math.abs(n) >= 10) return n.toFixed(digits);
    return n.toFixed(Math.max(digits, 3)).replace(/\.?0+$/, '');
  }

  function pct(value, digits = 1) {
    const n = Number(value);
    return Number.isFinite(n) ? `${n.toFixed(digits)}%` : '-';
  }

  function clamp01(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return 0;
    return Math.max(0, Math.min(1, n));
  }

  function debounce(fn, delay = 300) {
    let timer = null;
    return function debounced(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  function icon(name) {
    const paths = {
      refresh: '<path d="M21 12a9 9 0 1 1-2.64-6.36"/><path d="M21 3v6h-6"/>',
      download: '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
      settings: '<path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z"/><path d="M19.4 15a1.8 1.8 0 0 0 .36 1.98l.03.03a2.1 2.1 0 0 1-2.97 2.97l-.03-.03A1.8 1.8 0 0 0 15 19.4a1.8 1.8 0 0 0-1 .6l-.03.03a2.1 2.1 0 0 1-3.94 0L10 20a1.8 1.8 0 0 0-1-.6 1.8 1.8 0 0 0-1.79.55l-.03.03a2.1 2.1 0 0 1-2.97-2.97l.03-.03A1.8 1.8 0 0 0 4.6 15a1.8 1.8 0 0 0-.6-1l-.03-.03a2.1 2.1 0 0 1 0-3.94L4 10a1.8 1.8 0 0 0 .6-1 1.8 1.8 0 0 0-.55-1.79l-.03-.03a2.1 2.1 0 0 1 2.97-2.97l.03.03A1.8 1.8 0 0 0 9 4.6c.38-.16.7-.38 1-.6l.03-.03a2.1 2.1 0 0 1 3.94 0L14 4c.3.22.62.44 1 .6a1.8 1.8 0 0 0 1.79-.55l.03-.03a2.1 2.1 0 0 1 2.97 2.97l-.03.03A1.8 1.8 0 0 0 19.4 9c.16.38.38.7.6 1l.03.03a2.1 2.1 0 0 1 0 3.94L20 14c-.22.3-.44.62-.6 1Z"/>',
      trophy: '<path d="M8 21h8"/><path d="M12 17v4"/><path d="M7 4h10v5a5 5 0 0 1-10 0V4Z"/><path d="M17 5h3a2 2 0 0 1-2 5h-1"/><path d="M7 5H4a2 2 0 0 0 2 5h1"/>',
      warning: '<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5"/><path d="M12 18h.01"/>',
      chart: '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 5-7"/>',
      grid: '<path d="M3 3h7v7H3Z"/><path d="M14 3h7v7h-7Z"/><path d="M14 14h7v7h-7Z"/><path d="M3 14h7v7H3Z"/>',
      file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/>',
      search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
      note: '<path d="M4 4h16v16H4Z"/><path d="M8 8h8"/><path d="M8 12h8"/><path d="M8 16h5"/>',
      task: '<path d="M9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>',
    };
    return `<svg class="wb-icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.chart}</svg>`;
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      throw new Error(data.error || `${res.status} ${res.statusText}`);
    }
    return data;
  }

  function setStatus(text) {
    if ($('statusLeft')) $('statusLeft').textContent = text;
  }

  function fileUrl(id) {
    return `/api/file?id=${encodeURIComponent(id)}`;
  }

  function runParts(run) {
    const parts = String(run?.relative_path || run?.name || '').split(/[\\/]/).filter(Boolean);
    const resultIndex = parts.lastIndexOf('results');
    const groupParts = String(run?.group || '').split('/').map((part) => part.trim()).filter(Boolean);
    return {
      structure: resultIndex >= 2 ? parts[resultIndex - 2] : (parts[1] || ''),
      mother: resultIndex >= 1 ? parts[resultIndex - 1] : (run?.structure || groupParts.at(-1) || ''),
      perturbation: resultIndex >= 0 && parts[resultIndex + 1] ? parts[resultIndex + 1] : (run?.perturbation || parts.at(-2) || ''),
      runName: run?.name || parts.at(-1) || '',
    };
  }

  function runDisplayName(run) {
    const parts = runParts(run);
    const prefix = [parts.mother, parts.perturbation].filter(Boolean).join(' / ');
    return prefix ? `${prefix} / ${parts.runName}` : (run?.name || run?.id || 'run');
  }

  function runGroupDisplayName(run) {
    const parts = runParts(run);
    const group = [parts.mother, parts.perturbation].filter(Boolean).join(' / ');
    const runName = parts.runName || run?.name || run?.id || 'run';
    return group ? `${group} / ${runName}` : runName;
  }

  function rowRunDisplayName(row) {
    return runDisplayName({
      id: row?.run_id,
      name: row?.run_name || row?.name,
      relative_path: row?.run_path,
      mother: row?.mother,
      perturbation: row?.perturbation,
    });
  }

  function pinnedRunIds() {
    try {
      return new Set(JSON.parse(localStorage.getItem('fdtd_pinned_run_ids') || '[]').map(String));
    } catch (err) {
      return new Set();
    }
  }

  function savePinnedRunIds(ids) {
    localStorage.setItem('fdtd_pinned_run_ids', JSON.stringify([...ids]));
  }

  function sortRunEntries(entries) {
    const pins = pinnedRunIds();
    return [...entries].sort((a, b) => {
      const aid = String(a.run?.id || '');
      const bid = String(b.run?.id || '');
      const pinDelta = Number(pins.has(bid)) - Number(pins.has(aid));
      if (pinDelta) return pinDelta;
      const ap = runParts(a.run);
      const bp = runParts(b.run);
      const groupDelta = `${ap.mother}\u0000${ap.perturbation}`.localeCompare(`${bp.mother}\u0000${bp.perturbation}`, 'zh-Hans-CN', { numeric: true });
      if (groupDelta) return groupDelta;
      return Number(b.run?.modified || 0) - Number(a.run?.modified || 0);
    });
  }

  function topRunId() {
    const firstRank = bestGlobalRows()[0];
    if (firstRank?.run_id) return firstRank.run_id;
    const firstRun = sortRunEntries(state.global?.runs || [])[0]?.run;
    return firstRun?.id || '';
  }

  function bestGlobalRows(target = state.target) {
    const rankings = state.global?.rankings || {};
    return rankings[target] || rankings.overall || [];
  }

  function bestRunRows(target = state.target) {
    const rankings = state.run?.rankings || {};
    return rankings[target] || rankings.overall || [];
  }

  function allRows() {
    return state.run ? bestRunRows() : bestGlobalRows();
  }

  function selectedRunId() {
    const explicit = qs.get('run_id') || qs.get('id');
    if (explicit) return explicit;
    return topRunId();
  }

  function selectedItem() {
    const items = state.run?.items || [];
    return items.find((item) => String(item.uid) === String(state.selectedUid)) || items[0] || null;
  }

  function runRecordById(id) {
    return (state.global?.runs || []).find((row) => String(row.run?.id) === String(id));
  }

  function scoreOf(row) {
    return Number(row?.score &#39318;&#39029; row?.overall &#39318;&#39029; row?.summary?.best_score &#39318;&#39029; 0);
  }

  function rowRisk(row) {
    const flags = String(row?.flags || '');
    return /negative|unreliable|too_few|nan|edge|t_gt_1|parse/i.test(flags);
  }

  function qualityClass(score, risk = false) {
    if (risk) return 'danger';
    if (Number(score) >= 75) return 'success';
    if (Number(score) >= 50) return 'warning';
    return 'info';
  }

  function compactPath(path) {
    const parts = String(path || '').split(/[\\/]/).filter(Boolean);
    if (parts.length <= 4) return parts.join(' / ');
    return `${parts[0]} / ${parts[1]} / ... / ${parts.slice(-2).join(' / ')}`;
  }

  function kpi(label, value, sub = '', kind = 'info', iconName = 'chart') {
    return `<article class="wb-kpi ${kind}">
      <div class="wb-kpi-icon">${icon(iconName)}</div>
      <div><span>${esc(label)}</span><b>${esc(value)}</b>${sub ? `<small>${esc(sub)}</small>` : ''}</div>
    </article>`;
  }

  function pageTitle(extra = '') {
    return `<div class="wb-page-title wb-context-strip">
      <div>
        <strong>${esc(state.run ? '当前 run 上下文' : '当前全局上下文')}</strong>
        <p>${esc(extra || meta.desc)}</p>
      </div>
      <div class="wb-chip-row">
        <span class="wb-pill info">${esc(TARGET_LABELS[state.target] || state.target)}</span>
        ${state.run ? `<span class="wb-pill good">${esc(runDisplayName(state.run.run))}</span>` : '<span class="wb-pill">全局模式</span>'}
      </div>
    </div>`;
  }

  function panel(title, subtitle, body, cls = '') {
    return `<section class="wb-panel ${cls}">
      <div class="wb-panel-head"><strong>${esc(title)}</strong><span>${esc(subtitle || '')}</span></div>
      <div class="wb-panel-body">${body}</div>
    </section>`;
  }

  function chartPanel(id, title, subtitle = '', extraClass = '') {
    return `<section class="wb-panel ${extraClass}">
      <div class="wb-panel-head"><strong>${esc(title)}</strong><span>${esc(subtitle)}</span></div>
      <div class="wb-chart" id="${esc(id)}"></div>
    </section>`;
  }

  function rankingTable(rows, opts = {}) {
    const limit = opts.limit || 200;
    const global = opts.global &#39318;&#39029; !state.run;
    const filtered = rows.filter((row) => {
      if (!state.query) return true;
      return JSON.stringify(row).toLowerCase().includes(state.query.toLowerCase());
    }).slice(0, limit);
    const head = `<tr>
      <th scope="col" class="col-rank">排名</th>${global ? '<th scope="col" class="col-run">run</th>' : ''}<th scope="col" class="col-name">候选</th><th scope="col" class="col-target">目标</th><th scope="col" class="col-num num">λ0 (nm)</th><th scope="col" class="col-num num">FWHM</th><th scope="col" class="col-num num">Q</th><th scope="col" class="col-score num">Score</th><th scope="col" class="col-quality">质量</th><th scope="col" class="col-action">操作</th>
    </tr>`;
    const body = filtered.map((row, idx) => {
      const score = scoreOf(row);
      const risk = rowRisk(row);
      const runId = row.run_id || state.run?.run?.id || '';
      return `<tr data-run-id="${esc(runId)}" data-uid="${esc(row.uid || '')}">
        <th scope="row">${idx + 1}</th>
        ${global ? `<td class="truncate run-display-cell" title="${esc(row.run_path || '')}">${esc(rowRunDisplayName(row))}</td>` : ''}
        <td class="truncate" title="${esc(row.file_name || '')}">${esc(row.name || row.uid || '-')}</td>
        <td>${esc(TARGET_LABELS[row.target] || row.target || '-')}</td>
        <td class="num">${fmt(row.center_lambda_nm, 2)}</td>
        <td class="num">${fmt(row.fwhm_nm, 3)}</td>
        <td class="num">${fmt(row.q, 1)}</td>
        <td class="num"><div class="wb-scorebar" title="${fmt(score, 2)}"><span style="width:${Math.max(2, Math.min(100, score))}%"></span></div></td>
        <td><span class="wb-pill ${risk ? 'bad' : 'good'}">${risk ? '风险' : '可用'}</span></td>
        <td><a class="wb-pill info" href="/spectral_physics_diagnostics.html?run_id=${encodeURIComponent(runId)}&sample_id=${encodeURIComponent(row.uid || '')}&target=${encodeURIComponent(row.target || state.target)}">诊断</a></td>
      </tr>`;
    }).join('');
    return `<div class="wb-table-shell"><div class="wb-table-scroll"><table class="wb-table"><thead>${head}</thead><tbody>${body || `<tr><td colspan="${global ? 10 : 9}">暂无数据</td></tr>`}</tbody></table></div></div>`;
  }

  function missingRows() {
    const rows = [];
    (state.global?.runs || []).forEach((entry) => {
      const run = entry.run || {};
      (entry.missing_data || []).forEach((miss) => {
        rows.push({
          run_id: run.id,
          run_name: runDisplayName(run),
          run_path: run.relative_path,
          key: miss.key,
          label: miss.label,
          why: miss.why,
          next: miss.next,
          best_score: entry.summary?.best_score,
          spectra: entry.summary?.spectrum_count || 0,
        });
      });
    });
    return rows;
  }

  function availabilityRows() {
    const keys = ['transmission', 'reflection', 'absorption', 'field', 'phase', 'poynting'];
    return keys.map((key) => {
      const total = state.global?.runs?.length || 0;
      const present = (state.global?.runs || []).filter((entry) => entry.availability?.[key]?.present).length;
      return { key, total, present, pct: total ? present / total * 100 : 0 };
    });
  }

  function mechanismRows() {
    const buckets = new Map();
    bestGlobalRows().forEach((row) => {
      const key = row.target || 'unknown';
      buckets.set(key, (buckets.get(key) || 0) + 1);
    });
    return [...buckets.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6);
  }

  function lineLayout(xTitle, yTitle, title = '') {
    return {
      title: { text: title, font: { size: 12 } },
      margin: { l: 64, r: 28, t: title ? 48 : 24, b: 56 },
      paper_bgcolor: '#fff',
      plot_bgcolor: '#fff',
      xaxis: { title: xTitle, gridcolor: '#e9eef5', zeroline: false, tickformat: '.0f', automargin: true },
      yaxis: { title: yTitle, gridcolor: '#e9eef5', zeroline: false, automargin: true },
      legend: { orientation: 'h', x: 0, y: 1.16 },
      hovermode: 'x unified',
      font: { family: '"Microsoft YaHei", "Segoe UI", Arial, sans-serif', size: 11, color: '#0f1f33' },
    };
  }

  function renderLineChart(el, traces, layout) {
    if (!el) return;
    const good = traces.map((trace) => {
      const points = (trace.x || []).map((x, index) => [x, (trace.y || [])[index]])
        .filter((point) => point[0] !== undefined && point[0] !== null && point[0] !== '' && Number.isFinite(Number(point[1])));
      return { ...trace, x: points.map((point) => point[0]), y: points.map((point) => point[1]) };
    }).filter((trace) => (trace.x || []).length && (trace.y || []).length);
    if (!good.length) {
      el.innerHTML = '<div class="wb-empty">暂无可绘制数据。若本 run 有 Excel 谱线，请刷新或从左侧重新选择 run。</div>';
      return;
    }
    renderSvgLines(el, good, layout);
    return;
    if (window.Plotly && !window.__plotlyLoadFailed) {
      good.forEach((trace) => {
        if (!trace.hovertemplate) {
          trace.hovertemplate = '%{fullData.name}<br>x=%{x}<br>y=%{y:.4g}<extra></extra>';
        }
      });
      try {
        const result = Plotly.react(el, good, layout, PLOTLY_CONFIG);
        if (result && typeof result.catch === 'function') {
          result.catch(() => renderSvgLines(el, good, layout));
        }
      } catch (err) {
        renderSvgLines(el, good, layout);
      }
      return;
    }
    renderSvgLines(el, good, layout);
  }

  function renderScatterChart(el, rows) {
    const good = (rows || []).filter((row) => Number.isFinite(Number(row.fwhm_nm)) && Number.isFinite(Number(row.q)));
    if (!el) return;
    if (!good.length) {
      el.innerHTML = '<div class="wb-empty">暂无可绘制的 FWHM/Q 候选；请先生成含 FWHM 与 Q 的诊断数据。</div>';
      return;
    }
    renderSvgScatter(el, good);
    return;
    if (window.Plotly && !window.__plotlyLoadFailed) {
      try {
        const result = Plotly.react(el, [{
          type: 'scatter',
          mode: 'markers',
          x: good.map((row) => Number(row.fwhm_nm)),
          y: good.map((row) => Number(row.q)),
          text: good.map((row) => `${rowRunDisplayName(row)} / ${row.name || row.uid || ''}`),
          marker: {
            size: good.map((row) => 8 + clamp01(scoreOf(row) / 100) * 14),
            color: good.map((row) => scoreOf(row)),
            colorscale: [[0, '#dc2626'], [0.5, '#f59e0b'], [1, '#16a34a']],
            line: { color: '#ffffff', width: 1 },
            showscale: true,
            colorbar: { title: 'Score' },
          },
          hovertemplate: '%{text}<br>FWHM=%{x:.4g} nm<br>Q=%{y:.4g}<extra></extra>',
        }], lineLayout('线宽 FWHM (nm)', '品质因子 Q', 'Q-FWHM 候选分布图'), PLOTLY_CONFIG);
        if (result && typeof result.catch === 'function') result.catch(() => renderSvgScatter(el, good));
      } catch (err) {
        renderSvgScatter(el, good);
      }
      return;
    }
    renderSvgScatter(el, good);
  }

  function renderSvgScatter(el, rows) {
    const width = Math.max(420, el.clientWidth || 720);
    const height = Math.max(240, el.clientHeight || 300);
    const pad = { l: 52, r: 18, t: 22, b: 38 };
    const xs = rows.map((row) => Number(row.fwhm_nm));
    const ys = rows.map((row) => Number(row.q));
    const xmin = Math.min(...xs), xmax = Math.max(...xs);
    const ymin = Math.min(...ys), ymax = Math.max(...ys);
    const xspan = xmax - xmin || 1;
    const yspan = ymax - ymin || 1;
    const sx = (x) => pad.l + (x - xmin) / xspan * (width - pad.l - pad.r);
    const sy = (y) => height - pad.b - (y - ymin) / yspan * (height - pad.t - pad.b);
    const dots = rows.map((row) => {
      const score = scoreOf(row);
      const color = score >= 75 ? '#16a34a' : score >= 50 ? '#f59e0b' : '#dc2626';
      return `<circle cx="${sx(Number(row.fwhm_nm)).toFixed(1)}" cy="${sy(Number(row.q)).toFixed(1)}" r="${(5 + clamp01(score / 100) * 7).toFixed(1)}" fill="${color}" opacity="0.78"><title>${esc(rowRunDisplayName(row))} / Score ${fmt(score, 1)}</title></circle>`;
    }).join('');
    el.innerHTML = `<svg class="fallback-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Q-FWHM 候选分布图">
      <rect width="${width}" height="${height}" fill="#fff"/>
      <line x1="${pad.l}" y1="${height - pad.b}" x2="${width - pad.r}" y2="${height - pad.b}" stroke="#cbd5e1"/>
      <line x1="${pad.l}" y1="${pad.t}" x2="${pad.l}" y2="${height - pad.b}" stroke="#cbd5e1"/>
      ${dots}
      <text x="${pad.l}" y="${height - 9}" fill="#64748b" font-size="11">线宽 FWHM (nm)</text>
      <text x="8" y="${pad.t + 10}" fill="#64748b" font-size="11">品质因子 Q</text>
      <text x="${width - 104}" y="22" fill="#64748b" font-size="10">SVG scatter</text>
    </svg>`;
  }

  function renderSvgLines(el, traces, layout) {
    const width = Math.max(420, el.clientWidth || 720);
    const height = Math.max(240, el.clientHeight || 300);
    const pad = { l: 52, r: 18, t: 22, b: 38 };
    const rawX = traces.flatMap((t) => t.x || []).filter((x) => x !== undefined && x !== null && x !== '');
    const categoricalX = rawX.some((x) => !Number.isFinite(Number(x)));
    const categories = categoricalX ? [...new Set(rawX.map((x) => String(x)))] : [];
    const allX = categoricalX ? rawX.map((x) => categories.indexOf(String(x))).filter((x) => x >= 0) : rawX.map(Number).filter(Number.isFinite);
    const allY = traces.flatMap((t) => t.y || []).map(Number).filter(Number.isFinite);
    if (!allX.length || !allY.length) {
      el.innerHTML = '<div class="wb-empty">暂无可绘制数据</div>';
      return;
    }
    const xmin = Math.min(...allX), xmax = Math.max(...allX);
    const ymin = Math.min(...allY), ymax = Math.max(...allY);
    const xspan = xmax - xmin || 1;
    const yspan = ymax - ymin || 1;
    const sx = (x) => pad.l + (Number(x) - xmin) / xspan * (width - pad.l - pad.r);
    const sy = (y) => height - pad.b - (Number(y) - ymin) / yspan * (height - pad.t - pad.b);
    const xValue = (x) => categoricalX ? categories.indexOf(String(x)) : Number(x);
    const barWidth = categoricalX ? Math.max(10, Math.min(42, (width - pad.l - pad.r) / Math.max(categories.length, 1) * 0.58)) : 10;
    const lines = traces.map((trace, idx) => {
      const points = (trace.x || []).map((x, i) => [xValue(x), Number(trace.y[i]), x]).filter((p) => Number.isFinite(p[0]) && Number.isFinite(p[1]));
      if (trace.type === 'bar') {
        const baseY = sy(Math.min(0, ymin));
        return points.map((p) => {
          const y = sy(p[1]);
          const h = Math.max(1, Math.abs(baseY - y));
          const top = Math.min(baseY, y);
          return `<rect x="${(sx(p[0]) - barWidth / 2).toFixed(1)}" y="${top.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${h.toFixed(1)}" rx="4" fill="${trace.marker?.color || trace.line?.color || COLORS[idx % COLORS.length]}" opacity="0.82"><title>${esc(String(p[2]))}: ${fmt(p[1], 2)}</title></rect>`;
        }).join('');
      }
      const d = points.map((p) => `${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join(' ');
      return `<polyline points="${d}" fill="none" stroke="${trace.line?.color || COLORS[idx % COLORS.length]}" stroke-width="${trace.line?.width || 2}"><title>${esc(trace.name || '')}</title></polyline>`;
    }).join('');
    const ticks = categoricalX
      ? categories.slice(0, 10).map((label, index) => `<text x="${sx(index).toFixed(1)}" y="${height - 20}" fill="#64748b" font-size="10" text-anchor="middle">${esc(label).slice(0, 10)}</text>`).join('')
      : '';
    el.innerHTML = `<svg class="fallback-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(layout?.title?.text || 'chart')}">
      <rect width="${width}" height="${height}" fill="#fff"/>
      <line x1="${pad.l}" y1="${height - pad.b}" x2="${width - pad.r}" y2="${height - pad.b}" stroke="#cbd5e1"/>
      <line x1="${pad.l}" y1="${pad.t}" x2="${pad.l}" y2="${height - pad.b}" stroke="#cbd5e1"/>
      ${lines}
      ${ticks}
      <text x="${pad.l}" y="${height - 9}" fill="#64748b" font-size="11">${esc(layout?.xaxis?.title || '')}</text>
      <text x="8" y="${pad.t + 10}" fill="#64748b" font-size="11">${esc(layout?.yaxis?.title || '')}</text>
      <text x="${width - 104}" y="22" fill="#64748b" font-size="10">SVG fallback</text>
    </svg>`;
  }

  function renderHeatmap(el, items) {
    const spectra = (items || []).filter((item) => item.points?.length);
    if (spectra.length < 2) {
      el.innerHTML = '<div class="wb-empty">至少需要 2 条谱线才能生成热图</div>';
      return;
    }
    const xmin = Math.max(...spectra.map((item) => item.points[0][0]));
    const xmax = Math.min(...spectra.map((item) => item.points[item.points.length - 1][0]));
    if (!(xmax > xmin)) {
      el.innerHTML = '<div class="wb-empty">谱线波长范围没有重叠，无法生成热图</div>';
      return;
    }
    const steps = 150;
    const x = Array.from({ length: steps }, (_, i) => xmin + (xmax - xmin) * i / (steps - 1));
    const sorted = spectra.slice().sort((a, b) => Number(a.scan_value &#39318;&#39029; a.index &#39318;&#39029; 0) - Number(b.scan_value &#39318;&#39029; b.index &#39318;&#39029; 0));
    const y = sorted.map((item) => item.scan_value &#39318;&#39029; item.index &#39318;&#39029; item.name);
    const z = sorted.map((item) => x.map((xx) => interp(item.points, xx)));
    renderHeatmapSvg(el, x, y, z);
    return;
    if (window.Plotly && !window.__plotlyLoadFailed) {
      try {
        const heatmapResult = Plotly.react(el, [{ type: 'heatmap', x, y, z, colorscale: [[0, '#f8fafc'], [0.38, '#9be3dd'], [0.72, '#19a091'], [1, '#003f42']], colorbar: { title: '透射率 T' }, hovertemplate: '扫描参数=%{y}<br>波长 λ=%{x:.2f} nm<br>透射率 T=%{z:.4g}<extra></extra>' }], {
        margin: { l: 76, r: 28, t: 24, b: 56 },
        xaxis: { title: '波长 λ (nm)' },
        yaxis: { title: `扫描参数：${state.run?.scan_axis?.name || 'index'}${state.run?.scan_axis?.unit ? ` (${state.run.scan_axis.unit})` : ''}` },
        font: { family: '"Microsoft YaHei", "Segoe UI", Arial, sans-serif', size: 11 },
      }, PLOTLY_CONFIG);
        if (heatmapResult && typeof heatmapResult.catch === 'function') {
          heatmapResult.catch(() => renderHeatmapSvg(el, x, y, z));
        }
      } catch (err) {
        renderHeatmapSvg(el, x, y, z);
      }
      return;
    }
    renderHeatmapSvg(el, x, y, z);
  }

  function interp(points, x) {
    if (!points?.length) return null;
    if (x <= points[0][0]) return points[0][1];
    for (let i = 1; i < points.length; i += 1) {
      if (x <= points[i][0]) {
        const [x0, y0] = points[i - 1];
        const [x1, y1] = points[i];
        return y0 + (y1 - y0) * (x - x0) / (x1 - x0 || 1);
      }
    }
    return points[points.length - 1][1];
  }

  function renderHeatmapSvg(el, x, y, z) {
    const width = Math.max(420, el.clientWidth || 720);
    const height = Math.max(240, el.clientHeight || 300);
    const pad = { l: 52, r: 12, t: 12, b: 32 };
    const vals = z.flat().map(Number).filter(Number.isFinite);
    if (!vals.length) {
      el.innerHTML = '<div class="wb-empty">热图数据为空，无法绘制 SVG fallback</div>';
      return;
    }
    const min = Math.min(...vals), max = Math.max(...vals);
    const cellW = (width - pad.l - pad.r) / x.length;
    const cellH = (height - pad.t - pad.b) / y.length;
    const color = (v) => {
      const t = (Number(v) - min) / (max - min || 1);
      if (t < 0.32) return '#dbeafe';
      if (t < 0.62) return '#99f6e4';
      if (t < 0.82) return '#34d399';
      return '#047857';
    };
    const rects = z.map((row, j) => row.map((v, i) => `<rect x="${pad.l + i * cellW}" y="${pad.t + j * cellH}" width="${Math.ceil(cellW)}" height="${Math.ceil(cellH)}" fill="${color(v)}"/>`).join('')).join('');
    el.innerHTML = `<svg class="fallback-svg" viewBox="0 0 ${width} ${height}">
      <rect width="${width}" height="${height}" fill="#fff"/>${rects}
      <text x="${pad.l}" y="${height - 9}" fill="#64748b" font-size="11">波长 λ (nm)</text>
      <text x="${width - 104}" y="22" fill="#64748b" font-size="10">SVG fallback</text>
    </svg>`;
  }

  function renderSidebar() {
    const list = $('sideRunList');
    if (!list) return;
    const keyword = ($('sideSearch')?.value || '').trim().toLowerCase();
    const runs = sortRunEntries(state.global?.runs || []).filter((entry) => {
      const text = `${runGroupDisplayName(entry.run)} ${entry.run?.name || ''} ${entry.run?.relative_path || ''}`.toLowerCase();
      return !keyword || text.includes(keyword);
    }).slice(0, 180);
    const pins = pinnedRunIds();
    list.innerHTML = runs.map((entry) => {
      const score = Number(entry.summary?.best_score || 0);
      const cls = score >= 75 ? '' : score >= 45 ? 'warn' : 'bad';
      const id = entry.run?.id || '';
      const active = state.run?.run?.id && String(state.run.run.id) === String(id);
      const pinned = pins.has(String(id));
      return `<a class="wb-run-item ${active ? 'active' : ''}" href="/${state.page === 'global_leaderboard' ? 'spectral_physics_diagnostics.html' : location.pathname.split('/').pop()}?run_id=${encodeURIComponent(id)}" title="${esc(entry.run?.relative_path || '')}">
        <span class="wb-run-dot ${cls}"></span><span class="wb-run-name">${esc(runGroupDisplayName(entry.run))}</span><span class="wb-run-score">${pinned ? '顶 ' : ''}${fmt(score, 0)}</span><span class="wb-pin" role="button" tabindex="0" data-pin-run="${esc(id)}" aria-label="${pinned ? '取消置顶' : '置顶'}">${pinned ? '★' : '☆'}</span>
      </a>`;
    }).join('') || '<div class="wb-empty">没有匹配 run</div>';
    list.querySelectorAll('[data-pin-run]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        const ids = pinnedRunIds();
        const id = String(button.dataset.pinRun || '');
        if (ids.has(id)) ids.delete(id);
        else ids.add(id);
        savePinnedRunIds(ids);
        renderSidebar();
      });
      button.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        button.click();
      });
    });
    if ($('sideFoot')) {
      const s = state.global?.summary || {};
      $('sideFoot').textContent = `共 ${s.run_count || 0} run，${s.spectrum_count || 0} 条谱线，缺场图 ${s.missing_field_runs || 0} 个 run`;
    }
  }

  function renderTopShell() {
    document.title = `FDTD 光谱物理诊断工作台 - ${meta.title}`;
    if ($('pageCrumb')) {
      $('pageCrumb').className = 'wb-title-block';
      const crumbParts = String(meta.crumb || '').split('/').map((part) => part.trim()).filter(Boolean);
      const crumbLinks = [
        '<a href="/index.html">&#39318;&#39029;</a>',
        ...crumbParts.map((part, index) => index === 0
          ? `<a href="/global_spectral_leaderboard.html">${esc(part)}</a>`
          : `<span>${esc(part)}</span>`),
        `<b>${esc(meta.title)}</b>`,
      ].join(' <span>&#8250;</span> ');
      $('pageCrumb').innerHTML = `<div class="wb-breadcrumb">${crumbLinks}</div><h1>${esc(meta.title)}</h1><p>${esc(meta.desc)}</p>`;
    }
    document.querySelectorAll('[data-nav]').forEach((node) => {
      node.classList.toggle('active', node.dataset.nav === meta.active);
    });
    if ($('targetMode')) $('targetMode').value = state.target;
  }

  function renderKpis() {
    const s = state.global?.summary || {};
    const rows = bestGlobalRows();
    const best = rows[0] || {};
    return `<section class="wb-kpi-grid">
      ${kpi('可用 runs', s.run_count || 0, '包含当前扫描缓存', 'info', 'grid')}
      ${kpi('总谱线数', s.spectrum_count || 0, 'T 谱已纳入评分', 'info', 'chart')}
      ${kpi('高价值候选', s.high_value_count || 0, 'Score ≥ 60', 'success', 'trophy')}
      ${kpi('异常谱线', s.abnormal_spectrum_count || 0, 'T>1、负值或质量门控', s.abnormal_spectrum_count ? 'danger' : 'success', 'warning')}
      ${kpi('缺 R 谱 run', s.missing_reflection_runs || 0, '用于区分反射/吸收机制', s.missing_reflection_runs ? 'warning' : 'success', 'file')}
      ${kpi('最高评分', fmt(best.overall &#39318;&#39029; best.score, 1), rowRunDisplayName(best) || best.name || '暂无', qualityClass(scoreOf(best)), 'trophy')}
    </section>`;
  }

  function renderGlobalLeaderboard() {
    const rows = bestGlobalRows();
    $('pageRoot').innerHTML = [
      pageTitle(),
      renderKpis(),
      `<section class="wb-grid sidebar">
        ${panel('全局排行榜', `${rows.length} 条候选`, rankingTable(rows, { global: true }))}
        ${chartPanel('qScatter', 'Q-FWHM 候选分布图', 'x=线宽，y=品质因子，颜色=评分', 'short')}
      </section>`,
      `<section class="wb-grid two">
        ${panel('全局数据完整度', '按数据类型统计', availabilityProgress())}
        ${panel('结构库热门机制线索', '由目标推荐聚类得到', mechanismProgress())}
      </section>`,
      quickActions(),
    ].join('');
    renderScatter();
  }

  function availabilityProgress() {
    const labels = { transmission: 'T 谱', reflection: 'R 谱', absorption: 'A 谱', field: '场图', phase: '相位', poynting: 'Poynting' };
    return `<div class="wb-progress-list">${availabilityRows().map((row) => `
      <div class="wb-progress-row"><b>${esc(labels[row.key] || row.key)}</b><div class="wb-progress-track"><span style="width:${row.pct}%"></span></div><span>${pct(row.pct, 0)}</span></div>
    `).join('')}</div>`;
  }

  function mechanismProgress() {
    const total = Math.max(1, mechanismRows().reduce((sum, row) => sum + row[1], 0));
    return `<div class="wb-progress-list">${mechanismRows().map(([key, count], idx) => `
      <div class="wb-progress-row"><b>${esc(TARGET_LABELS[key] || key)}</b><div class="wb-progress-track"><span style="width:${count / total * 100}%; background:${COLORS[idx % COLORS.length]}"></span></div><span>${pct(count / total * 100, 0)}</span></div>
    `).join('')}</div>`;
  }

  function quickActions() {
    return panel('快速操作', '从这里进入常用工作流', `<div class="wb-chip-row">
      <a class="wb-btn primary" href="/spectral_physics_diagnostics.html">${icon('chart')}光谱诊断</a>
      <a class="wb-btn" href="/missing_data_repair_center.html">${icon('warning')}缺失补算</a>
      <a class="wb-btn" href="/resource_file_browser.html">${icon('file')}资源浏览</a>
      <a class="wb-btn" href="/report_preview_print.html?run_id=${encodeURIComponent(selectedRunId())}">${icon('download')}报告预览</a>
    </div>`);
  }

  function renderScatter() {
    const rows = bestGlobalRows().slice(0, 120).filter((row) => Number.isFinite(Number(row.fwhm_nm)) && Number.isFinite(Number(row.q)));
    renderScatterChart($('qScatter'), rows);
  }

  function renderMissingRepair() {
    const rows = missingRows();
    const high = rows.filter((row) => Number(row.best_score || 0) >= 60).length;
    const byKey = rows.reduce((map, row) => map.set(row.key, (map.get(row.key) || 0) + 1), new Map());
    $('pageRoot').innerHTML = [
      pageTitle(),
      `<section class="wb-kpi-grid">
        ${kpi('缺失总数', rows.length, '按 run × 数据类型统计', rows.length ? 'warning' : 'success', 'warning')}
        ${kpi('高影响缺失', high, '高分候选仍缺关键证据', high ? 'danger' : 'success', 'warning')}
        ${kpi('缺 R 谱', byKey.get('reflection') || 0, '机制判据优先补齐', 'warning', 'file')}
        ${kpi('缺场图', byKey.get('field') || 0, '共振模式证据', 'warning', 'grid')}
        ${kpi('缺相位', byKey.get('phase') || 0, 'Fano / 拓扑证据', 'info', 'chart')}
        ${kpi('缺 Poynting', byKey.get('poynting') || 0, '能流验证', 'info', 'chart')}
      </section>`,
      `<section class="wb-grid sidebar">
        ${panel('缺失片段列表', `${rows.length} 条`, missingTable(rows))}
        ${panel('自动补算建议', '按优先级合并', missingSuggestions(rows))}
      </section>`,
      `<section class="wb-grid two">${chartPanel('missingBar', '缺失数据类型统计', 'x=数据类型，y=缺失数量')}${panel('数据完整度', '当前结果库', availabilityProgress())}</section>`,
    ].join('');
    renderMissingBar(rows);
  }

  function missingTable(rows) {
    const body = rows.slice(0, 260).map((row) => `<tr>
      <td class="truncate" title="${esc(row.run_name)}">${esc(row.run_name)}</td><td>${esc(row.label || row.key)}</td><td class="num">${fmt(row.best_score, 1)}</td><td class="truncate" title="${esc(row.run_path)}">${esc(compactPath(row.run_path))}</td>
      <td class="truncate" title="${esc(row.next)}">${esc(row.next)}</td><td><a class="wb-pill info" href="/spectral_physics_diagnostics.html?run_id=${encodeURIComponent(row.run_id)}">查看</a></td>
    </tr>`).join('');
    return `<div class="wb-table-shell"><div class="wb-table-scroll"><table class="wb-table"><thead><tr><th class="col-run">run</th><th class="col-target">缺失类型</th><th class="col-num num">最佳分</th><th class="col-name">路径</th><th>建议动作</th><th class="col-action">操作</th></tr></thead><tbody>${body || '<tr><td colspan="6">没有缺失项</td></tr>'}</tbody></table></div></div>`;
  }

  function missingSuggestions(rows) {
    const top = ['reflection', 'absorption', 'field', 'phase', 'poynting'].map((key) => rows.filter((row) => row.key === key));
    const labels = { reflection: '补齐 R 谱', absorption: '补齐 A 谱', field: '导出场图', phase: '导出相位', poynting: '导出 Poynting' };
    return `<div class="wb-list">${top.filter((group) => group.length).map((group, idx) => `
      <div class="wb-list-row ${idx < 2 ? 'bad' : 'warn'}">
        <strong>${idx + 1}. ${esc(labels[group[0].key] || group[0].key)} <span class="wb-pill warn">${group.length} 项</span></strong>
        <p>${esc(group[0].why || group[0].next || '建议优先补齐高分候选。')}</p>
        <p>${esc(group.slice(0, 3).map((row) => row.run_name).join('；'))}</p>
      </div>
    `).join('') || '<div class="wb-empty">当前没有补算建议</div>'}</div>`;
  }

  function renderMissingBar(rows) {
    const buckets = [...rows.reduce((map, row) => map.set(row.label || row.key, (map.get(row.label || row.key) || 0) + 1), new Map()).entries()];
    renderLineChart($('missingBar'), [{
      x: buckets.map((row) => row[0]),
      y: buckets.map((row) => row[1]),
      type: 'bar',
      name: 'missing',
      marker: { color: '#f59e0b' },
      line: { color: '#f59e0b' },
    }], lineLayout('缺失数据类型', '缺失数量 (项)', '缺失数据类型统计'));
  }

  function renderBatchTasks() {
    const jobs = state.jobs?.jobs || [];
    const active = jobs.filter((job) => job.running).length;
    $('pageRoot').innerHTML = [
      pageTitle(),
      `<section class="wb-kpi-grid">
        ${kpi('运行中任务', active, '来自现有 /api/jobs', active ? 'info' : 'success', 'task')}
        ${kpi('排队建议', missingRows().length, '缺失数据可转补算', 'warning', 'warning')}
        ${kpi('近期待处理', jobs.length, '最近 20 个 job', 'info', 'file')}
        ${kpi('高影响缺失', missingRows().filter((row) => Number(row.best_score || 0) >= 60).length, '建议先补高分候选', 'danger', 'warning')}
        ${kpi('资源池', '占位', '后续接 GPU/CPU 池', 'info', 'grid')}
        ${kpi('成功率', '待接入', '后续从任务日志统计', 'info', 'chart')}
      </section>`,
      `<section class="wb-grid sidebar">
        ${panel('任务队列', `${jobs.length} 条`, jobTable(jobs))}
        ${panel('批量操作', '当前为安全占位', taskActions())}
      </section>`,
      `<section class="wb-grid two">${chartPanel('taskTrend', '任务进度趋势', 'x=任务序号，y=完成进度')}${panel('失败原因 Top', '从日志接入前的占位', failureReasons())}</section>`,
    ].join('');
    renderTaskTrend(jobs);
  }

  function jobTable(jobs) {
    const body = jobs.map((job) => `<tr><td>${esc(job.id || '-')}</td><td>${esc(job.title || job.kind || '-')}</td><td>${esc(job.running ? '运行中' : '结束')}</td><td>${fmt(job.progress || 0, 0)}%</td><td>${esc(job.started_text || job.started || '-')}</td></tr>`).join('');
    return `<div class="wb-table-shell"><div class="wb-table-scroll"><table class="wb-table"><thead><tr><th class="col-run">任务 ID</th><th class="col-name">来源</th><th class="col-target">状态</th><th class="col-num num">进度</th><th class="col-run">开始</th></tr></thead><tbody>${body || '<tr><td colspan="5">当前没有后台任务</td></tr>'}</tbody></table></div></div>`;
  }

  function taskActions() {
    return `<div class="wb-list">
      <div class="wb-list-row bad"><strong>高优先级：补齐高分候选缺失证据</strong><p>先对高分且缺 R/A/场图的 run 创建重算脚本，避免低证据结论进入报告。</p></div>
      <div class="wb-list-row warn"><strong>中优先级：加密 FWHM 不稳定区间</strong><p>围绕 λ0 和 FWHM 急剧变化区域细化扫描步长。</p></div>
      <div class="wb-list-row info"><strong>低优先级：补充 Poynting / 相位联动</strong><p>用于机制验证，建议在 Top 候选确定后执行。</p></div>
    </div>`;
  }

  function failureReasons() {
    return `<div class="wb-progress-list">
      <div class="wb-progress-row"><b>Monitor 缺失</b><div class="wb-progress-track"><span style="width:38%; background:#f59e0b"></span></div><span>38%</span></div>
      <div class="wb-progress-row"><b>采样不足</b><div class="wb-progress-track"><span style="width:27%; background:#2563eb"></span></div><span>27%</span></div>
      <div class="wb-progress-row"><b>不收敛风险</b><div class="wb-progress-track"><span style="width:19%; background:#dc2626"></span></div><span>19%</span></div>
      <div class="wb-progress-row"><b>文件命名不一</b><div class="wb-progress-track"><span style="width:16%; background:#64748b"></span></div><span>16%</span></div>
    </div>`;
  }

  function renderTaskTrend(jobs) {
    const x = jobs.length ? jobs.map((_, i) => i + 1) : [1, 2, 3, 4, 5];
    const y = jobs.length ? jobs.map((job) => Number(job.progress || 0)) : [0, 18, 42, 68, 100];
    renderLineChart($('taskTrend'), [{ x, y, mode: 'lines+markers', name: '任务进度', line: { color: '#006b68' } }], lineLayout('任务序号', '完成进度 (%)', '任务进度趋势'));
  }

  function renderSpectralCompare() {
    if (!state.run) {
      $('pageRoot').innerHTML = pageTitle('正在自动选择评分最高的 run...');
      return;
    }
    const rows = bestRunRows().slice(0, 8);
    const items = state.run?.items || [];
    const rowsWithItems = rows.map((row) => ({ row, item: items.find((x) => String(x.uid) === String(row.uid)) }))
      .filter((entry) => entry.item?.points?.length);
    $('pageRoot').innerHTML = [
      pageTitle(`当前对比对象：${runDisplayName(state.run?.run) || '自动选择 Top run'}`),
      `<section class="wb-grid sidebar">
        ${chartPanel('compareLines', '透射谱 T(λ) 对比', 'x=波长，y=透射率，按 Top 候选叠加')}
        ${panel('对比选项', '可导出为报告素材', compareOptions(rows))}
      </section>`,
      `<section class="wb-grid two">
        ${chartPanel('metricTrend', '关键指标趋势', 'λ0 / Q / Score 随扫描参数变化')}
        ${panel('多谱线参数对比表', `${rows.length} 条`, rankingTable(rows, { global: false, limit: 50 }))}
      </section>`,
    ].join('');
    const traces = rowsWithItems.map(({ row, item }, idx) => {
      return { x: (item.points || []).map((p) => p[0]), y: (item.points || []).map((p) => p[1]), mode: 'lines', name: row.name || row.uid, line: { color: COLORS[idx % COLORS.length], width: idx === 0 ? 3 : 1.6 } };
    });
    renderLineChart($('compareLines'), traces, lineLayout('波长 λ (nm)', '透射率 T', '透射谱 T(λ) 对比'));
    const trendRows = (state.run?.items || []).map((item, idx) => {
      const row = rows.find((candidate) => String(candidate.uid) === String(item.uid)) || {};
      return {
        x: Number(item.scan_value &#39318;&#39029; item.value_nm &#39318;&#39029; item.index &#39318;&#39029; row.scan_value &#39318;&#39029; row.index &#39318;&#39029; idx),
        lambda: Number(item.metrics?.center_lambda_nm &#39318;&#39029; row.center_lambda_nm),
        q: Number(item.metrics?.q &#39318;&#39029; row.q),
        score: Number(item.scores?.overall &#39318;&#39029; row.score &#39318;&#39029; row.overall),
      };
    }).filter((row) => Number.isFinite(row.x));
    renderLineChart($('metricTrend'), [
      { x: trendRows.map((row) => row.x), y: trendRows.map((row) => row.lambda), mode: 'lines+markers', name: 'λ0', line: { color: '#006b68' } },
      { x: trendRows.map((row) => row.x), y: trendRows.map((row) => row.q), mode: 'lines+markers', name: 'Q', line: { color: '#2563eb' } },
      { x: trendRows.map((row) => row.x), y: trendRows.map((row) => row.score), mode: 'lines+markers', name: 'Score', line: { color: '#16a34a' } },
    ], lineLayout(`扫描参数：${state.run?.scan_axis?.name || 'index'}${state.run?.scan_axis?.unit ? ` (${state.run.scan_axis.unit})` : ''}`, '指标值', '关键指标趋势'));
  }

  function compareOptions(rows) {
    return `<div class="wb-list">
      <div class="wb-list-row good"><strong>已选择谱线 <span class="wb-pill good">${rows.length}</span></strong><p>默认取当前 run 的 Top 候选，后续可接入多选状态和对比集。</p></div>
      <div class="wb-list-row info"><strong>归一化</strong><p>当前使用原始 T 值；报告阶段建议标注是否按峰值或背景归一。</p></div>
      <div class="wb-list-row warn"><strong>主峰 / 主谷标注</strong><p>若 FWHM 不可可靠计算，图上仅做候选提示，不作为结论。</p></div>
    </div>`;
  }

  function renderFieldViewer() {
    if (!state.run) {
      $('pageRoot').innerHTML = pageTitle('正在自动选择评分最高的 run...');
      return;
    }
    const item = selectedItem();
    const availability = state.run?.availability || {};
    $('pageRoot').innerHTML = [
      pageTitle(`当前 run：${runDisplayName(state.run?.run)}`),
      `<section class="wb-grid sidebar">
        ${chartPanel('resonanceLine', '透射谱 T(λ) — 当前样本', item?.name || '候选谱线')}
        ${panel('数据与视图信息', '当前样本', fieldInfo(item, availability))}
      </section>`,
      `<section class="wb-grid sidebar">
        ${panel('场图 / 相位 / Poynting 查看区', '真实文件存在时显示入口', supportCards(availability))}
        ${panel('物理判断提示', '保守证据链', mechanismCards())}
      </section>`,
      panel('共振前后对比', '占位联动卡片', beforeAfterCards(item)),
    ].join('');
    renderLineChart($('resonanceLine'), item?.points?.length ? [{ x: item.points.map((p) => p[0]), y: item.points.map((p) => p[1]), mode: 'lines', name: '透射率 T', line: { color: '#006b68', width: 2.4 } }] : [], lineLayout('波长 λ (nm)', '透射率 T', '透射谱 T(λ) — 当前样本'));
  }

  function fieldInfo(item, availability) {
    const m = item?.metrics || {};
    return `<div class="wb-list">
      <div class="wb-list-row good"><strong>λ0：${fmt(m.center_lambda_nm, 2)} nm</strong><p>FWHM ${fmt(m.line_width_nm, 3)} nm，Q ${fmt(m.q, 1)}</p></div>
      ${Object.entries(availability).map(([key, row]) => `<div class="wb-list-row ${row.present ? 'good' : 'warn'}"><strong>${esc(key)} <span class="wb-pill ${row.present ? 'good' : 'warn'}">${row.present ? `${row.count || 0} 个` : '缺失'}</span></strong><p>${row.present ? esc((row.files || []).slice(0, 2).map((f) => f.name).join('；')) : '建议下一轮补导出。'}</p></div>`).join('')}
    </div>`;
  }

  function supportCards(availability) {
    const labels = { field: '场图', phase: '相位', poynting: 'Poynting', reflection: 'R 谱', absorption: 'A 谱' };
    return `<div class="wb-grid three">${Object.entries(labels).map(([key, label]) => {
      const row = availability?.[key] || {};
      const file = row.files?.[0];
      return `<div class="wb-list-row ${row.present ? 'good' : 'warn'}"><strong>${label}</strong><p>${row.present ? `${row.count || 0} 个文件已识别` : '暂无导出文件'}</p>${file?.id ? `<a class="wb-btn" href="${fileUrl(file.id)}" target="_blank" rel="noopener">打开文件</a>` : '<span class="wb-pill warn">占位</span>'}</div>`;
    }).join('')}</div>`;
  }

  function mechanismCards() {
    const top = state.run?.mechanism_summary?.top || [];
    return `<div class="wb-list">${top.map((row, idx) => `<div class="wb-list-row ${idx === 0 ? 'good' : 'info'}"><strong>${idx + 1}. ${esc(row.claim || row.name)} <span class="wb-pill">${pct((row.confidence || 0) * 100, 0)}</span></strong><p>支持：${esc((row.supporting_evidence || []).join('；') || '暂无')}</p><p>缺失：${esc((row.missing_evidence || []).join('；') || '暂无')}</p></div>`).join('') || '<div class="wb-empty">进入单 run 后显示机制初判</div>'}</div>`;
  }

  function beforeAfterCards(item) {
    const m = item?.metrics || {};
    const center = Number(m.center_lambda_nm || 0);
    const fwhm = Number(m.line_width_nm || 0);
    const cards = [
      ['共振前', center - (Number.isFinite(fwhm) ? fwhm * 2 : 20), '用于背景场对照'],
      ['共振处', center, '优先导出 Ex/Ey/Ez/phase/Poynting'],
      ['共振后', center + (Number.isFinite(fwhm) ? fwhm * 2 : 20), '用于相位跃迁与能流对照'],
    ];
    return `<div class="wb-grid three">${cards.map((row, idx) => `<div class="wb-list-row ${idx === 1 ? 'good' : 'info'}"><strong>${row[0]}：${fmt(row[1], 2)} nm</strong><p>${row[2]}</p><span class="wb-pill ${idx === 1 ? 'good' : 'info'}">等待场图文件</span></div>`).join('')}</div>`;
  }

  function renderReportPreview() {
    const md = buildReportMarkdown();
    $('pageRoot').innerHTML = [
      pageTitle(state.run ? `报告对象：${runDisplayName(state.run.run)}` : '全局报告预览'),
      `<section class="wb-grid sidebar">
        <section class="wb-panel"><div class="wb-panel-head"><strong>页面预览</strong><span>A4 / Markdown</span></div><div class="wb-panel-body"><article class="wb-report-preview">${markdownToHtml(md)}</article></div></section>
        ${panel('报告设置', '当前支持后端摘要导出', reportControls(md))}
      </section>`,
    ].join('');
  }

  function buildReportMarkdown() {
    if (state.run) {
      const s = state.run.summary || {};
      const rows = bestRunRows().slice(0, 5);
      const mechs = state.run.mechanism_summary?.top || [];
      return `# ${runDisplayName(state.run.run)} 光谱诊断摘要\n\n` +
        `- 谱线数：${s.spectrum_count || 0}\n- 高价值候选：${s.high_value_count || 0}\n- 最佳评分：${fmt(s.best_score, 2)}\n- 推荐目标：${TARGET_LABELS[s.best_target] || s.best_target || '-'}\n\n` +
        `## Top 候选\n\n${rows.map((row, idx) => `${idx + 1}. ${row.name || row.uid}: λ0=${fmt(row.center_lambda_nm, 2)} nm, FWHM=${fmt(row.fwhm_nm, 3)} nm, Q=${fmt(row.q, 1)}, Score=${fmt(row.score || row.overall, 2)}`).join('\n')}\n\n` +
        `## 物理机制 Top 3\n\n${mechs.map((row, idx) => `${idx + 1}. ${row.claim || row.name}: 置信度 ${fmt((row.confidence || 0) * 100, 0)}%。支持：${(row.supporting_evidence || []).join('；') || '暂无'}。缺失：${(row.missing_evidence || []).join('；') || '暂无'}。`).join('\n')}\n\n` +
        `## 下一步建议\n\n${(state.run.suggestions || []).map((row) => `- [${row.priority || 'P3'}] ${row.title}: ${row.detail || row.reason || ''}`).join('\n')}`;
    }
    const s = state.global?.summary || {};
    const rows = bestGlobalRows().slice(0, 5);
    return `# FDTD 光谱诊断全局摘要\n\n- run 数：${s.run_count || 0}\n- 谱线数：${s.spectrum_count || 0}\n- 高价值候选：${s.high_value_count || 0}\n- 异常谱线：${s.abnormal_spectrum_count || 0}\n\n## 全局 Top 候选\n\n${rows.map((row, idx) => `${idx + 1}. ${rowRunDisplayName(row)} / ${row.name || row.uid}: Score=${fmt(row.score || row.overall, 2)}, λ0=${fmt(row.center_lambda_nm, 2)} nm, Q=${fmt(row.q, 1)}`).join('\n')}`;
  }

  function markdownToHtml(md) {
    return esc(md)
      .replace(/^# (.*)$/gm, '<h2>$1</h2>')
      .replace(/^## (.*)$/gm, '<h3>$1</h3>')
      .replace(/^- (.*)$/gm, '<p>• $1</p>')
      .replace(/^\d+\. (.*)$/gm, '<p>$&</p>')
      .replace(/\n{2,}/g, '<br>');
  }

  function reportControls(md) {
    return `<div class="wb-list">
      <div class="wb-list-row good"><strong>导出内容</strong><p>排行榜、诊断摘要、机制初判、缺失证据与下一步建议。</p></div>
      <button class="wb-btn primary" type="button" data-export>${icon('download')}导出摘要</button>
      <button class="wb-btn" type="button" data-copy-report>复制 Markdown</button>
      <pre class="wb-code">${esc(md.slice(0, 1800))}</pre>
    </div>`;
  }

  function renderCompareSets() {
    const sets = loadSets();
    const rows = bestGlobalRows().slice(0, 7);
    $('pageRoot').innerHTML = [
      pageTitle(),
      `<section class="wb-grid sidebar">
        ${panel('对比集列表', `${sets.length} 个本地集合`, compareSetList(sets))}
        ${panel('当前推荐集合', '由全局 Top 候选生成', currentSetDraft(rows))}
      </section>`,
      panel('候选明细', `${rows.length} 条`, rankingTable(rows, { global: true, limit: 30 })),
    ].join('');
  }

  function loadSets() {
    try { return JSON.parse(localStorage.getItem('fdtdCompareSets') || '[]'); } catch { return []; }
  }

  function saveSets(sets) {
    localStorage.setItem('fdtdCompareSets', JSON.stringify(sets));
  }

  function compareSetList(sets) {
    return `<div class="wb-list">${sets.map((set, idx) => `<div class="wb-list-row ${idx === 0 ? 'good' : 'info'}"><strong>${esc(set.name)} <span class="wb-pill">${set.items?.length || 0} 项</span></strong><p>${esc(set.created || '')}</p><p>${esc((set.items || []).slice(0, 3).map((x) => x.name).join('；'))}</p></div>`).join('') || '<div class="wb-empty">尚未创建本地对比集</div>'}</div>`;
  }

  function currentSetDraft(rows) {
    return `<div class="wb-list">
      <div class="wb-list-row good"><strong>全局 Top 对比集</strong><p>${esc(rows.slice(0, 4).map((row) => row.name || row.uid).join('；'))}</p></div>
      <button class="wb-btn primary" type="button" data-create-set>${icon('task')}保存当前 Top 对比集</button>
      <a class="wb-btn" href="/spectral_compare.html?run_id=${encodeURIComponent(selectedRunId())}">打开多谱线对比</a>
    </div>`;
  }

  function renderDataQuality() {
    const s = state.global?.summary || {};
    const completeness = availabilityRows().reduce((sum, row) => sum + row.pct, 0) / Math.max(1, availabilityRows().length);
    const risks = bestGlobalRows().filter(rowRisk).length;
    $('pageRoot').innerHTML = [
      pageTitle(),
      `<section class="wb-kpi-grid">
        ${kpi('结构完整性', pct(100, 1), '扫描缓存可读', 'success', 'grid')}
        ${kpi('光谱完整性', pct(completeness, 1), 'T/R/A/field/phase/Poynting', completeness > 80 ? 'success' : 'warning', 'chart')}
        ${kpi('异常谱线', s.abnormal_spectrum_count || 0, '质量 gate 标记', s.abnormal_spectrum_count ? 'danger' : 'success', 'warning')}
        ${kpi('文件注册', '正常', '复用 /api/file 注册机制', 'success', 'file')}
        ${kpi('缺失项', missingRows().length, '需补证据链', missingRows().length ? 'warning' : 'success', 'warning')}
        ${kpi('风险候选', risks, '排行榜前列质量风险', risks ? 'danger' : 'success', 'warning')}
      </section>`,
      `<section class="wb-grid sidebar">
        ${panel('质量问题清单', '按影响排序', qualityIssueTable())}
        ${panel('质量规则说明', '当前启用', qualityRules())}
      </section>`,
      `<section class="wb-grid two">${panel('完整性矩阵', '按数据类型', availabilityProgress())}${chartPanel('qualityTrend', '质量评分趋势', 'x=排行榜序号，y=综合评分')}</section>`,
    ].join('');
    renderLineChart($('qualityTrend'), [{ x: bestGlobalRows().slice(0, 80).map((_, i) => i + 1), y: bestGlobalRows().slice(0, 80).map(scoreOf), mode: 'lines+markers', name: '综合评分 Score', line: { color: '#16a34a' } }], lineLayout('排行榜序号', '综合评分 Score', '质量评分趋势'));
  }

  function qualityIssueTable() {
    const rows = [
      ...missingRows().slice(0, 80).map((row) => ({ type: `缺 ${row.label || row.key}`, severity: Number(row.best_score || 0) >= 60 ? '高' : '中', object: row.run_name, detail: row.next, run_id: row.run_id })),
      ...bestGlobalRows().filter(rowRisk).slice(0, 80).map((row) => ({ type: '谱线质量风险', severity: '高', object: rowRunDisplayName(row), detail: row.flags || '质量 gate 标记', run_id: row.run_id })),
    ].slice(0, 180);
    return `<div class="wb-table-shell"><div class="wb-table-scroll"><table class="wb-table"><thead><tr><th class="col-target">问题类型</th><th class="col-target">严重性</th><th class="col-run">对象</th><th>说明</th><th class="col-action">操作</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${esc(row.type)}</td><td><span class="wb-pill ${row.severity === '高' ? 'bad' : 'warn'}">${esc(row.severity)}</span></td><td class="truncate" title="${esc(row.object)}">${esc(row.object)}</td><td class="truncate" title="${esc(row.detail)}">${esc(row.detail)}</td><td><a class="wb-pill info" href="/spectral_physics_diagnostics.html?run_id=${encodeURIComponent(row.run_id)}">查看</a></td></tr>`).join('') || '<tr><td colspan="5">暂无质量问题</td></tr>'}</tbody></table></div></div>`;
  }

  function qualityRules() {
    return `<div class="wb-list">
      <div class="wb-list-row good"><strong>光谱完整性</strong><p>T 谱可解析且有效点数充足，FWHM/Q 无法计算时显式降权。</p></div>
      <div class="wb-list-row warn"><strong>能量异常</strong><p>T&gt;1、负值、NaN 比例高、贴边峰谷会进入质量 gate。</p></div>
      <div class="wb-list-row info"><strong>证据完整性</strong><p>机制判断需要 R/A/场图/相位/Poynting 支撑，否则只输出“疑似”。</p></div>
    </div>`;
  }

  function renderResourceBrowser() {
    const availability = state.run?.availability || {};
    const files = Object.entries(availability).flatMap(([type, row]) => (row.files || []).map((file) => ({ ...file, type })));
    $('pageRoot').innerHTML = [
      pageTitle(`当前资源对象：${runDisplayName(state.run?.run) || '自动选择 run'}`),
      `<section class="wb-grid sidebar">
        ${panel('目录树', '已识别资源目录', resourceTree(availability))}
        ${panel('文件预览', files[0]?.name || '暂无文件', resourcePreview(files[0]))}
      </section>`,
      panel('文件列表', `${files.length} 个已注册文件`, resourceTable(files)),
    ].join('');
  }

  function resourceTree(availability) {
    return `<div class="wb-list">${Object.entries(availability).map(([key, row]) => `<div class="wb-list-row ${row.present ? 'good' : 'warn'}"><strong>${esc(key)} <span class="wb-pill ${row.present ? 'good' : 'warn'}">${row.count || 0}</span></strong><p>${esc((row.files || []).slice(0, 2).map((f) => f.name).join('；') || '未发现文件')}</p></div>`).join('')}</div>`;
  }

  function resourcePreview(file) {
    if (!file) return '<div class="wb-empty">没有可预览文件</div>';
    return `<div class="wb-list">
      <div class="wb-list-row good"><strong>${esc(file.name)}</strong><p>${esc(file.path || '')}</p></div>
      <a class="wb-btn primary" href="${fileUrl(file.id)}" target="_blank" rel="noopener">${icon('file')}打开文件</a>
    </div>`;
  }

  function resourceTable(files) {
    const body = files.map((file) => `<tr><td>${esc(file.type)}</td><td>${esc(file.name)}</td><td>${esc(compactPath(file.path))}</td><td><a class="wb-pill info" href="${fileUrl(file.id)}" target="_blank" rel="noopener">打开</a></td></tr>`).join('');
    return `<div class="wb-table-shell"><div class="wb-table-scroll"><table class="wb-table"><thead><tr><th class="col-target">类型</th><th class="col-name">文件名</th><th>路径</th><th class="col-action">操作</th></tr></thead><tbody>${body || '<tr><td colspan="4">暂无注册文件</td></tr>'}</tbody></table></div></div>`;
  }

  function renderPage() {
    renderTopShell();
    renderSidebar();
    const renderers = {
      global_leaderboard: renderGlobalLeaderboard,
      missing_repair: renderMissingRepair,
      batch_tasks: renderBatchTasks,
      spectral_compare: renderSpectralCompare,
      field_viewer: renderFieldViewer,
      report_preview: renderReportPreview,
      compare_sets: renderCompareSets,
      data_quality: renderDataQuality,
      resource_browser: renderResourceBrowser,
    };
    (renderers[state.page] || renderGlobalLeaderboard)();
    bindDynamic();
  }

  function bindDynamic() {
    document.querySelectorAll('[data-export]').forEach((button) => {
      button.addEventListener('click', exportSummary);
    });
    document.querySelectorAll('[data-copy-report]').forEach((button) => {
      button.addEventListener('click', async () => {
        await navigator.clipboard?.writeText(buildReportMarkdown());
        button.textContent = '已复制 Markdown';
        setTimeout(() => { button.textContent = '复制 Markdown'; }, 1400);
      });
    });
    document.querySelectorAll('[data-create-set]').forEach((button) => {
      button.addEventListener('click', () => {
        const sets = loadSets();
        const items = bestGlobalRows().slice(0, 7).map((row) => ({ run_id: row.run_id, uid: row.uid, name: row.name, score: row.score || row.overall }));
        sets.unshift({ name: `全局 Top ${new Date().toLocaleString()}`, created: new Date().toISOString(), items });
        saveSets(sets.slice(0, 20));
        renderCompareSets();
      });
    });
  }

  async function exportSummary() {
    showModal('导出诊断摘要', '<div class="wb-loading">正在生成导出文件...</div>', '');
    try {
      const body = { run_id: state.run?.run?.id || qs.get('run_id') || '', target: state.target };
      const data = await fetchJson('/api/spectral-export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const links = Object.entries(data.files || {}).map(([key, id]) => `<a class="wb-btn" href="${fileUrl(id)}" target="_blank" rel="noopener">${icon('file')}${esc(key)}</a>`).join('');
      showModal('导出诊断摘要', `<div class="wb-list"><div class="wb-list-row good"><strong>导出完成</strong><p>${data.mode === 'run' ? '已写入该 run 的 12_analysis_summary。' : '已写入全局汇总目录。'}</p></div><div class="wb-chip-row">${links || '<span class="wb-pill warn">没有返回文件</span>'}</div></div>`, '<button class="wb-btn primary" data-close-modal>关闭</button>');
    } catch (err) {
      showModal('导出失败', `<div class="wb-list-row bad"><strong>${esc(err.message)}</strong><p>请确认 server.py 正在运行，且目标 run 可读。</p></div>`, '<button class="wb-btn primary" data-close-modal>关闭</button>');
    }
  }

  async function openConfig() {
    showModal('目标函数 / 评分规则配置', '<div class="wb-loading">正在读取配置...</div>', '');
    try {
      const data = await fetchJson('/api/spectral-config');
      const cfg = data.config || {};
      const targets = ['notch', 'passband', 'fano', 'q_mode', 'edge', 'broadband_high', 'broadband_low', 'flat', 'custom'];
      const body = `<div class="wb-grid two">
        ${targets.map((target) => `<div class="wb-list-row"><strong>${esc(TARGET_LABELS[target] || target)}</strong><p>当前权重与阈值由后端配置管理；本弹窗先提供统一入口，保存仍走 /api/spectral-config。</p><pre class="wb-code">${esc(JSON.stringify(cfg.targets?.[target] || cfg.scoring?.[target] || {}, null, 2))}</pre></div>`).join('')}
      </div>`;
      showModal('目标函数 / 评分规则配置', body, '<button class="wb-btn" data-close-modal>取消</button><button class="wb-btn primary" data-close-modal>应用并重算</button>');
    } catch (err) {
      showModal('配置读取失败', `<div class="wb-list-row bad"><strong>${esc(err.message)}</strong></div>`, '<button class="wb-btn primary" data-close-modal>关闭</button>');
    }
  }

  function openMechanismDrawer() {
    const body = mechanismCards();
    showDrawer('物理机制判断详情', body, '<button class="wb-btn primary" data-close-drawer>关闭</button>');
  }

  let focusedBeforeModal = null;
  let modalTrapCleanup = null;

  function trapModalFocus(modal) {
    if (!modal) return;
    const focusable = [...modal.querySelectorAll('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')];
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const handler = (event) => {
      if (event.key !== 'Tab' || !first || !last) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    modal.addEventListener('keydown', handler);
    modalTrapCleanup = () => modal.removeEventListener('keydown', handler);
    setTimeout(() => first?.focus(), 0);
  }

  function showModal(title, body, foot) {
    const layer = $('modalLayer');
    if (!layer) return;
    focusedBeforeModal = document.activeElement;
    if (modalTrapCleanup) {
      modalTrapCleanup();
      modalTrapCleanup = null;
    }
    layer.innerHTML = `<section class="wb-modal" role="dialog" aria-modal="true" aria-labelledby="modalTitle" tabindex="-1">
      <div class="wb-modal-head"><div><strong id="modalTitle">${esc(title)}</strong><p style="margin:4px 0 0;color:var(--wb-muted);font-size:12px">基于当前真实诊断数据生成。</p></div><button class="wb-close" data-close-modal aria-label="关闭">×</button></div>
      <div class="wb-modal-body">${body}</div>
      <div class="wb-modal-foot">${foot || '<button class="wb-btn primary" data-close-modal>关闭</button>'}</div>
    </section>`;
    layer.classList.add('open');
    layer.querySelectorAll('[data-close-modal]').forEach((button) => button.addEventListener('click', closeModal));
    trapModalFocus(layer.querySelector('.wb-modal'));
  }

  function closeModal() {
    const layer = $('modalLayer');
    layer?.classList.remove('open');
    if (modalTrapCleanup) {
      modalTrapCleanup();
      modalTrapCleanup = null;
    }
    if (focusedBeforeModal && document.contains(focusedBeforeModal)) {
      focusedBeforeModal.focus();
    }
  }

  function showDrawer(title, body, foot) {
    const layer = $('drawerLayer');
    if (!layer) return;
    layer.innerHTML = `<aside class="wb-drawer" role="dialog" aria-modal="true">
      <div class="wb-drawer-head"><div><strong>${esc(title)}</strong><p style="margin:4px 0 0;color:var(--wb-muted);font-size:12px">所有结论均为疑似/可能，缺失证据会明确列出。</p></div><button class="wb-close" data-close-drawer>×</button></div>
      <div class="wb-drawer-body">${body}</div>
      <div class="wb-drawer-foot">${foot || '<button class="wb-btn primary" data-close-drawer>关闭</button>'}</div>
    </aside>`;
    layer.classList.add('open');
    layer.querySelectorAll('[data-close-drawer]').forEach((button) => button.addEventListener('click', closeDrawer));
  }

  function closeDrawer() {
    $('drawerLayer')?.classList.remove('open');
  }

  async function load(refresh = false) {
    if (currentController) currentController.abort();
    const currentVersion = ++loadVersion;
    currentController = new AbortController();
    const { signal } = currentController;
    const root = $('pageRoot');
    root.innerHTML = '<div class="wb-loading">正在读取 FDTD 结果库...</div>';
    setStatus('正在读取光谱诊断数据...');
    try {
      const params = new URLSearchParams();
      if (refresh) params.set('refresh', '1');
      state.global = await fetchJson(`/api/spectral-diagnostics?${params.toString()}`, { signal });
      if (currentVersion !== loadVersion) return;
      if (state.page === 'batch_tasks') {
        state.jobs = await fetchJson('/api/jobs', { signal }).catch(() => ({ jobs: [] }));
        if (currentVersion !== loadVersion) return;
      }
      const runId = meta.run ? selectedRunId() : '';
      if (runId) {
        const explicitRunId = qs.get('run_id') || qs.get('id');
        if (!explicitRunId) {
          const url = new URL(location.href);
          url.searchParams.set('run_id', runId);
          history.replaceState(null, '', url.toString());
        }
        const runParams = new URLSearchParams({ run_id: runId });
        state.run = await fetchJson(`/api/spectral-diagnostics?${runParams.toString()}`, { signal });
        if (currentVersion !== loadVersion) return;
        state.selectedUid = state.run.summary?.best_uid || state.run.items?.[0]?.uid || '';
      } else {
        state.run = null;
      }
      renderPage();
      setStatus(`数据源：本地 FDTD 结果库。更新时间：${new Date().toLocaleString()}`);
      if ($('statusRight')) {
        $('statusRight').textContent = state.run ? `当前 run：${runDisplayName(state.run.run)}` : `共 ${state.global.summary?.run_count || 0} run`;
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      root.innerHTML = `<div class="wb-empty">读取失败：${esc(err.message)}</div>`;
      setStatus('读取失败');
    }
  }

  function bindStatic() {
    $('refreshBtn')?.addEventListener('click', () => load(true));
    $('exportSummaryBtn')?.addEventListener('click', exportSummary);
    $('configBtn')?.addEventListener('click', openConfig);
    $('mechanismBtn')?.addEventListener('click', openMechanismDrawer);
    $('targetMode')?.addEventListener('change', (event) => {
      state.target = event.target.value || 'overall';
      renderPage();
    });
    const sideSearch = $('sideSearch');
    if (sideSearch && !document.querySelector('label[for="sideSearch"]')) {
      const label = document.createElement('label');
      label.htmlFor = 'sideSearch';
      label.className = 'sr-only';
      label.textContent = '搜索 run 名称或路径';
      sideSearch.parentElement?.insertBefore(label, sideSearch);
    }
    $('sideSearch')?.addEventListener('input', debounce((event) => {
      state.query = event.target.value.trim();
      renderSidebar();
      if (['global_leaderboard', 'data_quality'].includes(state.page)) renderPage();
    }, 250));
    $('modalLayer')?.addEventListener('click', (event) => {
      if (event.target.id === 'modalLayer') closeModal();
    });
    $('drawerLayer')?.addEventListener('click', (event) => {
      if (event.target.id === 'drawerLayer') closeDrawer();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeModal();
        closeDrawer();
      }
    });
  }

  bindStatic();
  renderTopShell();
  load(false);
})();
