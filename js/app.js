import { recommend } from "./engine.js";

let optionCount = 0;
let eventCount = 0;

const optionsContainer = document.getElementById("options-container");
const eventsContainer = document.getElementById("events-container");
const resultsSection = document.getElementById("results-section");
const researchSection = document.getElementById("research-section");
const errorBox = document.getElementById("error");

function formatMoney(n) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}

function formatPct(n) {
  return `${(n * 100).toFixed(1)}%`;
}

function hideError() {
  errorBox.classList.add("hidden");
}

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.classList.remove("hidden");
}

function addOption(data = {}) {
  optionCount += 1;
  const id = data.id || String.fromCharCode(96 + optionCount);
  const card = document.createElement("div");
  card.className = "card option-card";
  card.dataset.id = id;
  card.innerHTML = `
    <div class="card-header">
      <strong>Option ${id.toUpperCase()}</strong>
      <button class="btn btn-danger btn-sm remove-option" type="button">Remove</button>
    </div>
    <div class="field"><label>Label</label><input class="opt-label" value="${data.label || `Option ${id.toUpperCase()}`}" /></div>
    <div class="grid-3">
      <div class="field"><label>Reward ($)</label><input class="opt-reward" type="number" min="0" step="1" value="${data.reward ?? 100}" /></div>
      <div class="field"><label>Cost ($)</label><input class="opt-cost" type="number" min="0" step="1" value="${data.cost ?? 10}" /></div>
      <div class="field"><label>Success prob (optional)</label><input class="opt-prob" type="number" min="0" max="1" step="0.01" value="${data.success_prob ?? ""}" placeholder="auto" /></div>
    </div>
  `;
  card.querySelector(".remove-option").addEventListener("click", () => card.remove());
  optionsContainer.appendChild(card);
  refreshEventOptionSelects();
}

function refreshEventOptionSelects() {
  const ids = [...document.querySelectorAll(".option-card")].map((c) => c.dataset.id);
  document.querySelectorAll(".evt-option").forEach((sel) => {
    const current = sel.value;
    sel.innerHTML = ids.map((id) => `<option value="${id}">${id}</option>`).join("");
    if (ids.includes(current)) sel.value = current;
  });
}

function addEvent(data = {}) {
  eventCount += 1;
  const ids = [...document.querySelectorAll(".option-card")].map((c) => c.dataset.id);
  const card = document.createElement("div");
  card.className = "card event-card";
  card.innerHTML = `
    <div class="card-header">
      <strong>Event ${eventCount}</strong>
      <button class="btn btn-danger btn-sm remove-event" type="button">Remove</button>
    </div>
    <div class="grid-2">
      <div class="field"><label>Option</label>
        <select class="evt-option">${ids.map((id) => `<option value="${id}">${id}</option>`).join("")}</select>
      </div>
      <div class="field"><label>Outcome</label>
        <select class="evt-outcome">
          <option value="success">Success</option>
          <option value="partial">Partial</option>
          <option value="failure">Failure</option>
        </select>
      </div>
    </div>
    <div class="field"><label>Notes</label><input class="evt-notes" placeholder="optional context" value="${data.notes || ""}" /></div>
  `;
  if (data.option_id) card.querySelector(".evt-option").value = data.option_id;
  if (data.outcome) card.querySelector(".evt-outcome").value = data.outcome;
  card.querySelector(".remove-event").addEventListener("click", () => card.remove());
  eventsContainer.appendChild(card);
}

function collectCase() {
  const options = [...document.querySelectorAll(".option-card")].map((card) => {
    const opt = {
      id: card.dataset.id,
      label: card.querySelector(".opt-label").value,
      reward: parseFloat(card.querySelector(".opt-reward").value),
      cost: parseFloat(card.querySelector(".opt-cost").value),
    };
    const prob = card.querySelector(".opt-prob").value;
    if (prob !== "") opt.success_prob = parseFloat(prob);
    return opt;
  });

  const past_events = [...document.querySelectorAll(".event-card")].map((card) => ({
    option_id: card.querySelector(".evt-option").value,
    outcome: card.querySelector(".evt-outcome").value,
    reward: 0,
    cost: 0,
    notes: card.querySelector(".evt-notes").value,
  }));

  return {
    subject: document.getElementById("subject").value,
    options,
    past_events,
  };
}

