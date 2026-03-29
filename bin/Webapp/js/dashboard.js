const dashboardHost = window.location.hostname;
const dashboardApiUrl = `http://${dashboardHost}:5000/api/v1`;

document.addEventListener("DOMContentLoaded", function () {
  const token = localStorage.getItem("access_token");
  const role = (localStorage.getItem("role") || "").toLowerCase();

  if (!token) {
    window.location.href = "/index.html";
    return;
  }

  if (role !== "admin") {
    const username = localStorage.getItem("username");
    window.location.href = username
      ? `/timesheet.html?username=${encodeURIComponent(username)}`
      : "/index.html";
    return;
  }

  document.getElementById("dashboardRefreshBtn")?.addEventListener("click", loadDashboardSummary);
  loadDashboardSummary();
});

async function loadDashboardSummary() {
  try {
    const response = await fetch(`${dashboardApiUrl}/dashboard/summary`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
      },
    });

    if (response.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("username");
      localStorage.removeItem("role");
      window.location.href = "/index.html";
      return;
    }

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || `HTTP ${response.status}`);
    }

    const data = result?.data || {};
    renderStats(data.stats || {});
    renderPresenceList(data.people_in_building || []);
    renderRecentActivity(data.recent_activity || []);
    renderLocations(data.locations || []);
  } catch (error) {
    window.appShell?.showNotice(`Dashboard kon niet geladen worden: ${error.message}`, "error");
  }
}

function renderStats(stats) {
  setText("stat-present-now", stats.present_now ?? 0);
  setText("stat-on-break", stats.on_break_now ?? 0);
  setText("stat-active-today", stats.active_today ?? 0);
  setText("stat-occupancy-rate", stats.occupancy_rate ?? 0);
  setText("stat-scans-today", stats.scans_today ?? 0);
  setText("stat-starts-today", stats.starts_today ?? 0);
  setText("stat-stops-today", stats.stops_today ?? 0);
  setText("stat-last-hour", stats.scans_last_hour ?? 0);
}

function renderPresenceList(people) {
  const container = document.getElementById("dashboard-presence-list");
  if (!container) return;

  if (people.length === 0) {
    container.innerHTML = `
      <div class="tt-empty-state">
        <i class="las la-door-closed"></i>
        <h5>Niemand aanwezig</h5>
        <p>Er is momenteel niemand in het gebouw volgens de badge-events.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = people.map((person) => `
    <article class="tt-dashboard-item">
      <div>
        <h5>${escapeHtml(person.display_name || person.username || "Onbekend")}</h5>
        <p>${escapeHtml(person.location || "Onbekende locatie")} - ${formatStatus(person.status)}</p>
      </div>
      <div class="text-right">
        <span class="badge badge-${person.status === "on_break" ? "warning" : "success"}">${formatStatus(person.status)}</span>
        <small>${formatDateTime(person.last_seen)}</small>
      </div>
    </article>
  `).join("");
}

function renderRecentActivity(events) {
  const container = document.getElementById("dashboard-recent-activity");
  if (!container) return;

  if (events.length === 0) {
    container.innerHTML = `
      <div class="tt-empty-state">
        <i class="las la-stream"></i>
        <h5>Nog geen recente activiteit</h5>
        <p>Zodra er nieuwe badge-events binnenkomen, zie je hier de laatste bewegingen.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = events.map((event) => `
    <article class="tt-dashboard-item">
      <div>
        <h5>${escapeHtml(event.display_name || event.username || "Onbekend")}</h5>
        <p>${escapeHtml(event.location || "Onbekende locatie")} - ${escapeHtml(event.action || "Onbekend")}</p>
      </div>
      <div class="text-right">
        <span class="badge badge-outline-primary">${escapeHtml(event.action || "-")}</span>
        <small>${formatDateTime(event.timestamp)}</small>
      </div>
    </article>
  `).join("");
}

function renderLocations(locations) {
  const container = document.getElementById("dashboard-locations");
  if (!container) return;

  if (locations.length === 0) {
    container.innerHTML = `
      <div class="col-12">
        <div class="tt-empty-state">
          <i class="las la-map-marker-alt"></i>
          <h5>Geen locatiegegevens</h5>
          <p>Er zijn momenteel geen aanwezigen om per locatie te tonen.</p>
        </div>
      </div>
    `;
    return;
  }

  container.innerHTML = locations.map((location) => `
    <div class="col-lg-4 col-md-6 mb-3">
      <div class="tt-panel">
        <span class="text-muted">Locatie</span>
        <h4 class="mb-1">${escapeHtml(location.location || "Onbekend")}</h4>
        <p class="mb-0">${location.count || 0} aanwezig</p>
      </div>
    </div>
  `).join("");
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function formatStatus(status) {
  if (status === "on_break") return "Pauze";
  if (status === "present") return "Aanwezig";
  return "Afwezig";
}

function formatDateTime(value) {
  if (!value) return "Onbekend";
  return new Date(value).toLocaleString("nl-BE", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
