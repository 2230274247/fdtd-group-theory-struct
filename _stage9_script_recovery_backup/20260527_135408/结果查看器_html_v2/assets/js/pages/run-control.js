import { api } from "../api.js";
import { escapeHtml, filteredScripts, fmtNumber, groupBy } from "../state.js";
import { openModal, toast } from "../ui.js";

let selectedIds = new Set();
let latestPreview = null;
let currentJobId = "";
let currentLogOffset = 0;
let currentJobMeta = null;

function scriptTree(scripts) {
  const byGroup = groupBy(scripts, "group");
  const statusLabel = (status) => ({
    has_full: "已有 full",
    has_test: "已有 test",
    missing_result: "缺结果",
    failed: "异常",
    unknown: "未知",
  }[status] || status || "未知");
  const statusTone = (status) => ({
    has_full: "green",
    has_test: "blue",
    missing_result: "orange",
    failed: "red",
  }[status] || "orange");
  return Object.entries(byGroup).map(([group, rows]) => `
    <div class="tree-group">
      <div class="tree-group-title">${escapeHtml(group)} <span class="tag blue">${rows.length}</span></div>
      ${rows.map((s) => `
        <button class="tree-row ${selectedIds.has(String(s.id || s.script_id)) ? "active" : ""}" data-script-id="${escapeHtml(s.id || s.script_id)}" type="button">
          <span class="dot ${statusTone(s.status) === "red" ? "red" : statusTone(s.status) === "green" ? "green" : "orange"}"></span>
          <span>${escapeHtml(s.mother_structure || "")} / ${escapeHtml(s.perturbation || s.relative_path)}</span>
          <span class="tag ${statusTone(s.status)}">${escapeHtml(statusLabel(s.status))}</span>
        </button>`).join("")}
    </div>`).join("");
}