function renderResults(result) {
  const w = result.recommendation;
  document.getElementById("winner").innerHTML = `${w.label} <small>(${w.id})</small>`;
  document.getElementById("winner-ev").textContent = formatMoney(w.expected_value);
  document.getElementById("winner-prob").textContent = formatPct(w.success_prob);
  document.getElementById("margin").textContent = formatMoney(result.margin);

  const flagsEl = document.getElementById("flags");
  flagsEl.innerHTML = result.flags.map((f) => `<span class="flag">${f.replace("_", " ")}</span>`).join("");

  const tbody = document.getElementById("rank-body");
  tbody.innerHTML = result.ranked.map((r, i) => `
    <tr class="${i === 0 ? "winner" : ""}">
      <td>${r.label}</td>
      <td>${formatPct(r.success_prob)}</td>
      <td>${formatMoney(r.expected_value)}</td>
      <td>${r.prob_source}</td>
    </tr>
  `).join("");

  resultsSection.classList.remove("hidden");
  researchSection.classList.remove("hidden");
}

function analyze() {
  hideError();
  try {
    const caseData = collectCase();
    const result = recommend(caseData);
    renderResults(result);
  } catch (err) {
    showError(err.message);
    resultsSection.classList.add("hidden");
  }
}

function exportJson() {
  const blob = new Blob([JSON.stringify(collectCase(), null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "decision-case.json";
  a.click();
}

function importJson(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    const data = JSON.parse(e.target.result);
    document.getElementById("subject").value = data.subject || "";
    optionsContainer.innerHTML = "";
    eventsContainer.innerHTML = "";
    optionCount = 0;
    eventCount = 0;
    (data.options || []).forEach(addOption);
    (data.past_events || []).forEach(addEvent);
    analyze();
  };
  reader.readAsText(file);
}

function loadSample() {
  optionsContainer.innerHTML = "";
  eventsContainer.innerHTML = "";
  optionCount = 0;
  eventCount = 0;
  document.getElementById("subject").value = "vendor selection";
  addOption({ id: "a", label: "Proven vendor", reward: 100, cost: 10 });
  addOption({ id: "b", label: "New vendor", reward: 120, cost: 15 });
  addEvent({ option_id: "a", outcome: "success", notes: "Delivered on time" });
  addEvent({ option_id: "a", outcome: "success", notes: "Good quality" });
  addEvent({ option_id: "b", outcome: "failure", notes: "Late shipment" });
  analyze();
}

function showResearch() {
  const raw = document.getElementById("research-json").value.trim();
  const el = document.getElementById("research-results");
  if (!raw) { el.innerHTML = "<p style='color:var(--text-muted);font-size:0.85rem'>No research data.</p>"; return; }
  try {
    const data = JSON.parse(raw);
    const articles = data.articles || [];
    el.innerHTML = articles.length
      ? articles.map((a) => `
        <div class="research-item">
          <a href="${a.url}" target="_blank" rel="noopener">${a.title}</a>
          <p>${a.snippet || ""}</p>
        </div>`).join("")
      : "<p style='color:var(--text-muted)'>No articles found.</p>";
  } catch {
    el.innerHTML = "<p class='error'>Invalid JSON</p>";
  }
}

document.getElementById("add-option").addEventListener("click", () => addOption());
document.getElementById("add-event").addEventListener("click", () => addEvent());
document.getElementById("analyze-btn").addEventListener("click", analyze);
document.getElementById("export-btn").addEventListener("click", exportJson);
document.getElementById("import-file").addEventListener("change", (e) => {
  if (e.target.files[0]) importJson(e.target.files[0]);
});
document.getElementById("load-sample").addEventListener("click", loadSample);
document.getElementById("show-research").addEventListener("click", showResearch);
document.getElementById("copy-cmd").addEventListener("click", () => {
  const subject = document.getElementById("subject").value.trim() || "your subject";
  const cmd = `python scripts/grokipedia-context.py "${subject}"`;
  navigator.clipboard.writeText(cmd);
  document.getElementById("research-cmd").textContent = cmd;
});
document.getElementById("subject").addEventListener("input", (e) => {
  const s = e.target.value.trim() || "subject";
  document.getElementById("research-cmd").textContent = `python scripts/grokipedia-context.py "${s}"`;
});

addOption({ id: "a", label: "Option A", reward: 100, cost: 10, success_prob: 0.7 });
addOption({ id: "b", label: "Option B", reward: 80, cost: 5, success_prob: 0.6 });