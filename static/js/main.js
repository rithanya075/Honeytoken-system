// =============================================================================
// main.js — Honeytoken Access Monitoring System — Frontend Logic
// =============================================================================
// Handles:
//   1. dashboardAutoRefresh()   — polls /api/stats every 30s
//   2. initCharts()             — Chart.js doughnut + line chart
//   3. initRiskBar()            — Chart.js bar chart for Risk Monitor
//   4. tableSearch()            — live client-side table filter
//   5. toggleUserAccordion()    — accordion rows on Users page
//   6. toggleAddForm()          — expand/collapse add honeytoken form
//   7. updateLastUpdated()      — live clock for "Last updated" text
// =============================================================================


// ── CHART DEFAULTS (dark theme) ──────────────────────────────────────────────
const CHART_DEFAULTS = {
  colors: {
    cyan:  "rgba(0, 212, 255, 1)",
    green: "rgba(0, 255, 136, 1)",
    red:   "rgba(255, 51, 85, 1)",
    amber: "rgba(255, 170, 0, 1)",
    cyanFade:  "rgba(0, 212, 255, 0.15)",
    greenFade: "rgba(0, 255, 136, 0.12)",
    redFade:   "rgba(255, 51, 85, 0.15)",
    amberFade: "rgba(255, 170, 0, 0.12)",
  }
};

// Shared Chart.js global overrides for dark theme
if (typeof Chart !== "undefined") {
  Chart.defaults.color          = "#64748b";
  Chart.defaults.borderColor    = "#1e2d40";
  Chart.defaults.backgroundColor = "transparent";
  Chart.defaults.font.family    = "'JetBrains Mono', monospace";
  Chart.defaults.font.size      = 11;
}


// ── 1. DASHBOARD AUTO-REFRESH ─────────────────────────────────────────────────
/**
 * dashboardAutoRefresh()
 * Polls /api/stats every 30 seconds and updates the 4 stat card numbers in the
 * DOM without a full page reload. Also updates the "Last updated" timestamp.
 */
function dashboardAutoRefresh() {
  setInterval(async () => {
    try {
      const res  = await fetch("/api/stats");
      if (!res.ok) return;
      const data = await res.json();

      // Update card values if elements exist on page
      const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined) {
          el.textContent = val;
          // Flash animation
          el.classList.add("stat-refreshed");
          setTimeout(() => el.classList.remove("stat-refreshed"), 600);
        }
      };

      setEl("stat-total-users",   data.total_users);
      setEl("stat-total-alerts",  data.total_alerts);
      setEl("stat-high-risk",     data.high_risk_count);
      setEl("stat-honeytokens",   data.total_honeytokens);

      // Update recent alerts list if present
      updateRecentAlertsList(data.recent_alerts || []);
      updateLastUpdated();

    } catch (err) {
      console.warn("[HAMS] Auto-refresh failed:", err);
    }
  }, 30000); // 30 seconds
}


/**
 * updateRecentAlertsList(alerts)
 * Rebuilds the recent alerts list panel from fresh API data.
 */
function updateRecentAlertsList(alerts) {
  const container = document.getElementById("recent-alerts-list");
  if (!container || alerts.length === 0) return;

  const severityClass = (sev) => {
    if (sev === "CRITICAL") return "alert-item--critical";
    if (sev === "HIGH")     return "alert-item--high";
    return "alert-item--medium";
  };
  const badgeClass = (sev) => {
    if (sev === "CRITICAL") return "badge-critical";
    if (sev === "HIGH")     return "badge-high";
    if (sev === "MEDIUM")   return "badge-medium";
    return "badge-low";
  };

  container.innerHTML = alerts.map(alert => `
    <div class="alert-item ${severityClass(alert.severity)}">
      <div class="alert-item-left">
        <span class="badge ${badgeClass(alert.severity)}">${alert.severity}</span>
        <span class="alert-user">${alert.username || "—"}</span>
      </div>
      <div class="alert-item-right">
        <span class="alert-desc">${(alert.description || "").substring(0, 50)}${(alert.description||"").length > 50 ? "…" : ""}</span>
        <span class="alert-time">${alert.created_at ? alert.created_at.substring(0,16) : "—"}</span>
      </div>
    </div>
  `).join("");
}


/**
 * updateLastUpdated()
 * Updates the "Last updated: HH:MM:SS" text with current time.
 */
function updateLastUpdated() {
  const el = document.getElementById("last-updated-time");
  if (!el) return;
  const now = new Date();
  el.textContent = now.toTimeString().substring(0, 8);
}


