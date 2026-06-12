const API_BASE = (() => {
  if (window.LEXAI_API_BASE) return window.LEXAI_API_BASE.replace(/\/$/, "");
  return "";
})();

const SESSION_KEY = "lexai_public_session";
const sessionId = (() => {
  const saved = localStorage.getItem(SESSION_KEY);
  if (saved) return saved;
  const created = crypto.randomUUID();
  localStorage.setItem(SESSION_KEY, created);
  return created;
})();

const state = {
  current: null,
  variants: [],
  allFeedbacks: [],
  quotaLeft: Infinity
};

const nodes = {
  prompt: document.getElementById("prompt"),
  language: document.getElementById("language"),
  model: document.getElementById("modelSelect"),
  fileInput: document.getElementById("fileInput"),
  formStatus: document.getElementById("formStatus"),
  tableStatus: document.getElementById("tableStatus"),
  resultCard: document.getElementById("resultCard"),
  resultTitle: document.getElementById("resultTitle"),
  resultText: document.getElementById("resultText"),
  feedbackControls: document.getElementById("feedbackControls"),
  variantsSection: document.getElementById("variantsSection"),
  variantList: document.getElementById("variantList"),
  feedbackBody: document.getElementById("feedbackBody"),
  backendHealth: document.getElementById("backendHealth"),
  quotaBar: document.getElementById("quotaBar"),
  quotaWrap: document.getElementById("quotaWrap"),
  filterSelect: document.getElementById("filterSelect"),
  variantsChk: document.getElementById("variantsChk"),
  busyOverlay: document.getElementById("busyOverlay"),
  busyText: document.getElementById("busyText")
};

function setStatus(el, msg, isError = false) {
  el.textContent = msg;
  el.style.color = isError ? "#c84c31" : "#5e6a76";
}

function setBusy(active, message = "Working...") {
  if (!nodes.busyOverlay || !nodes.busyText) return;
  nodes.busyText.textContent = message;
  nodes.busyOverlay.classList.toggle("active", active);
  nodes.busyOverlay.setAttribute("aria-hidden", active ? "false" : "true");
  document.querySelectorAll("button, select, textarea, input[type='file']").forEach((el) => {
    el.disabled = active;
  });
  if (!active) syncModeUi();
}

function activeMode() {
  return document.querySelector('input[name="mode"]:checked').value;
}

function api(path, options = {}) {
  if (!API_BASE) {
    throw new Error("Backend URL is not configured. Set window.LEXAI_API_BASE in frontend/config.js.");
  }
  const headers = new Headers(options.headers || {});
  headers.set("X-Lex-Session", sessionId);
  return fetch(`${API_BASE}${path}`, { ...options, headers });
}

async function parseJson(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return response.json();
  return {};
}

async function requestJson(path, options = {}) {
  const response = await api(path, options);
  const payload = await parseJson(response);
  if (!response.ok) {
    const detail = payload.detail || `${response.status} ${response.statusText}`;
    throw new Error(detail);
  }
  return payload;
}

function resetOutput() {
  state.current = null;
  state.variants = [];
  nodes.resultCard.style.display = "none";
  nodes.feedbackControls.style.display = "none";
  nodes.variantsSection.style.display = "none";
  nodes.variantList.innerHTML = "";
}

function renderOutput(title, text) {
  nodes.resultTitle.textContent = title;
  nodes.resultText.textContent = text;
  nodes.resultCard.style.display = "block";
  nodes.feedbackControls.style.display = "flex";
  nodes.variantsSection.style.display = "none";
  nodes.variantList.innerHTML = "";
  focusResultCard();
}

function focusResultCard() {
  if (!nodes.resultCard) return;
  window.setTimeout(() => {
    nodes.resultCard.scrollIntoView({ behavior: "smooth", block: "start" });
    const copyButton = document.getElementById("copyBtn");
    if (copyButton instanceof HTMLButtonElement) {
      copyButton.focus();
    }
  }, 80);
}

function focusVariantsSection() {
  if (!nodes.variantsSection) return;
  nodes.variantsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  const firstAction = nodes.variantList?.querySelector("button");
  if (firstAction instanceof HTMLButtonElement) {
    window.setTimeout(() => firstAction.focus(), 250);
  }
}

