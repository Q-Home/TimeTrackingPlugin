document.addEventListener("DOMContentLoaded", () => {
  const shell = window.appShell || {};
  const apiBase = `${window.location.origin}/api/v1`;
  const logsEndpoint = `${apiBase}/logs/?limit=1000`;

  const tableBody = document.querySelector(".js-Logs");
  const paginationContainer = document.getElementById("pagination");
  const searchInput = document.getElementById("exampleInputSearch");
  const logTypeFilter = document.getElementById("logTypeFilter");
  const exportBtn = document.getElementById("exportLogsBtn");
  const printBtn = document.getElementById("printLogsBtn");
  const refreshMqttBtn = document.getElementById("refreshMqttLogsBtn");
  const mqttStatus = document.getElementById("mqttDiagnosticsStatus");
  const mqttDetails = document.getElementById("mqttDiagnosticsDetails");
  const mqttSettings = document.getElementById("mqttDiagnosticsSettings");
  const mqttEvents = document.getElementById("mqttDiagnosticsEvents");

  const mqttEventLabels = new Map([
    ["starting", "Listener gestart"],
    ["connected", "Verbonden met MQTT-broker"],
    ["connection_error", "Broker niet bereikbaar. Controleer adres, poort en netwerk."],
    ["connection_refused", "Broker heeft de verbinding geweigerd. Controleer ook de aanmelding."],
    ["disconnected", "Verbinding met de broker verbroken"],
    ["subscribed", "Broker heeft het topicabonnement bevestigd"],
    ["subscription_refused", "Broker heeft het topicabonnement geweigerd"],
    ["badge_received", "Badge-event ontvangen"],
    ["badge_saved", "Badge-event opgeslagen door de API"],
    ["badge_api_error", "Badge-event niet opgeslagen: API-aanroep mislukt"],
    ["badge_unexpected_response", "Onverwacht antwoord van de API. Opslag niet bevestigd."],
    ["invalid_payload", "MQTT-bericht heeft een ongeldig formaat"],
    ["processing_error", "Fout bij het verwerken van het badge-event"],
    ["stats_received", "Statistiekvraag ontvangen"],
    ["stats_api_error", "API-aanroep voor statistiekvraag mislukt"],
    ["stopped", "Listener gestopt"],
  ]);

  const logsPerPage = 20;
  let currentPage = 1;
  let logsData = [];

  function notify(message, type = "info") {
    if (shell.showNotice) {
      shell.showNotice(message, type);
      return;
    }
    alert(message);
  }

  function authHeaders() {
    return {
      Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
    };
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatTimestamp(timestamp) {
    if (!timestamp) return "-";
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return timestamp;
    return date.toLocaleString("nl-BE");
  }

  async function fetchMqttDiagnostics() {
    refreshMqttBtn.disabled = true;
    mqttDetails.hidden = true;
    mqttStatus.textContent = "MQTT-diagnose laden…";
    try {
      const response = await fetch(`${apiBase}/logs/mqtt`, { headers: authHeaders(), cache: "no-store" });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const { data } = await response.json();
      if (!data?.available) {
        mqttStatus.textContent = "Nog geen MQTT-meldingen beschikbaar. Controleer of de bijgewerkte listener is gestart.";
        return;
      }

      const settings = [
        ["MQTT-broker", data.broker],
        ["Poort", data.port],
        ["MQTT-gebruikersnaam", data.username],
        ["MQTT-wachtwoord", data.password_configured ? "Ingesteld (verborgen)" : "Niet ingesteld"],
        ["Topic voor badge-events", data.badge_topic],
        ["Topic voor statistiekvragen", data.stats_topic],
        ["Topic voor terugkoppeling", data.publish_topic],
      ];
      mqttSettings.innerHTML = settings.map(([label, value]) =>
        `<dt class="col-sm-4">${label}</dt><dd class="col-sm-8 text-break">${escapeHtml(value || "Niet ingesteld")}</dd>`
      ).join("");

      mqttEvents.innerHTML = data.events.map(({ event, timestamp, code }) =>
        `<tr><td>${escapeHtml(formatTimestamp(timestamp))}</td>` +
        `<td>${escapeHtml(mqttEventLabels.get(event) || "Onbekende gebeurtenis")}</td>` +
        `<td>${escapeHtml(String(code ?? "–"))}</td></tr>`
      ).join("");
      mqttStatus.textContent = "Laatste gebeurtenissen sinds de listener werd gestart. Doe een testscan en klik daarna op Vernieuw MQTT-log.";
      mqttDetails.hidden = false;
    } catch (error) {
      mqttStatus.textContent = `De MQTT-diagnose kon niet worden geladen (${error.message}).`;
    } finally {
      refreshMqttBtn.disabled = false;
    }
  }

  function getFilteredLogs() {
    const searchTerm = (searchInput?.value || "").trim().toLowerCase();
    const selectedType = (logTypeFilter?.value || "all").toLowerCase();

    return logsData.filter((log) => {
      const type = (log.type || "").toLowerCase();
      const message = (log.message || "").toLowerCase();
      const timestamp = (log.timestamp || "").toLowerCase();

      const matchesSearch =
        !searchTerm ||
        type.includes(searchTerm) ||
        message.includes(searchTerm) ||
        timestamp.includes(searchTerm);

      const matchesType = selectedType === "all" || type === selectedType;

      return matchesSearch && matchesType;
    });
  }

  function renderEmptyState(message) {
    tableBody.innerHTML = `<tr><td colspan="3">${escapeHtml(message)}</td></tr>`;
    paginationContainer.innerHTML = "";
  }

  function renderLogs() {
    const filteredLogs = getFilteredLogs();
    tableBody.innerHTML = "";

    if (!filteredLogs.length) {
      renderEmptyState("Geen logs gevonden voor de huidige filter.");
      return;
    }

    const totalPages = Math.max(1, Math.ceil(filteredLogs.length / logsPerPage));
    if (currentPage > totalPages) {
      currentPage = totalPages;
    }

    const startIndex = (currentPage - 1) * logsPerPage;
    const visibleLogs = filteredLogs.slice(startIndex, startIndex + logsPerPage);

    visibleLogs.forEach((log) => {
      const row = `
        <tr>
          <td><span class="badge badge-light">${escapeHtml(log.type || "Info")}</span></td>
          <td>${escapeHtml(log.message || "")}</td>
          <td>${escapeHtml(formatTimestamp(log.timestamp))}</td>
        </tr>
      `;
      tableBody.insertAdjacentHTML("beforeend", row);
    });

    renderPagination(filteredLogs.length);
  }

  function renderPagination(totalItems) {
    paginationContainer.innerHTML = "";
    const totalPages = Math.ceil(totalItems / logsPerPage);
    if (totalPages <= 1) return;

    const addPageItem = (label, page, disabled = false, active = false) => {
      const item = document.createElement("li");
      item.className = `page-item${disabled ? " disabled" : ""}${active ? " active" : ""}`;
      item.innerHTML = `<a class="page-link" href="#">${label}</a>`;
      item.addEventListener("click", (event) => {
        event.preventDefault();
        if (disabled || page === currentPage) return;
        currentPage = page;
        renderLogs();
      });
      paginationContainer.appendChild(item);
    };

    addPageItem("Vorige", currentPage - 1, currentPage === 1);

    for (let page = 1; page <= totalPages; page += 1) {
      addPageItem(String(page), page, false, page === currentPage);
    }

    addPageItem("Volgende", currentPage + 1, currentPage === totalPages);
  }

  function debounce(func, delay) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => func(...args), delay);
    };
  }

  async function fetchLogs() {
    try {
      const response = await fetch(logsEndpoint, { headers: authHeaders() });

      if (response.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("username");
        localStorage.removeItem("role");
        window.location.href = "/index.html";
        return;
      }

      if (response.status === 403) {
        notify("Alleen admins kunnen de systeemlogs bekijken.", "warning");
        window.location.href = "/badgelist.html";
        return;
      }

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.error || payload.message || "Fout bij het ophalen van logs.");
      }

      logsData = payload?.data?.logs || [];
      currentPage = 1;
      renderLogs();
    } catch (error) {
      console.error("Error loading logs:", error);
      renderEmptyState("Fout bij het laden van logs. Probeer later opnieuw.");
      notify(error.message || "Fout bij het laden van logs.", "error");
    }
  }

  function exportLogsToCsv() {
    const filteredLogs = getFilteredLogs();
    if (!filteredLogs.length) {
      notify("Er zijn geen logs om te exporteren.", "warning");
      return;
    }

    const rows = [
      ["Type", "Bericht", "Tijdstip"],
      ...filteredLogs.map((log) => [
        log.type || "",
        log.message || "",
        formatTimestamp(log.timestamp),
      ]),
    ];

    const csv = rows
      .map((row) => row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(","))
      .join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "systeemlogs.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  searchInput?.addEventListener("input", debounce(() => {
    currentPage = 1;
    renderLogs();
  }, 200));

  logTypeFilter?.addEventListener("change", () => {
    currentPage = 1;
    renderLogs();
  });

  exportBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    exportLogsToCsv();
  });

  printBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    window.print();
  });

  if (refreshMqttBtn) {
    refreshMqttBtn.addEventListener("click", fetchMqttDiagnostics);
    fetchMqttDiagnostics();
  }
  fetchLogs();
});