// ── 2. CHART.JS — DASHBOARD ──────────────────────────────────────────────────
/**
 * initCharts()
 * Initializes the doughnut (Risk Distribution) and line (Alert Trend) charts
 * on the dashboard. Expects RISK_DIST and TREND_LABELS/TREND_VALUES to be
 * set in the dashboard template's <script> block.
 */
function initCharts() {
  // -- Doughnut: Risk Distribution --
  const doughnutEl = document.getElementById("riskDoughnut");
  if (doughnutEl && typeof RISK_DIST !== "undefined") {
    new Chart(doughnutEl, {
      type: "doughnut",
      data: {
        labels: ["Low", "Medium", "High", "Critical"],
        datasets: [{
          data: [RISK_DIST.low, RISK_DIST.med, RISK_DIST.high, RISK_DIST.crit],
          backgroundColor: [
            "rgba(0, 255, 136, 0.7)",
            "rgba(255, 224, 102, 0.7)",
            "rgba(255, 170, 0, 0.7)",
            "rgba(255, 51, 85, 0.7)",
          ],
          borderColor: [
            "rgba(0, 255, 136, 1)",
            "rgba(255, 224, 102, 1)",
            "rgba(255, 170, 0, 1)",
            "rgba(255, 51, 85, 1)",
          ],
          borderWidth: 1.5,
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "68%",
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.label}: ${ctx.parsed} user${ctx.parsed !== 1 ? "s" : ""}`
            }
          }
        }
      }
    });
  }

  // -- Line: Alert Trend --
  const lineEl = document.getElementById("alertTrend");
  if (lineEl && typeof TREND_LABELS !== "undefined") {
    new Chart(lineEl, {
      type: "line",
      data: {
        labels: TREND_LABELS,
        datasets: [{
          label: "Alerts",
          data: TREND_VALUES,
          borderColor: CHART_DEFAULTS.colors.cyan,
          backgroundColor: "rgba(0, 212, 255, 0.08)",
          borderWidth: 2,
          pointBackgroundColor: CHART_DEFAULTS.colors.cyan,
          pointBorderColor: "#0d1421",
          pointRadius: 4,
          pointHoverRadius: 6,
          tension: 0.35,
          fill: true,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#0d1421",
            borderColor: "#1e2d40",
            borderWidth: 1,
            titleColor: "#00d4ff",
            bodyColor: "#e2e8f0",
          }
        },
        scales: {
          x: {
            grid: { color: "rgba(30,45,64,0.8)" },
            ticks: { color: "#64748b" }
          },
          y: {
            grid: { color: "rgba(30,45,64,0.8)" },
            ticks: { color: "#64748b", stepSize: 1 },
            beginAtZero: true,
          }
        }
      }
    });
  }
}


// ── 3. CHART.JS — RISK BAR ───────────────────────────────────────────────────
/**
 * initRiskBar(labels, values)
 * Renders the bar chart on the Risk Monitor page.
 * Bar colors graduate from green → amber → red based on score.
 */
function initRiskBar(labels, values) {
  const el = document.getElementById("riskBar");
  if (!el) return;

  // Color each bar based on its score value
  const barColors = values.map(v => {
    if (v >= 80) return "rgba(255, 51, 85, 0.8)";
    if (v >= 50) return "rgba(255, 170, 0, 0.8)";
    if (v >= 20) return "rgba(255, 224, 102, 0.7)";
    return "rgba(0, 255, 136, 0.7)";
  });
  const barBorders = values.map(v => {
    if (v >= 80) return "rgba(255, 51, 85, 1)";
    if (v >= 50) return "rgba(255, 170, 0, 1)";
    if (v >= 20) return "rgba(255, 224, 102, 1)";
    return "rgba(0, 255, 136, 1)";
  });

  new Chart(el, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Risk Score",
        data: values,
        backgroundColor: barColors,
        borderColor: barBorders,
        borderWidth: 1.5,
        borderRadius: 4,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0d1421",
          borderColor: "#1e2d40",
          borderWidth: 1,
          titleColor: "#00d4ff",
          bodyColor: "#e2e8f0",
        }
      },
      scales: {
        x: {
          grid: { color: "rgba(30,45,64,0.8)" },
          ticks: { color: "#64748b" }
        },
        y: {
          grid: { color: "rgba(30,45,64,0.8)" },
          ticks: { color: "#64748b" },
          min: 0,
          max: 100,
          beginAtZero: true,
        }
      }
    }
  });
}


// ── 4. TABLE SEARCH (live filter) ────────────────────────────────────────────
/**
 * tableSearch(inputId, tableId)
 * Filters visible table rows in real-time as the user types.
 * Only hides rows — does not remove them from the DOM.
 *
 * @param {string} inputId  - ID of the text input element
 * @param {string} tableId  - ID of the <table> element
 */
function tableSearch(inputId, tableId) {
  const input = document.getElementById(inputId);
  const table = document.getElementById(tableId);
  if (!input || !table) return;

  input.addEventListener("input", () => {
    const query = input.value.trim().toLowerCase();
    const rows  = table.querySelectorAll("tbody tr.data-row");

    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      const match = !query || text.includes(query);
      row.style.display = match ? "" : "none";

      // Also hide any accordion row following a hidden parent
      const nextRow = row.nextElementSibling;
      if (nextRow && nextRow.classList.contains("accordion-row")) {
        nextRow.style.display = "none"; // always collapse when filtering
      }
    });
  });
}


// ── 5. USER ROW ACCORDION ────────────────────────────────────────────────────
/**
 * toggleUserAccordion(row)
 * Clicking a user row on /users fetches that user's last 3 access logs
 * from /api/user/<id>/logs and injects them into an inline sub-row.
 * Clicking again collapses it.
 *
 * @param {HTMLElement} row - The clicked <tr> element
 */
async function toggleUserAccordion(row) {
  const userId     = row.dataset.userId;
  if (!userId) return;

  const accordionRow     = document.getElementById(`accordion-${userId}`);
  const accordionContent = document.getElementById(`accordion-content-${userId}`);
  const expandHint       = row.querySelector(".expand-hint");

  if (!accordionRow) return;

  const isOpen = accordionRow.style.display !== "none";

  // Close all other open accordions first
  document.querySelectorAll(".accordion-row").forEach(r => { r.style.display = "none"; });
  document.querySelectorAll(".expand-hint").forEach(h => { h.textContent = "▶ EXPAND"; });

  if (isOpen) {
    // Toggle off
    accordionRow.style.display = "none";
    return;
  }

  // Open this one
  accordionRow.style.display = "table-row";
  if (expandHint) expandHint.textContent = "▼ COLLAPSE";
  accordionContent.innerHTML = `<div class="accordion-loading">Loading recent access logs…</div>`;

  try {
    const res  = await fetch(`/api/user/${userId}/logs`);
    const logs = await res.json();

    if (!logs || logs.length === 0) {
      accordionContent.innerHTML = `<p class="muted" style="padding:8px 0;font-size:12px">No access logs found for this user.</p>`;
      return;
    }

    const rows = logs.map(log => `
      <tr>
        <td class="mono" style="padding:6px 12px">${log.log_id}</td>
        <td style="padding:6px 12px">${log.resource_name || "—"}</td>
        <td style="padding:6px 12px"><span class="action-tag action-tag--${(log.action_type||"").toLowerCase()}">${log.action_type || "—"}</span></td>
        <td class="mono muted" style="padding:6px 12px">${log.ip_address || "—"}</td>
        <td class="mono muted" style="padding:6px 12px">${(log.access_time || "—").substring(0, 19)}</td>
        <td style="padding:6px 12px">${log.is_suspicious ? '<span class="suspicious-flag">⚠ SUSPICIOUS</span>' : '<span class="muted">—</span>'}</td>
      </tr>
    `).join("");

    accordionContent.innerHTML = `
      <p style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#64748b;letter-spacing:.08em;margin-bottom:10px;">
        LAST 3 ACCESS LOGS
      </p>
      <table class="accordion-log-table">
        <thead>
          <tr>
            <th>LOG ID</th><th>RESOURCE</th><th>ACTION</th>
            <th>IP ADDRESS</th><th>TIMESTAMP</th><th>FLAG</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (err) {
    accordionContent.innerHTML = `<p class="muted" style="padding:8px 0;font-size:12px">Failed to load logs: ${err.message}</p>`;
  }
}


// ── 6. HONEYTOKEN ADD FORM TOGGLE ────────────────────────────────────────────
/**
 * toggleAddForm()
 * Shows or hides the inline "Add Honeytoken" form panel on /honeytokens.
 */
function toggleAddForm() {
  const panel = document.getElementById("addTokenForm");
  if (!panel) return;
  const isVisible = panel.style.display !== "none";
  panel.style.display = isVisible ? "none" : "block";
  if (!isVisible) {
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}


// ── 7. INIT ON DOM READY ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Auto-start table search on pages that have a search input
  // (Users page wires it manually via oninput, but this handles others)
  const genericSearch = document.getElementById("tableSearchInput");
  if (genericSearch) {
    tableSearch("tableSearchInput", "mainDataTable");
  }

  // Update "last updated" clock immediately on dashboard load
  updateLastUpdated();
});