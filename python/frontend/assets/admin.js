const experimentsContainer = document.getElementById("experimentsContainer");
const metricsContainer = document.getElementById("metricsContainer");
const experimentsState = document.getElementById("experimentsState");
const metricsState = document.getElementById("metricsState");

const reloadExperimentsBtn = document.getElementById("reloadExperiments");
const reloadMetricsBtn = document.getElementById("reloadMetrics");

const outcomeForm = document.getElementById("outcomeForm");
const outcomeState = document.getElementById("outcomeState");
const outcomeSubmitBtn = document.getElementById("outcomeSubmitBtn");

const experimentIdInput = document.getElementById("experimentId");
const groupNameInput = document.getElementById("groupName");
const isSuccessInput = document.getElementById("isSuccess");

let loadingExperiments = false;
let loadingMetrics = false;

function formatRate(successes, failures) {
  const total = successes + failures;
  if (!total) {
    return "0.0%";
  }
  return ((successes / total) * 100).toFixed(1) + "%";
}

function safeString(value) {
  if (value === null || value === undefined) {
    return "-";
  }
  return String(value);
}

function renderExperiments(experiments) {
  const keys = Object.keys(experiments || {});
  if (keys.length === 0) {
    experimentsContainer.innerHTML = "<div class=\"empty-state\">No experiment data found. Check backend initialization.</div>";
    return;
  }

  experimentsContainer.innerHTML = keys
    .map((expId) => {
      const exp = experiments[expId] || {};
      const groups = Array.isArray(exp.groups) ? exp.groups : [];

      const groupRows = groups
        .map((group) => {
          const successes = Number(group.successes || 0);
          const failures = Number(group.failures || 0);
          const rate = formatRate(successes, failures);
          return [
            "<tr>",
            "<td>" + AppUI.escapeHtml(safeString(group.name)) + "</td>",
            "<td>" + AppUI.escapeHtml(safeString(group.weight)) + "</td>",
            "<td>" + AppUI.escapeHtml(String(successes)) + " / " + AppUI.escapeHtml(String(failures)) + "</td>",
            "<td>" + AppUI.escapeHtml(rate) + "</td>",
            "<td class=\"mono\">" + AppUI.escapeHtml(JSON.stringify(group.config || {})) + "</td>",
            "</tr>",
          ].join("");
        })
        .join("");

      const stats = exp.stats && typeof exp.stats === "object" ? exp.stats : {};
      const statGroups = Object.keys(stats);
      const statsHtml = statGroups.length === 0
        ? "<div class=\"subtle-text\">No business metric records yet.</div>"
        : "<div class=\"subtle-text\">Stats groups: " + AppUI.escapeHtml(statGroups.join(", ")) + "</div>";

      return [
        "<article class=\"info-card experiment-card\">",
        "<div class=\"info-title-row\">",
        "  <div class=\"info-title\">" + AppUI.escapeHtml(expId) + "</div>",
        "  <span class=\"tag " + (exp.enabled ? "tag-ok" : "tag-muted") + "\">" + (exp.enabled ? "enabled" : "disabled") + "</span>",
        "</div>",
        "<div class=\"subtle-text\">" + AppUI.escapeHtml(exp.name || "Unnamed experiment") + "</div>",
        "<div class=\"table-wrap\">",
        "<table class=\"group-table\">",
        "<thead><tr><th>Group</th><th>Weight</th><th>Success/Fail</th><th>Success Rate</th><th>Config</th></tr></thead>",
        "<tbody>" + groupRows + "</tbody>",
        "</table>",
        "</div>",
        statsHtml,
        "</article>",
      ].join("");
    })
    .join("");
}

function renderMetrics(metrics) {
  const safeMetrics = metrics || {};
  const agents = safeMetrics.agents || {};
  const names = Object.keys(agents);

  if (names.length === 0) {
    metricsContainer.innerHTML = [
      "<div class=\"empty-state\">",
      "No metric data yet. Run recommendation requests from the user page, then refresh.",
      "</div>",
    ].join("");
    return;
  }

  const agentCards = names
    .map((name) => {
      const metric = agents[name] || {};
      const errors = Array.isArray(metric.recent_errors) ? metric.recent_errors : [];
      const errorHtml = errors.length === 0
        ? "<div class=\"subtle-text\">No recent errors.</div>"
        : "<div class=\"subtle-text\">Recent errors: " + AppUI.escapeHtml(errors.join(" | ")) + "</div>";

      return [
        "<article class=\"info-card\">",
        "<div class=\"info-title\">" + AppUI.escapeHtml(name) + "</div>",
        "<div class=\"kv\"><strong>Call Count</strong><span>" + AppUI.escapeHtml(safeString(metric.call_count)) + "</span></div>",
        "<div class=\"kv\"><strong>Success Rate</strong><span>" + AppUI.escapeHtml(safeString(metric.success_rate)) + "</span></div>",
        "<div class=\"kv\"><strong>Avg Latency (ms)</strong><span>" + AppUI.escapeHtml(safeString(metric.avg_latency_ms)) + "</span></div>",
        errorHtml,
        "</article>",
      ].join("");
    })
    .join("");

  const business = safeMetrics.business || {};
  const businessNames = Object.keys(business);
  const businessCard = businessNames.length === 0
    ? "<article class=\"info-card\"><div class=\"info-title\">Business Metrics</div><div class=\"subtle-text\">No business events collected yet.</div></article>"
    : [
        "<article class=\"info-card\">",
        "<div class=\"info-title\">Business Metrics</div>",
        businessNames
          .map((metricName) => {
            const count = business[metricName] && business[metricName].count;
            return "<div class=\"kv\"><strong>" + AppUI.escapeHtml(metricName) + "</strong><span>" + AppUI.escapeHtml(safeString(count)) + "</span></div>";
          })
          .join(""),
        "</article>",
      ].join("");

  metricsContainer.innerHTML = agentCards + businessCard;
}

