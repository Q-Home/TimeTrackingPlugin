let badgesPerPage = 50;
let currentPage = 1;
let badgeData = [];
let filters = {};
let paginationInfo = null;

const currentHost = window.location.hostname;
const url = `http://${currentHost}:5000`;
const apiUrl = `${url}/api/v1`;

document.addEventListener("DOMContentLoaded", function () {
  const token = localStorage.getItem("access_token");

  if (!token) {
    window.location.href = "/index.html";
    return;
  }

  fetchBadges();
});

function authHeaders(includeJson = true) {
  const headers = {
    Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  };

  if (includeJson) {
    headers["Content-Type"] = "application/json";
  }

  return headers;
}

function notify(message, type = "info") {
  if (window.appShell?.showNotice) {
    window.appShell.showNotice(message, type);
    return;
  }

  alert(message);
}

function handleAuthError(response) {
  if (response.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    window.location.href = "/index.html";
    return true;
  }

  if (response.status === 403) {
    notify("Geen toegang.", "warning");
    return true;
  }

  return false;
}

function buildQueryParams(filterParams = {}) {
  const params = new URLSearchParams();

  params.set("page", currentPage);
  params.set("limit", badgesPerPage);

  if (filterParams.day) params.set("day", filterParams.day);
  if (filterParams.month) params.set("month", filterParams.month);
  if (filterParams.start_date) params.set("start_date", filterParams.start_date);
  if (filterParams.end_date) params.set("end_date", filterParams.end_date);
  if (filterParams.badge_code) params.set("badge_code", filterParams.badge_code);
  if (filterParams.user) params.set("user", filterParams.user);

  return params.toString();
}

async function fetchBadges(filterParams = filters) {
  try {
    showLoading();

    filters = { ...filterParams };

    const queryString = buildQueryParams(filters);
    const endpoint = `${apiUrl}/badges/?${queryString}`;

    const response = await fetch(endpoint, {
      method: "GET",
      headers: authHeaders(false),
    });

    if (handleAuthError(response)) return;

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      const textResponse = await response.text();
      throw new Error(`Server returned ${contentType || "unknown content-type"} instead of JSON: ${textResponse.substring(0, 200)}`);
    }

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || `HTTP ${response.status}`);
    }

    const data = result?.data || result;

    badgeData = data.badges || [];
    paginationInfo = data.pagination || null;
    filters = data.filters_applied || filters || {};

    renderBadges();
    updateFilterInfo();
    updateRecordCount();
    clearError();
  } catch (error) {
    console.error("Error loading badge data:", error);
    showError(`Error loading badge data: ${error.message}`);
  }
}

function getActionDisplay(action) {
  const rawAction = (action || "N/A").toString().trim();
  const normalizedAction = rawAction.toLowerCase();

  switch (normalizedAction) {
    case "scan":
      return {
        label: "Scan",
        className: "text-primary",
        icon: "ri-qr-scan-line",
      };

    case "scan_in":
    case "start":
      return {
        label: normalizedAction === "start" ? "START" : "Scan In",
        className: "text-success",
        icon: "ri-login-circle-line",
      };

    case "scan_out":
    case "stop":
      return {
        label: normalizedAction === "stop" ? "STOP" : "Scan Out",
        className: "text-danger",
        icon: "ri-logout-circle-r-line",
      };

    case "break":
      return {
        label: "BREAK",
        className: "text-warning",
        icon: "ri-pause-circle-line",
      };

    case "return":
      return {
        label: "RETURN",
        className: "text-info",
        icon: "ri-arrow-go-back-line",
      };

    default:
      return {
        label: rawAction || "N/A",
        className: "text-secondary",
        icon: "ri-question-line",
      };
  }
}

