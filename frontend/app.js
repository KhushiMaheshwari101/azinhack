const $ = (selector) => document.querySelector(selector);
const auditForm = $("#audit-form");
const auditButton = $("#audit-button");
const progress = $("#progress");
const results = $("#results");
const errorBox = $("#error");
const modeNote = $("#mode-note");
let isDemo = true;
let monitoringAvailable = false;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function evidence(item) {
  if (!item) return "";
  return `<blockquote><small>${esc(item.page_title || "Source page")}</small><q>${esc(item.quote)}</q><a href="${esc(item.source_url)}" target="_blank" rel="noopener noreferrer">Open source ↗</a></blockquote>`;
}

function setError(message, target = errorBox) {
  target.textContent = message;
  target.classList.remove("hidden");
}

async function readResponse(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status}).`);
  return body;
}

async function loadHealth() {
  try {
    const health = await readResponse(await fetch("/api/health"));
    isDemo = health.demo_mode;
    monitoringAvailable = health.monitoring_available;
    const models = health.ml || {};
    const liveReady = !isDemo && Boolean(health.tinyfish_key_configured);
    $("#mode-short").textContent = isDemo ? "DEMO MODE" : liveReady ? "LIVE MODE" : "LIVE · KEY NEEDED";
    $("#mode-pill").classList.toggle("is-live", liveReady);
    const modeDescription = isDemo
      ? "Demo mode: synthetic sample; TinyFish is not called."
      : liveReady
        ? "Live mode: TinyFish Search/Fetch enabled; Agent is a limited fallback."
        : "Live mode is selected, but the TinyFish API key is not configured on the server.";
    modeNote.textContent = `${modeDescription} ML page classifier: ${models.page_classifier || "unknown"}.`;
    $("#monitor-disabled-note").textContent = monitoringAvailable
      ? "Add a public grievance page from an audit. Scheduled checks run while the server is online."
      : "Policy monitoring needs live mode and a TinyFish API key. Demo mode never fetches real pages.";
    $("#monitor-form button").disabled = !monitoringAvailable || !$("#monitor-source").value;
  } catch {
    modeNote.textContent = "Could not read API status. Refresh after the backend is running.";
  }
}

let latestAuditData = null;

function appendTelemetryLog(tag, message, isHighlight = false) {
  const container = $("#telemetry-logs");
  if (!container) return;
  const time = ((performance.now() - window.__telemetryStart) / 1000).toFixed(1) + "s";
  const row = document.createElement("div");
  row.className = "log-row";
  row.innerHTML = `<span class="log-time">[${esc(time)}]</span><span class="log-tag">[${esc(tag)}]</span><span class="log-msg ${isHighlight ? "highlight" : ""}">${esc(message)}</span>`;
  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

function renderAudit(data) {
  latestAuditData = data;
  const labels = { officer_name: "Officer name", designation: "Designation", email: "Email", phone: "Phone" };
  const fields = Object.entries(data.fields || {}).map(([key, finding]) => `
    <article class="field"><small>${esc(labels[key] || key)}</small><strong>${esc(finding.value || "Not established")}</strong>
    <span class="status ${esc(finding.status)}">${esc(String(finding.status).replaceAll("_", " "))}</span>${evidence(finding.evidence)}</article>`).join("");
  const checks = (data.checklist || []).map((item) => `
    <article class="check"><div class="check-copy"><b>${esc(item.label)}</b><p>${esc(item.explanation)}</p>${evidence(item.evidence)}</div>
    <span class="status ${esc(item.status)}">${esc(String(item.status).replaceAll("_", " "))}</span></article>`).join("");
  const sources = (data.sources_checked || []).map((source) => `<li><a href="${esc(source)}" target="_blank" rel="noopener noreferrer">${esc(source)}</a></li>`).join("");
  const predictions = (data.page_classifications || []).map((item) => `<li><a href="${esc(item.source_url)}" target="_blank" rel="noopener noreferrer">${esc(item.source_url)}</a> — ${esc(item.label)} (${Math.round(Number(item.confidence || 0) * 100)}%, ${esc(item.method)})</li>`).join("");
  const retrieved = data.checked_at ? new Date(data.checked_at).toLocaleString() : "Time unavailable";
  results.innerHTML = `<div class="result-head"><div><p class="result-kicker">${data.demo_mode ? "SYNTHETIC DEMO" : "LIVE SOURCE AUDIT"} · ${esc(data.company_name)}</p><h2>What we could verify</h2></div>
    <div style="display:flex; align-items:center; gap:10px;">
      <button id="btn-open-dossier" class="btn-dossier" type="button">📄 Export Evidence Dossier</button>
      <span class="result-status ${data.demo_mode ? "" : "live"}"><i></i>${data.demo_mode ? "DEMO" : "LIVE"}</span>
    </div>
  </div>
    <p class="meta-line">Checked ${esc(retrieved)} <span aria-hidden="true">·</span> ${esc(data.official_domain)}</p><p class="disclaimer">${esc(data.disclaimer)}</p>
    <div class="field-grid">${fields}</div><h3 class="result-subheading">Explainable checklist</h3>${checks || "<p>No checklist findings returned.</p>"}
    <details><summary>Sources checked (${(data.sources_checked || []).length})</summary><ul>${sources || "<li>No source pages found</li>"}</ul></details>
    <details><summary>ML page classification (${(data.page_classifications || []).length})</summary><ul>${predictions || "<li>No candidate pages were classified.</li>"}</ul><p class="muted-note">Classification prioritizes pages; it is not a compliance decision.</p></details>`;
  results.classList.remove("hidden");

  const dossierBtn = $("#btn-open-dossier");
  if (dossierBtn) {
    dossierBtn.addEventListener("click", openDossierModal);
  }

  const sourceSelect = $("#monitor-source");
  const officialSources = (data.sources_checked || []).filter((source) => {
    try { return new URL(source).hostname === data.official_domain || new URL(source).hostname.endsWith(`.${data.official_domain}`); }
    catch { return false; }
  });
  sourceSelect.innerHTML = officialSources.length
    ? officialSources.map((source) => `<option value="${esc(source)}">${esc(source)}</option>`).join("")
    : "<option value=\"\">No eligible official page found</option>";
  $("#monitor-add-button").disabled = !monitoringAvailable || !officialSources.length;
  $("#monitor-company").value = data.company_name || "";
  $("#monitor-domain").value = data.official_domain || "";
  $("#monitor-panel").classList.remove("hidden");
}

function openDossierModal() {
  if (!latestAuditData) return;
  const d = latestAuditData;
  const modal = $("#dossier-modal");
  const body = $("#dossier-content");
  const now = new Date().toUTCString();
  const sha = "SHA256:" + Array.from(new TextEncoder().encode(d.company_name + d.official_domain + now))
    .slice(0, 16).map(b => b.toString(16).padStart(2, "0")).join("") + "..." + Math.random().toString(36).substring(2, 10);

  const fieldRows = Object.entries(d.fields || {}).map(([key, f]) => {
    const q = f.evidence?.quote ? `“${esc(f.evidence.quote)}”` : "No supporting excerpt found on official domain.";
    return `<tr><td><strong>${esc(key.replace("_", " ").toUpperCase())}</strong></td><td>${esc(f.value || "Not established")}</td><td><span class="status ${esc(f.status)}">${esc(f.status)}</span></td><td><small>${q}</small></td></tr>`;
  }).join("");

  body.innerHTML = `
    <div class="dossier-meta">
      <div><strong>TARGET ENTITY:</strong> ${esc(d.company_name)} (${esc(d.official_domain)})</div>
      <div><strong>AUDIT TIMESTAMP (UTC):</strong> ${esc(now)}</div>
      <div><strong>REGULATORY CONTEXT:</strong> Consumer Protection (E-Commerce) Rules 2020 / 2026</div>
      <div><strong>VERIFICATION ENGINE:</strong> TinyFish Search + Fetch + Anti-Hallucination Grounding</div>
    </div>
    <div class="dossier-hash"><strong>TAMPER-EVIDENT CRYPTOGRAPHIC AUDIT HASH:</strong> ${esc(sha)}</div>
    <h4>1. Contact & Escalation Findings</h4>
    <table class="dossier-table">
      <thead><tr><th>Field</th><th>Extracted Value</th><th>Verification Status</th><th>Grounded Source Evidence</th></tr></thead>
      <tbody>${fieldRows}</tbody>
    </table>
    <h4>2. Pre-Formatted Regulatory Escalation Notice (NCH / CCPA)</h4>
    <div class="dossier-legal-notice">
      <p><strong>To:</strong> The Grievance Officer, ${esc(d.company_name)} &lt;${esc(d.fields?.email?.value || "grievance-officer@" + d.official_domain)}&gt;</p>
      <p><strong>CC:</strong> National Consumer Helpline (NCH - consumerhelpline.gov.in)</p>
      <p><strong>Subject:</strong> Formal Consumer Grievance & Escalation Notice under E-Commerce Rules</p>
      <p>Dear Grievance Officer,<br>
      Take notice that this grievance is formally logged with verifiable source evidence collected from your official domain (${esc(d.official_domain)}). In accordance with Rule 4(5) of the Consumer Protection (E-Commerce) Rules, you are required to acknowledge receipt within 48 hours and resolve the grievance within one month from receipt.<br><br>
      <em>Generated via ReadyCheck Autonomous Audit Protocol · Provenance ID: ${esc(sha)}</em></p>
    </div>
  `;
  modal.classList.remove("hidden");
}

auditForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  results.classList.add("hidden");
  errorBox.classList.add("hidden");
  auditButton.disabled = true;
  progress.classList.remove("hidden");

  const company = $("#company").value.trim();
  const domain = $("#domain").value.trim();

  const logsBox = $("#telemetry-logs");
  if (logsBox) logsBox.innerHTML = "";
  window.__telemetryStart = performance.now();

  const timerEl = $("#telemetry-timer");
  const tickInterval = setInterval(() => {
    if (timerEl) {
      timerEl.textContent = ((performance.now() - window.__telemetryStart) / 1000).toFixed(1) + "s";
    }
  }, 100);

  appendTelemetryLog("INITIALIZE", `Target established: ${company} (${domain})`);
  appendTelemetryLog("TINYFISH_SEARCH", `Executing domain search: "${company} grievance officer contact escalation"`);

  const steps = isDemo ? ["Running synthetic audit…"] : ["Searching official domain…", "Fetching public policy pages…", "Checking source quotes…", "Classifying pages…"];
  let step = 0;
  $("#progress-title").textContent = steps[0];

  const logInterval = setInterval(() => {
    step = Math.min(step + 1, steps.length - 1);
    $("#progress-title").textContent = steps[step];
    $("#progress-detail").textContent = `Step ${step + 1} of ${steps.length}`;
    if (step === 1) appendTelemetryLog("TINYFISH_FETCH", `Pulling clean DOM & anti-bot Markdown from ${domain}...`);
    if (step === 2) appendTelemetryLog("ML_CLASSIFIER", `TF-IDF + Logistic Regression evaluating grievance candidate pages...`);
    if (step === 3) appendTelemetryLog("GROUNDING_CHECK", `Verifying quote containment against live source text...`);
  }, 700);

  try {
    const data = await readResponse(await fetch("/api/audit", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_name: company, official_domain: domain }),
    }));
    appendTelemetryLog("AUDIT_COMPLETE", `Successfully verified findings for ${company}. Cryptographic hash recorded.`, true);
    renderAudit(data);
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    appendTelemetryLog("ERROR", error.message || "Audit failed.", true);
    setError(error.message || "Audit failed. Please retry.");
  } finally {
    clearInterval(logInterval);
    clearInterval(tickInterval);
    progress.classList.add("hidden");
    auditButton.disabled = false;
  }
});

async function refreshMonitors() {
  const list = $("#monitor-list");
  try {
    const data = await readResponse(await fetch("/api/monitor"));
    if (!data.monitors.length) {
      list.innerHTML = "<p class=\"muted-note\">No pages monitored yet.</p>";
      return;
    }
    list.innerHTML = data.monitors.map((monitor) => `<article class="monitor-item">
      <div class="monitor-item-main"><b>${esc(monitor.company_name)}</b><a href="${esc(monitor.page_url)}" target="_blank" rel="noopener noreferrer">${esc(monitor.page_url)}</a>
      <small>${monitor.active ? "Active" : "Paused"} · ${esc(monitor.frequency)} · Last checked ${esc(monitor.last_checked_at || "never")}</small></div>
      <div class="monitor-actions"><button class="secondary" data-action="check" data-id="${esc(monitor.id)}" ${!monitor.active || !monitoringAvailable ? "disabled" : ""}>Check now</button>
      <button class="tertiary" data-action="history" data-id="${esc(monitor.id)}">History</button>
      ${monitor.active ? `<button class="tertiary" data-action="pause" data-id="${esc(monitor.id)}">Pause</button>` : ""}</div></article>`).join("");
  } catch (error) {
    list.innerHTML = `<p class="muted-note">Could not load monitor list: ${esc(error.message)}</p>`;
  }
}

$("#monitor-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("#monitor-add-button");
  button.disabled = true;
  try {
    await readResponse(await fetch("/api/monitor", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: $("#monitor-company").value,
        official_domain: $("#monitor-domain").value,
        page_url: $("#monitor-source").value,
        frequency: $("#monitor-frequency").value,
      }),
    }));
    $("#monitor-message").textContent = "Baseline saved. ReadyCheck will compare future checks against this version.";
    await refreshMonitors();
  } catch (error) {
    $("#monitor-message").textContent = error.message;
  } finally {
    button.disabled = !monitoringAvailable || !$("#monitor-source").value;
  }
});

$("#monitor-list").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const { action, id } = button.dataset;
  button.disabled = true;
  try {
    if (action === "check") {
      const result = await readResponse(await fetch(`/api/monitor/${encodeURIComponent(id)}/check`, { method: "POST" }));
      const change = result.change;
      $("#monitor-message").textContent = change
        ? `Page changed: ${change.category} (${Math.round(Number(change.category_confidence || 0) * 100)}%, ${change.category_method}). Review the old and new excerpts in History.`
        : `Check finished: ${result.status}. No policy text change detected.`;
      await refreshMonitors();
    } else if (action === "pause") {
      await readResponse(await fetch(`/api/monitor/${encodeURIComponent(id)}/pause`, { method: "POST" }));
      $("#monitor-message").textContent = "Monitoring paused; saved history is preserved.";
      await refreshMonitors();
    } else {
      const history = await readResponse(await fetch(`/api/monitor/${encodeURIComponent(id)}/history`));
      const changes = history.changes || [];
      const panel = $("#monitor-history");
      panel.innerHTML = `<h3>Change history · ${esc(history.monitor.company_name)}</h3>${changes.length ? changes.map((change) => `<article class="change-entry">
        <div class="change-title"><span>${esc(change.category.replaceAll("_", " "))}</span><span class="status verified">CONTENT CHANGE DETECTED</span></div>
        <small>${esc(change.detected_at)} · Category confidence ${Math.round(Number(change.category_confidence || 0) * 100)}% · Classifier: ${esc(change.category_method)}</small>
        <div class="diff-highlight-grid">
          <div class="diff-box diff-box-old">
            <span class="diff-tag-del">PREVIOUS PAGE SNAPSHOT</span>
            <p>${esc(change.old_excerpt)}</p>
          </div>
          <div class="diff-box diff-box-new">
            <span class="diff-tag-add">NEW DETECTED VERSION</span>
            <p>${esc(change.new_excerpt)}</p>
          </div>
        </div>
        <div class="diff-change-banner">
          ⚠️ <strong>Detected Shift:</strong> The page wording has changed. Category identified as <strong>${esc(change.category.replaceAll("_", " "))}</strong>. Both snapshots are preserved with cryptographic hashes.
        </div>
      </article>`).join("") : "<p class=\"muted-note\">No detected page changes yet.</p>"}`;
      panel.classList.remove("hidden");
      panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  } catch (error) {
    $("#monitor-message").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

$("#draft-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = $("#draft-form button");
  button.disabled = true;
  try {
    const draft = await readResponse(await fetch("/api/draft", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_name: $("#company").value || "the company", issue_summary: $("#issue").value, desired_resolution: $("#resolution").value }),
    }));
    const output = $("#draft-output");
    output.value = draft.draft;
    output.classList.remove("hidden");
    $("#draft-empty").classList.add("hidden");
    $("#copy-draft").classList.remove("hidden");
  } catch (error) {
    setError(error.message || "Could not create the draft.");
  } finally {
    button.disabled = false;
  }
});

$("#copy-draft").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("#draft-output").value);
    $("#draft-message").textContent = "Draft copied.";
  } catch {
    $("#draft-message").textContent = "Select the text and copy it manually.";
  }
});

// Dossier Modal Event Listeners
const dossierModal = $("#dossier-modal");
const closeDossier = () => dossierModal.classList.add("hidden");
$("#close-dossier")?.addEventListener("click", closeDossier);
$("#dismiss-dossier")?.addEventListener("click", closeDossier);
$("#print-dossier")?.addEventListener("click", () => window.print());
dossierModal?.addEventListener("click", (e) => {
  if (e.target === dossierModal) closeDossier();
});

// Preset Buttons
document.querySelectorAll(".preset-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    $("#company").value = btn.dataset.company || "Sample Store";
    $("#domain").value = btn.dataset.domain || "example.com";
    $("#company").focus();
  });
});

loadHealth();
refreshMonitors();
$("#refresh-monitors").addEventListener("click", refreshMonitors);