function renderFeedbackRows(rows) {
  if (!rows.length) {
    nodes.feedbackBody.innerHTML = '<tr><td colspan="5">No feedback saved yet.</td></tr>';
    return;
  }

  nodes.feedbackBody.innerHTML = rows.map((row, index) => `
    <tr>
      <td>${index + 1}</td>
      <td>${escapeHtml(row.original_prompt)}</td>
      <td>${escapeHtml(row.target_language)}</td>
      <td>${escapeHtml(row.feedback)}</td>
      <td>${escapeHtml(row.translated_text)}</td>
    </tr>
  `).join("");
}

function filteredFeedbackRows() {
  const filter = nodes.filterSelect?.value || "all";
  return state.allFeedbacks.filter((row) => {
    if (filter === "all") return true;
    return String(row.feedback || "").startsWith(filter);
  });
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function loadFeedbacks() {
  setStatus(nodes.tableStatus, "Loading feedback history...");
  try {
    const includeVariants = nodes.variantsChk?.checked ? "true" : "false";
    const rows = await requestJson(`/feedbacks/?include_variants=${includeVariants}`);
    state.allFeedbacks = rows;
    const visibleRows = filteredFeedbackRows();
    renderFeedbackRows(visibleRows);
    setStatus(
      nodes.tableStatus,
      visibleRows.length
        ? `Loaded ${visibleRows.length} visible rows from ${rows.length} saved rows.`
        : "No saved rows yet."
    );
  } catch (error) {
    state.allFeedbacks = [];
    renderFeedbackRows([]);
    setStatus(nodes.tableStatus, `Could not load feedback history: ${error.message}`, true);
  }
}

function renderQuota(limit, used, day) {
  if (!nodes.quotaBar || !nodes.quotaWrap) return;
  const max = Number(limit) || 0;
  const usedVal = Number(used) || 0;
  const left = Math.max(0, max - usedVal);
  const rawPct = max > 0 ? (usedVal / max) * 100 : 0;
  const pct = usedVal > 0 ? Math.max(8, Math.min(100, Math.round(rawPct))) : 0;
  state.quotaLeft = Number.isFinite(left) ? left : Infinity;
  nodes.quotaBar.style.width = `${pct}%`;
  nodes.quotaWrap.title = `Daily quota: ${usedVal.toLocaleString()} / ${max.toLocaleString()} chars - ${day} (ET)`;
}

async function refreshQuota() {
  if (!API_BASE) return;
  try {
    const payload = await requestJson("/quota", { cache: "no-store" });
    renderQuota(payload.limit, payload.used, payload.day);
  } catch {
    state.quotaLeft = Infinity;
    if (nodes.quotaBar) nodes.quotaBar.style.width = "0%";
  }
}

async function checkBackendHealth() {
  if (!nodes.backendHealth) return;
  if (!API_BASE) {
    nodes.backendHealth.textContent = "Backend URL not configured. Set frontend/config.js before deploying the static frontend.";
    nodes.backendHealth.style.color = "#c84c31";
    return;
  }

  nodes.backendHealth.textContent = "Checking backend connection…";
  try {
    const response = await fetch(`${API_BASE}/healthz`, { headers: { Accept: "application/json" } });
    const payload = await parseJson(response);
    if (!response.ok) throw new Error(payload.detail || "Health check failed");
    const dbState = payload.database_ok ? "database connected" : (payload.database_configured ? "database unavailable" : "database not configured");
    nodes.backendHealth.textContent = `Backend connected. ${dbState}.`;
    nodes.backendHealth.style.color = payload.database_ok ? "#2d8f5a" : "#5e6a76";
  } catch (error) {
    nodes.backendHealth.textContent = `Backend unavailable: ${error.message}`;
    nodes.backendHealth.style.color = "#c84c31";
  }
}

function hasQuotaForText(text) {
  if (!Number.isFinite(state.quotaLeft)) return true;
  return text.length <= state.quotaLeft;
}

async function runWorkflow() {
  const prompt = nodes.prompt.value.trim();
  if (!prompt) {
    setStatus(nodes.formStatus, "Enter text before running the workflow.", true);
    return;
  }

  const mode = activeMode();
  const model = nodes.model.value;
  if (mode === "translate" && !hasQuotaForText(prompt)) {
    setStatus(nodes.formStatus, "That text exceeds the remaining daily quota for this browser session.", true);
    return;
  }
  setStatus(nodes.formStatus, "Running workflow...");
  setBusy(true, mode === "rephrase" ? "Rewriting English copy..." : "Running translation workflow...");
  resetOutput();

  try {
    if (mode === "rephrase") {
      const data = await requestJson("/rephrase/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, model, keep_length: true })
      });

      state.current = {
        original_prompt: prompt,
        translated_text: data.rephrased,
        target_language: "EN"
      };
      renderOutput("Rewritten Output", data.rephrased);
    } else {
      const targetLanguage = nodes.language.value;
      const data = await requestJson("/full-process/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, target_language: targetLanguage, model })
      });

      state.current = {
        original_prompt: prompt,
        translated_text: data.translated_text,
        target_language: targetLanguage
      };
      renderOutput("Translated Output", data.translated_text);
    }

    setStatus(nodes.formStatus, "Workflow completed.");
    if (mode === "translate") await refreshQuota();
  } catch (error) {
    setStatus(nodes.formStatus, `Workflow failed: ${error.message}`, true);
  } finally {
    setBusy(false);
  }
}

