document.addEventListener("DOMContentLoaded", () => {
  const shell = window.appShell || {};
  const hostname = window.location.hostname;
  const apiBase = `http://${hostname}:5000/api/v1`;
  const logsEndpoint = `${apiBase}/logs/?limit=1000`;

  const tableBody = document.querySelector(".js-Logs");
  const paginationContainer = document.getElementById("pagination");
  const searchInput = document.getElementById("exampleInputSearch");
  const logTypeFilter = document.getElementById("logTypeFilter");
  const exportBtn = document.getElementById("exportLogsBtn");
  const printBtn = document.getElementById("printLogsBtn");

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

  fetchLogs();
});