export async function render() {
  const scripts = filteredScripts();
  const selectedCount = selectedIds.size;
  return `
    <section class="page active">
      <div class="page-head">
        <div>
          <h1 class="page-title">运行控制</h1>
          <div class="page-subtitle">通过 fdtd_master_controller.py 启动任务，支持 web_capture 与独立 CMD 原始输出。</div>
        </div>
        <button class="btn secondary" id="refresh-scripts" type="button">刷新脚本缓存</button>
      </div>

      <div class="layout-3">
        <div class="card pad">
          <div class="card-title">结构与脚本树 <span class="muted">${fmtNumber(scripts.length)} 个脚本</span></div>
          <div class="script-tree">${scripts.length ? scriptTree(scripts) : `<div class="empty">暂无脚本缓存。</div>`}</div>
        </div>

        <div class="card pad">
          <div class="card-title">运行参数 <span class="muted">已选择 ${selectedCount} 个脚本</span></div>
          <div class="field">
            <label>运行模式</label>
            <div class="segmented" id="mode-control">
              <button class="active" data-value="preview" type="button">preview</button>
              <button data-value="test" type="button">test</button>
              <button data-value="full" type="button">full</button>
            </div>
          </div>
          <div class="field" style="margin-top:12px">
            <label>执行策略</label>
            <div class="segmented" id="style-control">
              <button class="active" data-value="sequential" type="button">sequential</button>
              <button data-value="parallel" type="button">parallel</button>
            </div>
          </div>

          <div class="form-grid" style="margin-top:12px">
            <div class="field unit-field"><label>并发数</label><input class="input" id="max-parallel" type="number" min="1" max="16" value="1"><span class="unit">个</span></div>
            <div class="field unit-field"><label>start</label><input class="input" id="start-value" type="number" value=""><span class="unit">nm</span></div>
            <div class="field unit-field"><label>end</label><input class="input" id="end-value" type="number" value=""><span class="unit">nm</span></div>
            <div class="field unit-field"><label>step</label><input class="input" id="step-value" type="number" value=""><span class="unit">nm</span></div>
            <div class="field unit-field"><label>mesh accuracy</label><input class="input" id="mesh-accuracy" type="number" min="1" max="8" value=""><span class="unit">level</span></div>
            <div class="field unit-field"><label>dt 因子</label><input class="input" id="dt-factor" type="number" step="0.01" value=""><span class="unit">CFL</span></div>
          </div>
          <div class="form-grid" style="margin-top:12px">
            <div class="field unit-field"><label>runtime</label><input class="input" id="runtime-fs" type="number" value=""><span class="unit">fs</span></div>
            <div class="field unit-field"><label>auto shutoff</label><input class="input" id="auto-shutoff" type="number" step="0.0001" value=""><span class="unit">min</span></div>
            <div class="field unit-field"><label>子任务超时</label><input class="input" id="child-timeout" type="number" value="3600"><span class="unit">s</span></div>
          </div>

          <div class="notice" style="margin-top:10px">
            <div style="font-weight:600;margin-bottom:8px">自动容错（二次迭代）</div>
            <div class="form-grid">
              <div class="field unit-field"><label>启用自动容错</label><input id="auto-retry-enabled" type="checkbox" checked><span class="unit">on</span></div>
              <div class="field unit-field"><label>最大重试次数</label><input class="input" id="auto-retry-max" type="text" placeholder="空=自适应，0=不重试，2=最多重试2次" value=""><span class="unit">mode</span></div>
              <div class="field unit-field"><label>自适应硬上限</label><input class="input" id="auto-retry-hard-cap" type="number" min="1" value="8"><span class="unit">次</span></div>
              <div class="field unit-field"><label>无改善停止 patience</label><input class="input" id="auto-retry-patience" type="number" min="0" value="2"><span class="unit">次</span></div>
              <div class="field unit-field"><label>最小改善比例</label><input class="input" id="auto-retry-min-improve" type="number" step="0.01" value="0.15"><span class="unit">ratio</span></div>
              <div class="field unit-field"><label>T 阈值</label><input class="input" id="quality-t-limit" type="number" step="0.01" value="1.03"><span class="unit">|T|²</span></div>
              <div class="field unit-field"><label>ripple 阈值</label><input class="input" id="quality-ripple-limit" type="number" step="0.01" value="0.12"><span class="unit">score</span></div>
            </div>
          </div>

          <div class="notice" style="margin-top:10px">
            <div style="font-weight:600;margin-bottom:8px">输出方式</div>
            <div class="form-grid">
              <div class="field"><label>output_mode</label><select class="input" id="output-mode"><option value="web_capture" selected>web_capture</option><option value="cmd_raw">cmd_raw</option></select></div>
              <div class="field unit-field"><label>任务结束后保留 CMD</label><input id="keep-console-open" type="checkbox" checked><span class="unit">on</span></div>
            </div>
          </div>
        </div>

        <div>
          <div class="card pad">
            <div class="card-title">启动摘要</div>
            <table class="table"><tbody>
              <tr><td>扫描点估算</td><td id="point-estimate">待预览</td></tr>
              <tr><td>时长估算</td><td id="duration-estimate">待预览</td></tr>
              <tr><td>安全状态</td><td>未启动</td></tr>
            </tbody></table>
            <div style="display:flex;gap:10px;margin-top:14px">
              <button class="btn secondary" id="preview-run" type="button">生成预览</button>
              <button class="btn primary" id="start-run" type="button">启动</button>
            </div>
          </div>
          <div class="terminal-head" style="margin-top:12px"><span>实时日志</span><button class="link" id="stop-job" type="button">停止任务</button></div>
          <pre class="terminal" id="job-log">尚未启动任务。</pre>
        </div>
      </div>

      <div class="bottom-actions">
        <span class="muted">full + parallel 会触发高风险确认。</span>
        <div class="toolbar"><button class="btn ghost" id="clear-selected" type="button">清空选择</button><button class="btn primary" id="bottom-start" type="button">确认启动</button></div>
      </div>
    </section>`;
}

function activeValue(root, id) {
  return root.querySelector(`#${id} .active`)?.dataset.value;
}

