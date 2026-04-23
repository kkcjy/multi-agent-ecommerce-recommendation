const experimentsContainer = document.getElementById("experimentsContainer");
const metricsContainer = document.getElementById("metricsContainer");
const reloadExperimentsBtn = document.getElementById("reloadExperiments");
const reloadMetricsBtn = document.getElementById("reloadMetrics");
const outcomeForm = document.getElementById("outcomeForm");
const outcomeState = document.getElementById("outcomeState");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setOutcomeState(message, statusClass) {
  outcomeState.textContent = message;
  outcomeState.className = "status";
  if (statusClass) {
    outcomeState.classList.add(statusClass);
  }
}

function renderExperiments(experiments) {
  const keys = Object.keys(experiments || {});
  if (keys.length === 0) {
    experimentsContainer.innerHTML = "<div class=\"status\">No experiment data.</div>";
    return;
  }

  experimentsContainer.innerHTML = keys
    .map((expId) => {
      const exp = experiments[expId];
      const groupsHtml = (exp.groups || [])
        .map((g) => {
          return [
            "<div class=\"kv\"><strong>Group</strong><span>" + escapeHtml(g.name) + "</span></div>",
            "<div class=\"kv\"><strong>Weight</strong><span>" + escapeHtml(g.weight) + "</span></div>",
            "<div class=\"kv\"><strong>Success/Fail</strong><span>" + escapeHtml(g.successes) + " / " + escapeHtml(g.failures) + "</span></div>",
            "<div class=\"kv\"><strong>Config</strong><span>" + escapeHtml(JSON.stringify(g.config || {})) + "</span></div>",
            "<hr />",
          ].join("");
        })
        .join("");

      return [
        "<article class=\"info-card\">",
        "  <div class=\"info-title\">" + escapeHtml(expId) + " - " + escapeHtml(exp.name || "") + "</div>",
        "  <div class=\"kv\"><strong>Enabled</strong><span>" + escapeHtml(exp.enabled) + "</span></div>",
        groupsHtml,
        "</article>",
      ].join("");
    })
    .join("");
}

function renderMetrics(metrics) {
  const agents = metrics.agents || {};
  const names = Object.keys(agents);
  if (names.length === 0) {
    metricsContainer.innerHTML = "<div class=\"status\">No metric data yet. Run recommendation first.</div>";
    return;
  }

  metricsContainer.innerHTML = names
    .map((name) => {
      const m = agents[name];
      return [
        "<article class=\"info-card\">",
        "  <div class=\"info-title\">" + escapeHtml(name) + "</div>",
        "  <div class=\"kv\"><strong>Call Count</strong><span>" + escapeHtml(m.call_count) + "</span></div>",
        "  <div class=\"kv\"><strong>Success Rate</strong><span>" + escapeHtml(m.success_rate) + "</span></div>",
        "  <div class=\"kv\"><strong>Avg Latency (ms)</strong><span>" + escapeHtml(m.avg_latency_ms) + "</span></div>",
        "</article>",
      ].join("");
    })
    .join("");
}

async function loadExperiments() {
  experimentsContainer.innerHTML = "<div class=\"status loading\">Loading experiments...</div>";
  try {
    const response = await fetch("/api/v1/experiments");
    if (!response.ok) {
      throw new Error("Failed with status " + response.status);
    }
    const data = await response.json();
    renderExperiments(data);
  } catch (error) {
    experimentsContainer.innerHTML = "<div class=\"status error\">" + escapeHtml(error.message) + "</div>";
  }
}

async function loadMetrics() {
  metricsContainer.innerHTML = "<div class=\"status loading\">Loading metrics...</div>";
  try {
    const response = await fetch("/api/v1/metrics");
    if (!response.ok) {
      throw new Error("Failed with status " + response.status);
    }
    const data = await response.json();
    renderMetrics(data);
  } catch (error) {
    metricsContainer.innerHTML = "<div class=\"status error\">" + escapeHtml(error.message) + "</div>";
  }
}

async function submitOutcome(event) {
  event.preventDefault();
  const experimentId = document.getElementById("experimentId").value.trim();
  const groupName = document.getElementById("groupName").value.trim();
  const isSuccess = document.getElementById("isSuccess").value === "true";

  if (!experimentId || !groupName) {
    setOutcomeState("experiment_id and group are required.", "error");
    return;
  }

  setOutcomeState("Submitting outcome...", "loading");

  try {
    const url = "/api/v1/experiments/" + encodeURIComponent(experimentId) + "/outcome?group=" + encodeURIComponent(groupName) + "&success=" + isSuccess;
    const response = await fetch(url, { method: "POST" });
    if (!response.ok) {
      const text = await response.text();
      throw new Error("Failed: " + response.status + " " + text);
    }

    setOutcomeState("Outcome recorded.", "ok");
    await Promise.all([loadExperiments(), loadMetrics()]);
  } catch (error) {
    setOutcomeState(error.message, "error");
  }
}

reloadExperimentsBtn.addEventListener("click", loadExperiments);
reloadMetricsBtn.addEventListener("click", loadMetrics);
outcomeForm.addEventListener("submit", submitOutcome);

Promise.all([loadExperiments(), loadMetrics()]);