function renderBadges() {
  const badgeContainer = document.getElementById("badges");
  if (!badgeContainer) return;

  if (badgeData.length === 0) {
    badgeContainer.innerHTML = `
      <div class="alert alert-info text-center">
        <h5>No badge data found</h5>
        <p>No badge scans match your current filters.</p>
      </div>
    `;

    const paginationEl = document.getElementById("pagination");
    if (paginationEl) paginationEl.innerHTML = "";
    updateRecordCount();
    return;
  }

  let badgeTable = `
    <table class="table table-striped table-hover">
      <thead class="table-dark">
        <tr>
          <th><i class="ri-qr-code-line"></i> Badge Code</th>
          <th><i class="ri-calendar-line"></i> Timestamp</th>
          <th><i class="ri-user-line"></i> Username</th>
          <th><i class="ri-play-circle-line"></i> Action</th>
          <th><i class="ri-device-line"></i> Device</th>
        </tr>
      </thead>
      <tbody>
  `;

  badgeData.forEach((badge) => {
    const actionDisplay = getActionDisplay(badge.action);

    badgeTable += `
      <tr>
        <td>
          <strong>
            <i class="ri-qr-code-line text-primary"></i>
            ${escapeHtml(badge.badge_code || badge.badgecode || "N/A")}
          </strong>
        </td>
        <td>
          <i class="ri-calendar-line text-muted"></i>
          ${escapeHtml(formatDateTime(badge.timestamp))}
        </td>
        <td>
          <i class="ri-user-line text-info"></i>
          ${escapeHtml(badge.username || badge.user || "Unknown")}
        </td>
        <td>
          <span class="${actionDisplay.className}">
            <i class="${actionDisplay.icon}"></i>
            ${escapeHtml(actionDisplay.label)}
          </span>
        </td>
        <td>
          <i class="ri-device-line text-secondary"></i>
          ${escapeHtml(badge.device_id || badge.device || "N/A")}
        </td>
      </tr>
    `;
  });

  badgeTable += `
      </tbody>
    </table>
  `;

  badgeContainer.innerHTML = badgeTable;
  renderPagination();
}

function renderPagination() {
  const paginationContainer = document.getElementById("pagination");
  if (!paginationContainer) return;

  paginationContainer.innerHTML = "";

  const totalPages = paginationInfo?.total_pages || 1;
  if (totalPages <= 1) return;

  const prevButton = document.createElement("li");
  prevButton.classList.add("page-item");
  if (!paginationInfo?.has_prev) {
    prevButton.classList.add("disabled");
  }
  prevButton.innerHTML = `<a class="page-link" href="#"><i class="ri-arrow-left-line"></i> Previous</a>`;
  prevButton.addEventListener("click", function (e) {
    e.preventDefault();
    changePage(currentPage - 1);
  });
  paginationContainer.appendChild(prevButton);

  const maxVisiblePages = 5;
  let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
  let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

  if (endPage - startPage + 1 < maxVisiblePages) {
    startPage = Math.max(1, endPage - maxVisiblePages + 1);
  }

  for (let i = startPage; i <= endPage; i++) {
    const pageButton = document.createElement("li");
    pageButton.classList.add("page-item");
    if (i === currentPage) {
      pageButton.classList.add("active");
    }
    pageButton.innerHTML = `<a class="page-link" href="#">${i}</a>`;
    pageButton.addEventListener("click", function (e) {
      e.preventDefault();
      changePage(i);
    });
    paginationContainer.appendChild(pageButton);
  }

  const nextButton = document.createElement("li");
  nextButton.classList.add("page-item");
  if (!paginationInfo?.has_next) {
    nextButton.classList.add("disabled");
  }
  nextButton.innerHTML = `<a class="page-link" href="#">Next <i class="ri-arrow-right-line"></i></a>`;
  nextButton.addEventListener("click", function (e) {
    e.preventDefault();
    changePage(currentPage + 1);
  });
  paginationContainer.appendChild(nextButton);
}

function changePage(page) {
  const totalPages = paginationInfo?.total_pages || 1;
  if (page < 1 || page > totalPages) return;

  currentPage = page;
  fetchBadges(filters);
}