function parseNumber(value) {
  if (value === undefined || value === null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function getAutotuneOverrides(root) {
  const out = {
    AUTO_RETRY_ENABLED: !!root.querySelector("#auto-retry-enabled")?.checked,
  };

  const retryMaxRaw = String(root.querySelector("#auto-retry-max")?.value ?? "").trim();
  if (!retryMaxRaw) {
    out.AUTO_RETRY_MODE = "adaptive";
    out.AUTO_RETRY_MAX = "adaptive";
  } else if (retryMaxRaw.toLowerCase() === "adaptive") {
    out.AUTO_RETRY_MODE = "adaptive";
    out.AUTO_RETRY_MAX = "adaptive";
  } else {
    const retryMaxNum = parseInt(retryMaxRaw, 10);
    if (Number.isNaN(retryMaxNum) || retryMaxNum < 0) {
      throw new Error("最大重试次数只能是空、adaptive 或 >=0 的整数");
    }
    out.AUTO_RETRY_MODE = "fixed";
    out.AUTO_RETRY_MAX = retryMaxNum;
  }

  const hardCap = parseNumber(root.querySelector("#auto-retry-hard-cap")?.value);
  const patience = parseNumber(root.querySelector("#auto-retry-patience")?.value);
  const minImprove = parseNumber(root.querySelector("#auto-retry-min-improve")?.value);
  const tLimit = parseNumber(root.querySelector("#quality-t-limit")?.value);
  const rippleLimit = parseNumber(root.querySelector("#quality-ripple-limit")?.value);

  if (hardCap !== null) out.AUTO_RETRY_HARD_CAP = hardCap;
  if (patience !== null) out.AUTO_RETRY_PATIENCE = patience;
  if (minImprove !== null) out.AUTO_RETRY_MIN_IMPROVE = minImprove;
  if (tLimit !== null) out.QUALITY_T_LIMIT = tLimit;
  if (rippleLimit !== null) out.QUALITY_RIPPLE_LIMIT = rippleLimit;

  return out;
}

function getExecutionOptions(root) {
  return {
    output_mode: String(root.querySelector("#output-mode")?.value || "web_capture"),
    keep_console_open: !!root.querySelector("#keep-console-open")?.checked,
  };
}

function collectPayload(root) {
  const overrides = {};
  const wildcard = {};
  const map = [
    ["start-value", "START_NM"],
    ["end-value", "END_NM"],
    ["step-value", "STEP_NM"],
    ["mesh-accuracy", "MESH_ACCURACY"],
    ["dt-factor", "DT_STABILITY_FACTOR"],
    ["runtime-fs", "SIMULATION_TIME_FS"],
    ["auto-shutoff", "AUTO_SHUTOFF_MIN"],
  ];

  map.forEach(([id, key]) => {
    const n = parseNumber(root.querySelector(`#${id}`)?.value);
    if (n !== null) wildcard[key] = n;
  });
  if (
    wildcard.START_NM !== undefined ||
    wildcard.END_NM !== undefined ||
    wildcard.STEP_NM !== undefined
  ) {
    wildcard.__scan_range__ = {
      unit: "nm",
      target: "primary",
      start_nm: wildcard.START_NM,
      end_nm: wildcard.END_NM,
      step_nm: wildcard.STEP_NM,
    };
  }
  if (wildcard.START_NM !== undefined) {
    wildcard.SCAN_START_NM = wildcard.START_NM;
    wildcard.START = wildcard.START_NM;
    wildcard.START_M = wildcard.START_NM * 1e-9;
  }
  if (wildcard.END_NM !== undefined) {
    wildcard.SCAN_STOP_NM = wildcard.END_NM;
    wildcard.END = wildcard.END_NM;
    wildcard.END_M = wildcard.END_NM * 1e-9;
  }
  if (wildcard.STEP_NM !== undefined) {
    wildcard.SCAN_STEP_NM = wildcard.STEP_NM;
    wildcard.STEP = wildcard.STEP_NM;
    wildcard.STEP_M = wildcard.STEP_NM * 1e-9;
  }
  if (Object.keys(wildcard).length) overrides["*"] = wildcard;

  const mode = activeValue(root, "mode-control") || "preview";
  const style = mode === "preview" ? "sequential" : (activeValue(root, "style-control") || "sequential");
  const payload = {
    mode,
    style,
    max_parallel: Number(root.querySelector("#max-parallel")?.value || 1),
    ids: Array.from(selectedIds),
    overrides,
    runtime_overrides: getAutotuneOverrides(root),
    execution_options: getExecutionOptions(root),
    child_timeout_s: Number(root.querySelector("#child-timeout")?.value || 3600),
  };
  try {
    console.debug("[run-control] payload", payload);
  } catch (_) {}
  return payload;
}

async function refreshLog(root) {
  if (!currentJobId) return;
  const terminal = root.querySelector("#job-log");
  try {
    const job = await api.job(currentJobId);
    currentJobMeta = job;

    if (job.output_mode === "cmd_raw") {
      terminal.textContent = [
        `任务ID: ${job.job_id}`,
        `状态: ${job.status}`,
        `output_mode: cmd_raw`,
        `cmd_pid: ${job.cmd_pid || ""}`,
        `cmd_script_path: ${job.cmd_script_path || ""}`,
        `cmd_status_dir: ${job.cmd_status_dir || ""}`,
        "stdout/stderr 原始输出请查看独立 CMD 窗口。",
      ].join("\n");
      if (job.status === "running_in_cmd" || job.status === "stopping") {
        window.setTimeout(() => refreshLog(root), 800);
      }
      return;
    }

    const log = await api.jobLog(currentJobId, { offset: currentLogOffset });
    if (log?.text) {
      terminal.textContent += log.text;
      terminal.scrollTop = terminal.scrollHeight;
    }
    currentLogOffset = Number(log?.next_offset ?? currentLogOffset) || currentLogOffset;
    if (job.status === "running" || job.status === "stopping") {
      window.setTimeout(() => refreshLog(root), 800);
    }
  } catch (error) {
    terminal.textContent += `\n[log-error] ${error.message}`;
  }
}

export async function afterRender(root) {
  root.querySelectorAll(".tree-row").forEach((row) => {
    row.addEventListener("click", () => {
      const id = String(row.dataset.scriptId);
      if (selectedIds.has(id)) selectedIds.delete(id);
      else selectedIds.add(id);
      row.classList.toggle("active");
    });
  });

  root.querySelectorAll(".segmented").forEach((seg) => {
    seg.addEventListener("click", (event) => {
      const btn = event.target.closest("button");
      if (!btn) return;
      seg.querySelectorAll("button").forEach((b) => b.classList.toggle("active", b === btn));
    });
  });

  root.querySelector("#refresh-scripts").addEventListener("click", async () => {
    try {
      await api.refreshScripts();
      toast("脚本缓存刷新完成", "success");
    } catch (error) {
      toast(error.message, "error");
    }
  });

  root.querySelector("#preview-run").addEventListener("click", async () => {
    try {
      latestPreview = await api.controllerPreview(collectPayload(root));
      root.querySelector("#point-estimate").textContent = latestPreview.estimated_points || "--";
      root.querySelector("#duration-estimate").textContent = latestPreview.estimated_duration || "--";
      root.querySelector("#job-log").textContent = (latestPreview.command || []).join(" ");
    } catch (error) {
      toast(error.message, "error");
    }
  });

  async function start() {
    let payload;
    try {
      payload = collectPayload(root);
    } catch (error) {
      toast(error.message, "error");
      return;
    }

    if (!payload.ids.length) {
      toast("请先选择至少一个脚本", "error");
      return;
    }

    const highRisk = payload.mode === "full" && payload.style === "parallel";
    openModal({
      title: highRisk ? "高风险启动确认" : "启动确认",
      danger: highRisk,
      confirmText: highRisk ? "确认 full 并行启动" : "确认启动",
      body: `<p>${highRisk ? "full + parallel 风险较高，请确认资源。" : "将通过 fdtd_master_controller.py 启动任务。"}</p><pre class="mono">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>`,
      onConfirm: async () => {
        try {
          latestPreview = await api.controllerPreview(payload);
          const job = await api.controllerStart({
            ...payload,
            preview_hash: latestPreview.preview_hash,
            confirm: true,
            risk_ack: highRisk,
          });
          currentJobId = job.job_id;
          currentJobMeta = job;
          currentLogOffset = 0;

          if (job.output_mode === "cmd_raw") {
            toast("已弹出独立 CMD 窗口", "success");
            root.querySelector("#job-log").textContent = [
              `任务ID: ${job.job_id}`,
              `状态: ${job.status}`,
              `output_mode: cmd_raw`,
              `cmd_pid: ${job.cmd_pid || ""}`,
              `cmd_script_path: ${job.cmd_script_path || ""}`,
              `cmd_status_dir: ${job.cmd_status_dir || ""}`,
              "stdout/stderr 原始输出请查看独立 CMD 窗口。",
            ].join("\n");
          } else {
            root.querySelector("#job-log").textContent = `任务已启动：${job.job_id}`;
          }
          refreshLog(root);
        } catch (error) {
          toast(error.message, "error");
        }
      },
    });
  }

  root.querySelector("#start-run").addEventListener("click", start);
  root.querySelector("#bottom-start").addEventListener("click", start);

  root.querySelector("#clear-selected").addEventListener("click", () => {
    selectedIds = new Set();
    root.querySelectorAll(".tree-row.active").forEach((row) => row.classList.remove("active"));
  });

  root.querySelector("#stop-job").addEventListener("click", async () => {
    if (!currentJobId) {
      toast("当前没有任务可停止", "error");
      return;
    }

    if ((currentJobMeta?.output_mode || "") === "cmd_raw") {
      const ok = window.confirm("当前任务在独立 CMD 中运行。停止会终止 CMD、Python 以及可能运行中的 FDTD 子进程。是否继续？");
      if (!ok) return;
    }

    try {
      await api.stopJob(currentJobId);
      toast("已发送停止任务请求", "success");
    } catch (error) {
      toast(error.message, "error");
    }
  });
}