async function loadExperiments() {
  if (loadingExperiments) {
    return;
  }
  loadingExperiments = true;
  AppUI.setButtonBusy(reloadExperimentsBtn, true, "Refreshing...", "Refresh");
  AppUI.setStatus(experimentsState, "Loading experiments...", "loading");

  try {
    const data = await AppUI.fetchJson("/api/v1/experiments");
    renderExperiments(data);
    AppUI.setStatus(experimentsState, "Experiments loaded.", "ok");
  } catch (error) {
    experimentsContainer.innerHTML = "<div class=\"empty-state\">Failed to load experiments: " + AppUI.escapeHtml(error.message || "Unknown error") + "</div>";
    AppUI.setStatus(experimentsState, "Experiment refresh failed.", "error");
    throw error;
  } finally {
    loadingExperiments = false;
    AppUI.setButtonBusy(reloadExperimentsBtn, false, "Refreshing...", "Refresh");
  }
}

async function loadMetrics() {
  if (loadingMetrics) {
    return;
  }
  loadingMetrics = true;
  AppUI.setButtonBusy(reloadMetricsBtn, true, "Refreshing...", "Refresh");
  AppUI.setStatus(metricsState, "Loading metrics...", "loading");

  try {
    const data = await AppUI.fetchJson("/api/v1/metrics");
    renderMetrics(data);
    AppUI.setStatus(metricsState, "Metrics loaded.", "ok");
  } catch (error) {
    metricsContainer.innerHTML = "<div class=\"empty-state\">Failed to load metrics: " + AppUI.escapeHtml(error.message || "Unknown error") + "</div>";
    AppUI.setStatus(metricsState, "Metrics refresh failed.", "error");
    throw error;
  } finally {
    loadingMetrics = false;
    AppUI.setButtonBusy(reloadMetricsBtn, false, "Refreshing...", "Refresh");
  }
}

async function refreshDashboard() {
  const results = await Promise.allSettled([loadExperiments(), loadMetrics()]);
  const failedCount = results.filter((result) => result.status === "rejected").length;
  if (failedCount > 0) {
    AppUI.setStatus(outcomeState, "Dashboard refreshed with partial failures.", "error");
  }
}

async function submitOutcome(event) {
  event.preventDefault();

  const experimentId = experimentIdInput.value.trim();
  const groupName = groupNameInput.value.trim();
  const isSuccess = isSuccessInput.value === "true";

  if (!experimentId || !groupName) {
    AppUI.setStatus(outcomeState, "Experiment ID and Group Name are required.", "error");
    return;
  }

  AppUI.setButtonBusy(outcomeSubmitBtn, true, "Submitting...", "Submit Outcome");
  AppUI.setStatus(outcomeState, "Submitting outcome...", "loading");

  try {
    const url = "/api/v1/experiments/" + encodeURIComponent(experimentId) + "/outcome?group=" + encodeURIComponent(groupName) + "&success=" + isSuccess;
    await AppUI.fetchJson(url, { method: "POST" });

    AppUI.setStatus(outcomeState, "Outcome recorded. Refreshing experiments and metrics...", "ok");

    const refreshResults = await Promise.allSettled([loadExperiments(), loadMetrics()]);
    const refreshFailed = refreshResults.some((result) => result.status === "rejected");

    if (refreshFailed) {
      AppUI.setStatus(outcomeState, "Outcome recorded, but one panel failed to refresh.", "error");
    } else {
      AppUI.setStatus(outcomeState, "Outcome recorded and dashboard refreshed.", "ok");
    }
  } catch (error) {
    AppUI.setStatus(outcomeState, "Submit failed: " + (error.message || "Unknown error"), "error");
  } finally {
    AppUI.setButtonBusy(outcomeSubmitBtn, false, "Submitting...", "Submit Outcome");
  }
}

reloadExperimentsBtn.addEventListener("click", loadExperiments);
reloadMetricsBtn.addEventListener("click", loadMetrics);
outcomeForm.addEventListener("submit", submitOutcome);

refreshDashboard();