async function extractText() {
  const file = nodes.fileInput.files[0];
  if (!file) {
    setStatus(nodes.formStatus, "Choose a PDF or image first.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  const endpoint = file.name.toLowerCase().endsWith(".pdf") ? "/upload-pdf/" : "/upload-image/";
  setStatus(nodes.formStatus, "Extracting text...");

  try {
    const data = await requestJson(endpoint, { method: "POST", body: formData });
    nodes.prompt.value = data.extracted_text || "";
    setStatus(nodes.formStatus, data.extracted_text ? "Text extracted into the source field." : "No text was extracted.");
  } catch (error) {
    setStatus(nodes.formStatus, `Extraction failed: ${error.message}`, true);
  }
}

async function saveFeedback(type) {
  if (!state.current) {
    setStatus(nodes.formStatus, "Run the workflow before saving feedback.", true);
    return false;
  }

  await requestJson("/feedback/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      original_prompt: state.current.original_prompt,
      translated_text: state.current.translated_text,
      target_language: state.current.target_language,
      feedback: type
    })
  });
  await loadFeedbacks();
  return true;
}

async function generateVariants() {
  if (!state.current) return;
  if (!hasQuotaForText(state.current.original_prompt)) {
    setStatus(nodes.formStatus, "Generating variants would exceed the remaining daily quota.", true);
    return;
  }
  setStatus(nodes.formStatus, "Generating alternative outputs...");
  setBusy(true, "Generating 5 alternative outputs...");

  try {
    const data = await requestJson("/copy-variants/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: state.current.original_prompt,
        target_language: state.current.target_language,
        model: nodes.model.value
      })
    });

    state.variants = data.variants || [];
    nodes.variantsSection.style.display = state.variants.length ? "block" : "none";
    nodes.variantList.innerHTML = state.variants.map((text, index) => `
      <li>
        <span>${escapeHtml(text)}</span>
        <div class="variant-actions">
          <button class="secondary" data-index="${index}" data-rating="Good" type="button">Good</button>
          <button class="danger" data-index="${index}" data-rating="Bad" type="button">Bad</button>
        </div>
      </li>
    `).join("");
    if (state.variants.length && nodes.variantsChk) {
      nodes.variantsChk.checked = true;
    }
    setStatus(nodes.formStatus, state.variants.length ? "Alternative outputs ready." : "No alternatives returned.");
    if (state.variants.length) focusVariantsSection();
    await refreshQuota();
  } catch (error) {
    setStatus(nodes.formStatus, `Could not generate alternatives: ${error.message}`, true);
  } finally {
    setBusy(false);
  }
}

async function handleVariantVote(event) {
  const button = event.target.closest("button[data-index]");
  if (!button || !state.current) return;

  const variantText = state.variants[Number(button.dataset.index)];
  if (!variantText) return;

  try {
    await requestJson("/variant-feedback/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        original_prompt: state.current.original_prompt,
        target_language: state.current.target_language,
        variant_text: variantText,
        rating: button.dataset.rating
      })
    });
    if (nodes.variantsChk) {
      nodes.variantsChk.checked = true;
    }
    await loadFeedbacks();
    button.closest("li").style.opacity = ".65";
    setStatus(nodes.formStatus, "Variant feedback saved.");
  } catch (error) {
    setStatus(nodes.formStatus, `Could not save variant feedback: ${error.message}`, true);
  }
}