function changeRecordsPerPage() {
  const select = document.getElementById("records-per-page");
  if (!select) return;

  badgesPerPage = parseInt(select.value, 10) || 50;
  currentPage = 1;
  fetchBadges(filters);
}

function formatDateTime(dateTimeString) {
  if (!dateTimeString) return "N/A";

  try {
    return new Date(dateTimeString).toLocaleString("nl-BE", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch (error) {
    return dateTimeString;
  }
}

function updateRecordCount() {
  const recordCount = document.getElementById("record-count");
  if (!recordCount) return;

  const totalCount = paginationInfo?.total_count || badgeData.length;

  if (badgeData.length === 0) {
    recordCount.innerHTML = `<span class="text-muted">No records found</span>`;
    return;
  }

  const startIndex = ((paginationInfo?.current_page || currentPage) - 1) * (paginationInfo?.page_size || badgesPerPage) + 1;
  const endIndex = Math.min(startIndex + badgeData.length - 1, totalCount);

  recordCount.innerHTML = `
    <span class="text-primary">
      <i class="ri-file-list-line"></i>
      Showing ${startIndex}-${endIndex} of ${totalCount} badge scans
      ${Object.keys(filters).length > 0 ? "(filtered)" : ""}
    </span>
  `;
}

function updateFilterInfo() {
  const filterInfo = document.getElementById("filter-info");
  if (!filterInfo) return;

  let filterText = "Latest badge scans";
  const activeFilters = [];

  if (filters.day) activeFilters.push(`<strong>Day:</strong> ${filters.day}`);
  if (filters.month) activeFilters.push(`<strong>Month:</strong> ${filters.month}`);
  if (filters.start_date && filters.end_date) {
    activeFilters.push(`<strong>Range:</strong> ${escapeHtml(filters.start_date)} to ${escapeHtml(filters.end_date)}`);
  }
  if (filters.badge_code) activeFilters.push(`<strong>Badge:</strong> ${escapeHtml(filters.badge_code)}`);
  if (filters.user) activeFilters.push(`<strong>Person:</strong> ${escapeHtml(filters.user)}`);

  if (activeFilters.length > 0) {
    filterText = `<i class="ri-filter-line"></i> Filtered by: ${activeFilters.join(", ")}`;
    filterInfo.className = "alert alert-warning";
  } else {
    filterText = `<i class="ri-list-check-line"></i> ${filterText}`;
    filterInfo.className = "alert alert-info";
  }

  filterInfo.innerHTML = filterText;
}

function applyDayFilter() {
  const dayInput = document.getElementById("filter-day")?.value;
  if (!dayInput) {
    const newFilters = { ...filters };
    delete newFilters.day;
    currentPage = 1;
    fetchBadges(newFilters);
    return;
  }

  let dayNumber;
  if (dayInput.includes("-")) {
    const dateParts = dayInput.split("-");
    dayNumber = parseInt(dateParts[2], 10);
  } else {
    dayNumber = parseInt(dayInput, 10);
  }

  if (dayNumber >= 1 && dayNumber <= 31) {
    currentPage = 1;
    fetchBadges({ ...filters, day: dayNumber });
  } else {
    notify("Ongeldige dag. Gebruik een getal tussen 1 en 31.", "warning");
  }
}

function applyMonthFilter() {
  const monthInput = document.getElementById("filter-month")?.value;
  if (!monthInput) {
    const newFilters = { ...filters };
    delete newFilters.month;
    currentPage = 1;
    fetchBadges(newFilters);
    return;
  }

  let monthNumber;
  if (monthInput.includes("-")) {
    const dateParts = monthInput.split("-");
    monthNumber = parseInt(dateParts[1], 10);
  } else {
    monthNumber = parseInt(monthInput, 10);
  }

  if (monthNumber >= 1 && monthNumber <= 12) {
    currentPage = 1;
    fetchBadges({ ...filters, month: monthNumber });
  } else {
    notify("Ongeldige maand. Gebruik een getal tussen 1 en 12.", "warning");
  }
}

function applyBadgeFilter() {
  const badgeCode = document.getElementById("filter-badge")?.value?.trim() || "";
  currentPage = 1;

  if (badgeCode) {
    fetchBadges({ ...filters, badge_code: badgeCode });
  } else {
    const newFilters = { ...filters };
    delete newFilters.badge_code;
    fetchBadges(newFilters);
  }
}

function applyUserFilter() {
  const user = document.getElementById("filter-user")?.value?.trim() || "";
  currentPage = 1;

  if (user) {
    fetchBadges({ ...filters, user: user });
  } else {
    const newFilters = { ...filters };
    delete newFilters.user;
    fetchBadges(newFilters);
  }
}

function applyCombinedFilters() {
  const currentFilters = {};

  const dayInput = document.getElementById("filter-day")?.value;
  if (dayInput) {
    let dayNumber;
    if (dayInput.includes("-")) {
      const dateParts = dayInput.split("-");
      dayNumber = parseInt(dateParts[2], 10);
    } else {
      dayNumber = parseInt(dayInput, 10);
    }
    if (dayNumber >= 1 && dayNumber <= 31) {
      currentFilters.day = dayNumber;
    }
  }

  const monthInput = document.getElementById("filter-month")?.value;
  if (monthInput) {
    let monthNumber;
    if (monthInput.includes("-")) {
      const dateParts = monthInput.split("-");
      monthNumber = parseInt(dateParts[1], 10);
    } else {
      monthNumber = parseInt(monthInput, 10);
    }
    if (monthNumber >= 1 && monthNumber <= 12) {
      currentFilters.month = monthNumber;
    }
  }

  const badgeCode = document.getElementById("filter-badge")?.value?.trim();
  if (badgeCode) {
    currentFilters.badge_code = badgeCode;
  }

  const user = document.getElementById("filter-user")?.value?.trim();
  if (user) {
    currentFilters.user = user;
  }

  currentPage = 1;
  fetchBadges(currentFilters);
}

function refreshBadgeData() {
  fetchBadges(filters);
}

function showLoading() {
  const badgeContainer = document.getElementById("badges");
  if (!badgeContainer) return;

  badgeContainer.innerHTML = `
    <div class="text-center p-4">
      <div class="spinner-border text-primary" role="status">
        <span class="sr-only">Loading...</span>
      </div>
      <p class="mt-2">Loading badge data...</p>
    </div>
  `;
}

function showError(message) {
  const errorContainer = document.getElementById("badge-error");
  if (!errorContainer) return;

  errorContainer.innerHTML = `
    <div class="alert alert-danger alert-dismissible fade show" role="alert">
      <i class="ri-error-warning-line"></i> ${escapeHtml(message)}
      <button type="button" class="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>
  `;
}

function clearError() {
  const errorContainer = document.getElementById("badge-error");
  if (errorContainer) {
    errorContainer.innerHTML = "";
  }
}

function exportToCSV() {
  if (!badgeData || badgeData.length === 0) {
    notify("Geen data om te exporteren. Laad eerst badge data.", "warning");
    return;
  }

  try {
    const headers = ["Badge Code", "Timestamp", "Username", "Action", "Device"];
    const csvRows = [headers.join(",")];

    badgeData.forEach((badge) => {
      const actionDisplay = getActionDisplay(badge.action);

      const row = [
        `"${(badge.badge_code || badge.badgecode || "N/A").replace(/"/g, '""')}"`,
        `"${formatDateTime(badge.timestamp).replace(/"/g, '""')}"`,
        `"${(badge.username || badge.user || "Unknown").replace(/"/g, '""')}"`,
        `"${actionDisplay.label.replace(/"/g, '""')}"`,
        `"${(badge.device_id || badge.device || "N/A").replace(/"/g, '""')}"`,
      ];
      csvRows.push(row.join(","));
    });

    const csvContent = csvRows.join("\n");
    const now = new Date();
    const timestamp = now.toISOString().slice(0, 19).replace(/[:T]/g, "-");
    const filename = `badge-export-${timestamp}.csv`;

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const blobUrl = URL.createObjectURL(blob);

    link.setAttribute("href", blobUrl);
    link.setAttribute("download", filename);
    link.style.visibility = "hidden";

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showExportSuccess(`Exported ${badgeData.length} records to ${filename}`);
  } catch (error) {
    console.error("Error exporting CSV:", error);
    notify("Fout bij exporteren van CSV: " + error.message, "error");
  }
}

function exportToCSVWithFilters() {
  if (!badgeData || badgeData.length === 0) {
    notify("Geen data om te exporteren. Laad eerst badge data.", "warning");
    return;
  }

  try {
    const headers = ["Badge Code", "Timestamp", "Username", "Action", "Device"];
    const csvRows = [];

    if (Object.keys(filters).length > 0) {
      csvRows.push("# Badge Export with Filters Applied");
      Object.entries(filters).forEach(([key, value]) => {
        csvRows.push(`# ${key}: ${value}`);
      });
      csvRows.push(`# Export Date: ${new Date().toISOString()}`);
      csvRows.push("");
    } else {
      csvRows.push("# Badge Export");
      csvRows.push(`# Export Date: ${new Date().toISOString()}`);
      csvRows.push("");
    }

    csvRows.push(headers.join(","));

    badgeData.forEach((badge) => {
      const actionDisplay = getActionDisplay(badge.action);

      const row = [
        `"${(badge.badge_code || badge.badgecode || "N/A").replace(/"/g, '""')}"`,
        `"${formatDateTime(badge.timestamp).replace(/"/g, '""')}"`,
        `"${(badge.username || badge.user || "Unknown").replace(/"/g, '""')}"`,
        `"${actionDisplay.label.replace(/"/g, '""')}"`,
        `"${(badge.device_id || badge.device || "N/A").replace(/"/g, '""')}"`,
      ];
      csvRows.push(row.join(","));
    });

    const csvContent = csvRows.join("\n");
    const now = new Date();
    const timestamp = now.toISOString().slice(0, 19).replace(/[:T]/g, "-");
    const filterSuffix = Object.keys(filters).length > 0 ? "-filtered" : "";
    const filename = `badge-export${filterSuffix}-${timestamp}.csv`;

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const blobUrl = URL.createObjectURL(blob);

    link.setAttribute("href", blobUrl);
    link.setAttribute("download", filename);
    link.style.visibility = "hidden";

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    const filterInfo = Object.keys(filters).length > 0 ? " (filtered data)" : "";
    showExportSuccess(`Exported ${badgeData.length} records${filterInfo} to ${filename}`);
  } catch (error) {
    console.error("Error exporting CSV:", error);
    notify("Fout bij exporteren van CSV: " + error.message, "error");
  }
}

function showExportSuccess(message) {
  const successContainer =
    document.getElementById("export-success") ||
    document.getElementById("badge-error");

  if (!successContainer) return;

  successContainer.innerHTML = `
    <div class="alert alert-success alert-dismissible fade show" role="alert">
      <i class="ri-download-line"></i> ${escapeHtml(message)}
      <button type="button" class="close" data-dismiss="alert" aria-label="Close">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>
  `;

  setTimeout(() => {
    successContainer.innerHTML = "";
  }, 3000);
}

function startAutoRefresh(intervalSeconds = 30) {
  setInterval(() => {
    refreshBadgeData();
  }, intervalSeconds * 1000);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

window.changePage = changePage;
window.changeRecordsPerPage = changeRecordsPerPage;
window.applyDayFilter = applyDayFilter;
window.applyMonthFilter = applyMonthFilter;
window.applyBadgeFilter = applyBadgeFilter;
window.applyUserFilter = applyUserFilter;
window.applyCombinedFilters = applyCombinedFilters;
window.refreshBadgeData = refreshBadgeData;
window.exportToCSV = exportToCSV;
window.exportToCSVWithFilters = exportToCSVWithFilters;
