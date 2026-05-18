(function initAppUI(global) {
  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function setStatus(element, message, tone) {
    if (!element) {
      return;
    }
    element.textContent = message;
    element.className = "status";
    if (tone) {
      element.classList.add(tone);
    }
  }

  function setButtonBusy(button, isBusy, busyText, idleText) {
    if (!button) {
      return;
    }
    if (isBusy) {
      if (!button.dataset.idleText) {
        button.dataset.idleText = idleText || button.textContent;
      }
      button.textContent = busyText || "Loading...";
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      return;
    }
    button.disabled = false;
    button.removeAttribute("aria-busy");
    button.textContent = button.dataset.idleText || idleText || button.textContent;
  }

  function flattenFastApiDetail(detail) {
    if (Array.isArray(detail)) {
      return detail
        .map(function mapDetail(item) {
          if (!item || typeof item !== "object") {
            return String(item || "");
          }
          var where = Array.isArray(item.loc) ? item.loc.join(".") + ": " : "";
          return where + (item.msg || JSON.stringify(item));
        })
        .filter(Boolean)
        .join("; ");
    }
    if (detail && typeof detail === "object") {
      return JSON.stringify(detail);
    }
    return String(detail || "");
  }

  async function parseFetchError(response) {
    var payloadText = "";
    try {
      payloadText = await response.text();
    } catch (error) {
      payloadText = "";
    }

    if (!payloadText) {
      return "HTTP " + response.status + " " + response.statusText;
    }

    try {
      var parsed = JSON.parse(payloadText);
      if (parsed && parsed.detail) {
        return flattenFastApiDetail(parsed.detail);
      }
      if (parsed && parsed.message) {
        return String(parsed.message);
      }
      return JSON.stringify(parsed);
    } catch (error) {
      return payloadText;
    }
  }

  async function fetchJson(url, options) {
    var response = await fetch(url, options || {});
    if (!response.ok) {
      var errorMessage = await parseFetchError(response);
      throw new Error(errorMessage || "Request failed");
    }
    return response.json();
  }

  function normalizeCsv(value) {
    return String(value || "")
      .replaceAll("，", ",")
      .split(",")
      .map(function trimToken(token) {
        return token.trim();
      })
      .filter(Boolean);
  }

  function toInt(value, fallback) {
    var n = Number.parseInt(String(value), 10);
    if (Number.isNaN(n)) {
      return fallback;
    }
    return n;
  }

  function clampInt(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function formatLatency(latencyMs) {
    if (typeof latencyMs !== "number" || Number.isNaN(latencyMs)) {
      return "-";
    }
    return latencyMs.toFixed(1);
  }

  function asArray(value) {
    if (Array.isArray(value)) {
      return value;
    }
    if (value === null || value === undefined) {
      return [];
    }
    return [value];
  }

  global.AppUI = {
    asArray: asArray,
    clampInt: clampInt,
    escapeHtml: escapeHtml,
    fetchJson: fetchJson,
    formatLatency: formatLatency,
    normalizeCsv: normalizeCsv,
    parseFetchError: parseFetchError,
    setButtonBusy: setButtonBusy,
    setStatus: setStatus,
    toInt: toInt,
  };
})(window);