async function critiqueAndRegenerate() {
  if (!state.current) {
    setStatus(nodes.formStatus, "Run the workflow before requesting regeneration.", true);
    return;
  }

  const reason = window.prompt("What went wrong with this translation?");
  if (!reason) return;

  setStatus(nodes.formStatus, "Regenerating from critique...");
  setBusy(true, "Regenerating translation from your critique...");
  try {
    const data = await requestJson("/feedback/regenerate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        original_prompt: state.current.original_prompt,
        translated_text: state.current.translated_text,
        target_language: state.current.target_language,
        reason,
        model: nodes.model.value
      })
    });

    state.current.original_prompt = data.improved_prompt;
    state.current.translated_text = data.new_translation;
    renderOutput("Regenerated Output", data.new_translation);
    nodes.prompt.value = data.improved_prompt;
    await loadFeedbacks();
    await refreshQuota();
    setStatus(nodes.formStatus, "Regenerated output ready.");
  } catch (error) {
    setStatus(nodes.formStatus, `Regeneration failed: ${error.message}`, true);
  } finally {
    setBusy(false);
  }
}

async function downloadFeedbackExport() {
  try {
    const params = new URLSearchParams();
    const filter = nodes.filterSelect?.value || "all";
    if (filter !== "all") params.set("type", filter);
    params.set("include_variants", nodes.variantsChk?.checked ? "true" : "false");
    const response = await api(`/feedbacks/download?${params.toString()}`);
    if (!response.ok) {
      const payload = await parseJson(response);
      throw new Error(payload.detail || "Download failed");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "lexai_feedbacks.xlsx";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setStatus(nodes.tableStatus, "Excel export downloaded.");
  } catch (error) {
    setStatus(nodes.tableStatus, `Could not download export: ${error.message}`, true);
  }
}

async function clearFeedbacks() {
  if (!window.confirm("Delete all saved feedback rows for this local demo session?")) return;
  try {
    await requestJson("/feedbacks/clear", { method: "DELETE" });
    await loadFeedbacks();
    setStatus(nodes.tableStatus, "Feedback history cleared.");
  } catch (error) {
    setStatus(nodes.tableStatus, `Could not clear feedback history: ${error.message}`, true);
  }
}

function copyOutput() {
  if (!state.current) return;
  navigator.clipboard.writeText(state.current.translated_text).then(
    () => setStatus(nodes.formStatus, "Output copied to clipboard."),
    () => setStatus(nodes.formStatus, "Clipboard copy failed.", true)
  );
}

function syncModeUi() {
  const isRephrase = activeMode() === "rephrase";
  nodes.language.disabled = isRephrase;
  nodes.language.style.opacity = isRephrase ? ".55" : "1";
}

document.getElementById("runBtn").addEventListener("click", runWorkflow);
document.getElementById("uploadBtn").addEventListener("click", extractText);
document.getElementById("clearInputBtn").addEventListener("click", () => {
  nodes.prompt.value = "";
  nodes.fileInput.value = "";
  setStatus(nodes.formStatus, "");
  resetOutput();
});
document.getElementById("goodBtn").addEventListener("click", async () => {
  try {
    const saved = await saveFeedback("Good");
    if (saved && window.confirm("Saved. Would you like 5 alternative suggestions?")) {
      await generateVariants();
    }
  } catch (error) {
    setStatus(nodes.formStatus, `Could not save feedback: ${error.message}`, true);
  }
});
document.getElementById("badBtn").addEventListener("click", critiqueAndRegenerate);
document.getElementById("copyBtn").addEventListener("click", copyOutput);
document.getElementById("refreshBtn").addEventListener("click", loadFeedbacks);
document.getElementById("downloadBtn").addEventListener("click", downloadFeedbackExport);
document.getElementById("clearFeedbackBtn").addEventListener("click", clearFeedbacks);
nodes.variantList.addEventListener("click", handleVariantVote);
nodes.filterSelect?.addEventListener("change", () => {
  const visibleRows = filteredFeedbackRows();
  renderFeedbackRows(visibleRows);
  setStatus(
    nodes.tableStatus,
    visibleRows.length
      ? `Showing ${visibleRows.length} filtered rows from ${state.allFeedbacks.length} saved rows.`
      : "No feedback rows match the current filter."
  );
});
nodes.variantsChk?.addEventListener("change", loadFeedbacks);
document.querySelectorAll('input[name="mode"]').forEach((radio) => {
  radio.addEventListener("change", syncModeUi);
});

syncModeUi();
checkBackendHealth();
refreshQuota();
loadFeedbacks();
