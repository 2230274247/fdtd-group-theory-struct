(function () {
  const UNKNOWN = '未知';

  function text(value, fallback = UNKNOWN) {
    if (value === undefined || value === null || value === '') return fallback;
    return String(value);
  }

  function num(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function fmt(value, digits = 3) {
    const n = num(value);
    if (n === null) return text(value, UNKNOWN);
    return n.toFixed(digits).replace(/\.?0+$/, '');
  }

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }[ch]));
  }

  function collectParams(run) {
    const out = {};
    for (const item of run?.items || []) {
      for (const [key, value] of Object.entries(item.params || {})) {
        if (out[key] === undefined && value !== '') out[key] = value;
      }
    }
    return out;
  }

  function first(params, keys) {
    const lowered = {};
    for (const [key, value] of Object.entries(params || {})) lowered[key.toLowerCase()] = value;
    for (const key of keys) {
      if (params && params[key] !== undefined && params[key] !== '') return params[key];
      const value = lowered[String(key).toLowerCase()];
      if (value !== undefined && value !== '') return value;
    }
    return '';
  }

  function isBzfRun(run) {
    const hay = [
      run?.name,
      run?.relative_path,
      run?.perturbation,
      JSON.stringify(collectParams(run)),
    ].join(' ').toLowerCase();
    return /(bzf|brillouin|folding|supercell|eta|deltal|布里渊|折叠|超胞)/i.test(hay);
  }

  function classify(run, item) {
    const params = { ...collectParams(run), ...(item?.params || {}) };
    const eta = first(params, ['eta_nm', 'ETA_NM', 'deltaL_nm', 'delta_l_nm', 'delta_nm', 'value_nm']);
    const etaN = num(eta);
    const simpleCopy = etaN !== null ? Math.abs(etaN) < 1e-9 : UNKNOWN;
    const physical = simpleCopy === UNKNOWN ? UNKNOWN : !simpleCopy;
    return { params, eta, etaN, simpleCopy, physical };
  }

  function fact(label, value, suffix = '') {
    return `<div class="bzf-fact"><b>${esc(label)}</b><span>${esc(text(value, '未记录'))}${value !== undefined && value !== null && value !== '' ? suffix : ''}</span></div>`;
  }

  function check(label, state, detail = '') {
    const cls = state === true ? 'ok' : state === false ? 'bad' : 'unknown';
    const word = state === true ? '通过' : state === false ? '需检查' : '未知';
    return `<div class="bzf-check ${cls}"><b>${esc(label)}</b><br><span>${word}${detail ? `：${esc(detail)}` : ''}</span></div>`;
  }

  function nearlyEqual(a, b) {
    const x = num(a), y = num(b);
    if (x === null || y === null) return null;
    return Math.abs(x - y) <= Math.max(1e-6, Math.abs(y) * 1e-4);
  }

  function bzfSvg(info) {
    const p = info.params;
    const primitive = num(first(p, ['primitive_period_x_nm', 'PRIMITIVE_PERIOD_X_NM'])) || 900;
    const supercell = num(first(p, ['supercell_period_x_nm', 'SUPERCELL_PERIOD_X_NM'])) || primitive * 2;
    const L = num(first(p, ['L_nm', 'L_NM'])) || supercell / 4;
    const baseDelta = num(first(p, ['BASE_DELTA_NM', 'base_delta_nm', 'deltaL0_nm'])) || primitive / 5;
    const eta = info.etaN || 0;
    const xs = [
      -L - (baseDelta + eta),
      -L + (baseDelta + eta),
      L - (baseDelta - eta),
      L + (baseDelta - eta),
    ];
    const xToPx = x => 40 + ((x + supercell / 2) / supercell) * 520;
    const labels = xs.map((x, idx) => {
      const cx = xToPx(x);
      return `<circle cx="${cx}" cy="86" r="15" fill="#0f766e" opacity="0.86"></circle><text x="${cx}" y="122" text-anchor="middle" font-size="11" fill="#334155">x${idx + 1}</text>`;
    }).join('');
    const primitiveLines = [];
    for (let x = -supercell / 2 + primitive; x < supercell / 2; x += primitive) {
      primitiveLines.push(`<line x1="${xToPx(x)}" y1="38" x2="${xToPx(x)}" y2="136" stroke="#64748b" stroke-dasharray="5 5"></line>`);
    }
    return `
      <div class="bzf-svg-wrap">
        <svg viewBox="0 0 600 176" role="img" aria-label="BZF supercell geometry">
          <rect x="40" y="38" width="520" height="98" rx="8" fill="#ecfeff" stroke="#0f766e" stroke-width="2"></rect>
          ${primitiveLines.join('')}
          <line x1="40" y1="148" x2="560" y2="148" stroke="#334155"></line>
          <text x="300" y="26" text-anchor="middle" font-size="14" fill="#0f172a">supercell A = ${fmt(supercell)} nm</text>
          <text x="168" y="160" text-anchor="middle" font-size="11" fill="#64748b">primitive a = ${fmt(primitive)} nm</text>
          <text x="432" y="160" text-anchor="middle" font-size="11" fill="#64748b">primitive a = ${fmt(primitive)} nm</text>
          ${labels}
          <text x="300" y="68" text-anchor="middle" font-size="12" fill="#7c3aed">eta = ${fmt(eta)} nm</text>
          <text x="153" y="92" text-anchor="middle" font-size="11" fill="#92400e">d_in_1</text>
          <text x="300" y="92" text-anchor="middle" font-size="11" fill="#92400e">d_out</text>
          <text x="447" y="92" text-anchor="middle" font-size="11" fill="#92400e">d_in_2</text>
        </svg>
      </div>`;
  }

  function render(run, item) {
    if (!isBzfRun(run)) {
      return '<div class="empty">当前 run 未识别为 BZF / supercell 扰动。名称或参数中包含 BZF、brillouin、folding、supercell、eta、布里渊、折叠、超胞时会自动启用。</div>';
    }
    const info = classify(run, item);
    const p = info.params;
    const primitive = first(p, ['primitive_period_x_nm', 'PRIMITIVE_PERIOD_X_NM']);
    const supercell = first(p, ['supercell_period_x_nm', 'SUPERCELL_PERIOD_X_NM']);
    const folding = first(p, ['folding_order', 'FOLDING_ORDER']);
    const fdtdSpan = first(p, ['fdtd_x_span_nm', 'FDTD_x_span_nm', 'fdtd_span_x_nm']);
    const substrateSpan = first(p, ['substrate_x_span_nm', 'substrate_span_x_nm']);
    const sourceSpan = first(p, ['source_x_span_nm', 'source_span_x_nm']);
    const monitorSpan = first(p, ['monitor_x_span_nm', 'monitor_span_x_nm', 'T_monitor_x_span_nm']);
    const eta0Exists = (run.items || []).some(row => {
      const value = first(row.params || {}, ['eta_nm', 'ETA_NM', 'deltaL_nm', 'delta_nm', 'value_nm']);
      const n = num(value);
      return n !== null && Math.abs(n) < 1e-9;
    });
    const scanCount = (run.items || []).length;
    const badCount = (run.items || []).filter(row => row.unconverged || num(row.max_abs2) > 1).length;
    const alertClass = info.simpleCopy === true ? 'baseline' : info.physical === true ? 'physical' : '';
    const alertText = info.simpleCopy === true
      ? '当前为 simple-copy supercell，只能作为数学折叠基线，不能单独证明真实物理扰动。'
      : info.physical === true
        ? '当前为 physical BZF perturbation，原 primitive 平移对称被破坏，超胞周期成为真实物理周期。'
        : '当前缺少 eta 字段，暂时无法判断 simple-copy 或 physical perturbation。';
    return `
      <div class="panel-title"><span>BZF 分析</span><span class="pill">${esc(run?.perturbation || 'BZF')}</span></div>
      <div class="bzf-card">
        <div class="bzf-alert ${alertClass}">${esc(alertText)}</div>
        <div class="bzf-facts">
          ${fact('primitive_period_x', primitive, ' nm')}
          ${fact('supercell_period_x', supercell, ' nm')}
          ${fact('folding_order', folding)}
          ${fact('L_nm', first(p, ['L_nm', 'L_NM']), ' nm')}
          ${fact('deltaL0_nm / BASE_DELTA', first(p, ['deltaL0_nm', 'BASE_DELTA_NM', 'base_delta_nm']), ' nm')}
          ${fact('eta_nm', info.eta, ' nm')}
          ${fact('simple copy', info.simpleCopy === UNKNOWN ? UNKNOWN : (info.simpleCopy ? '是' : '否'))}
          ${fact('physical perturbation', info.physical === UNKNOWN ? UNKNOWN : (info.physical ? '是' : '否'))}
          ${fact('FDTD x span', fdtdSpan, ' nm')}
          ${fact('substrate x span', substrateSpan, ' nm')}
          ${fact('source x span', sourceSpan, ' nm')}
          ${fact('monitor x span', monitorSpan, ' nm')}
        </div>
        ${bzfSvg(info)}
        <div class="bzf-checklist">
          ${check('FDTD x span = supercell', nearlyEqual(fdtdSpan, supercell))}
          ${check('substrate x span = supercell', nearlyEqual(substrateSpan, supercell))}
          ${check('source x span = supercell', nearlyEqual(sourceSpan, supercell))}
          ${check('monitor x span = supercell', nearlyEqual(monitorSpan, supercell))}
          ${check('motif 对象命名唯一', first(p, ['unique_object_names', 'motif_names_unique']) === '' ? null : /true|1|yes|ok/i.test(first(p, ['unique_object_names', 'motif_names_unique'])))}
          ${check('eta=0 基线存在', eta0Exists)}
          ${check('eta 扫描点数 >= 5', scanCount >= 5, `${scanCount} 点`)}
          ${check('manifest.csv 完整', Boolean(run?.has_manifest))}
          ${check('max(T)>1 异常数量可接受', badCount <= Math.max(1, Math.ceil(scanCount * 0.25)), `${badCount} 条`)}
        </div>
      </div>`;
  }

  window.FDTDBZF = { isBzfRun, render };
})();
