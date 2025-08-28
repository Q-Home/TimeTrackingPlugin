let badgesPerPage = 50;
let currentPage = 1;
let badgeData = [];
let filters = {};
const currentHost = window.location.hostname;
// Dynamische URL configuratie op basis van omgeving

const url = `http://${currentHost}:5000`;
console.debug("Detected API URL:", url);

async function fetchBadges(filterParams = {}) {
  try {
    showLoading();

    const requestBody = {
      filters: filterParams,
      limit: 50,
      sort: { timestamp: -1 },
    };

    console.debug("=== BADGE FETCH DEBUG ===");
    console.debug("API URL:", url);
    console.debug("Endpoint:", `${url}/api/v1/badges/search`);
    console.debug("Request body:", JSON.stringify(requestBody, null, 2));

    const response = await fetch(`${url}/api/v1/badges/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    console.debug("Response status:", response.status);
    console.debug("Response ok:", response.ok);
    console.debug("Response headers:", Object.fromEntries(response.headers.entries()));

    // Check if response is actually JSON
    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      const textResponse = await response.text();
      console.error("Expected JSON but got:", contentType);
      console.error("Response text:", textResponse);
      throw new Error(`Server returned ${contentType} instead of JSON: ${textResponse.substring(0, 200)}`);
    }

    const data = await response.json();
    console.debug("Response data:", data);

    if (!response.ok) {
      throw new Error(data.message || data.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    badgeData = data.badges || [];
    filters = data.filters_applied || {};

    console.debug("Processed badge data:", badgeData.length, "badges");

    // Reset to first page when new data is loaded
    currentPage = 1;
    renderBadges();
    updateFilterInfo();
    clearError();
  } catch (error) {
    console.error("=== FETCH ERROR ===");
    console.error("Error type:", error.constructor.name);
    console.error("Error message:", error.message);
    console.error("API URL:", url);
    console.error("Full error:", error);

    showError(`Error loading badge data: ${error.message}`);
  }
}

// Test functie om de API te testen
async function testAPI() {
  console.log("=== API TEST ===");

  // Test health endpoint
  try {
    const healthResponse = await fetch(`${url}/api/v1/health`);
    console.log("Health check:", healthResponse.status, await healthResponse.text());
  } catch (e) {
    console.error("Health check failed:", e);
  }

  // Test GET badges endpoint
  try {
    const getResponse = await fetch(`${url}/api/v1/badges/`);
    console.log("GET badges:", getResponse.status, await getResponse.text());
  } catch (e) {
    console.error("GET badges failed:", e);
  }
}

function renderBadges() {
  const badgeContainer = document.getElementById("badges");

  if (badgeData.length === 0) {
    badgeContainer.innerHTML = `
            <div class="alert alert-info text-center">
                <h5>No badge data found</h5>
                <p>No badge scans match your current filters.</p>
            </div>
        `;
    updateRecordCount();
    document.getElementById("pagination").innerHTML = "";
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

  // Calculate the indices for the current page
  const startIndex = (currentPage - 1) * badgesPerPage;
  const endIndex = Math.min(startIndex + badgesPerPage, badgeData.length);

  // Create table rows for the current page
  for (let i = startIndex; i < endIndex; i++) {
    const badge = badgeData[i];

    // Determine action styling
    const actionClass = badge.action === "START" ? "text-success" : badge.action === "STOP" ? "text-danger" : badge.action === "BREAK" ? "text-warning" : badge.action === "RETURN" ? "text-info" : "text-secondary";

    const actionIcon = badge.action === "START" ? "ri-play-circle-line" : badge.action === "STOP" ? "ri-stop-circle-line" : badge.action === "BREAK" ? "ri-pause-circle-line" : badge.action === "RETURN" ? "ri-skip-back-line" : "ri-question-line";

    badgeTable += `
            <tr>
                <td><strong><i class="ri-qr-code-line text-primary"></i> ${badge.badgecode || badge.badge_code || "N/A"}</strong></td>
                <td><i class="ri-calendar-line text-muted"></i> ${formatDateTime(badge.timestamp)}</td>
                <td><i class="ri-user-line text-info"></i> ${badge.username || badge.user || "Unknown"}</td>
                <td><span class="${actionClass}"><i class="${actionIcon}"></i> ${badge.action || "N/A"}</span></td>
                <td><i class="ri-device-line text-secondary"></i> ${badge.device_id || badge.device || "N/A"}</td>
            </tr>
        `;
  }

  badgeTable += `
            </tbody>
        </table>
    `;

  badgeContainer.innerHTML = badgeTable;

  // Update the pagination
  renderPagination();

  // Update record count
  updateRecordCount();
}

function renderPagination() {
  const paginationContainer = document.getElementById("pagination");
  paginationContainer.innerHTML = "";

  // Calculate total pages (max 50 records, dus max 1 pagina bij 50 per pagina)
  const totalPages = Math.ceil(badgeData.length / badgesPerPage);

  if (totalPages <= 1) {
    return; // Don't show pagination if only one page
  }

  // Add "Previous" button
  const prevButton = document.createElement("li");
  prevButton.classList.add("page-item");
  if (currentPage === 1) {
    prevButton.classList.add("disabled");
  }
  prevButton.innerHTML = `<a class="page-link" href="#" onclick="changePage(${currentPage - 1})"><i class="ri-arrow-left-line"></i> Previous</a>`;
  paginationContainer.appendChild(prevButton);

  // Calculate page range to show
  const maxVisiblePages = 5;
  let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
  let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

  if (endPage - startPage + 1 < maxVisiblePages) {
    startPage = Math.max(1, endPage - maxVisiblePages + 1);
  }

  // Add page number buttons
  for (let i = startPage; i <= endPage; i++) {
    const pageButton = document.createElement("li");
    pageButton.classList.add("page-item");
    if (i === currentPage) {
      pageButton.classList.add("active");
    }
    pageButton.innerHTML = `<a class="page-link" href="#" onclick="changePage(${i})">${i}</a>`;
    paginationContainer.appendChild(pageButton);
  }

  // Add "Next" button
  const nextButton = document.createElement("li");
  nextButton.classList.add("page-item");
  if (currentPage === totalPages) {
    nextButton.classList.add("disabled");
  }
  nextButton.innerHTML = `<a class="page-link" href="#" onclick="changePage(${currentPage + 1})">Next <i class="ri-arrow-right-line"></i></a>`;
  paginationContainer.appendChild(nextButton);
}

function changePage(page) {
  const totalPages = Math.ceil(badgeData.length / badgesPerPage);
  if (page >= 1 && page <= totalPages) {
    currentPage = page;
    renderBadges();
  }
}

function changeRecordsPerPage() {
  const select = document.getElementById("records-per-page");
  const newLimit = parseInt(select.value);

  // Update badgesPerPage voor display, maar haal altijd max 50 van server
  badgesPerPage = Math.min(newLimit, 50);
  currentPage = 1; // Reset to first page
  renderBadges();
}

function formatDateTime(dateTimeString) {
  if (!dateTimeString) return "N/A";

  try {
    const date = new Date(dateTimeString);
    return date.toLocaleString("nl-NL", {
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
  if (recordCount) {
    if (badgeData.length === 0) {
      recordCount.innerHTML = `<span class="text-muted">No records found</span>`;
    } else {
      const startIndex = (currentPage - 1) * badgesPerPage + 1;
      const endIndex = Math.min(currentPage * badgesPerPage, badgeData.length);
      recordCount.innerHTML = `
                <span class="text-primary">
                    <i class="ri-file-list-line"></i> 
                    Showing ${startIndex}-${endIndex} of ${badgeData.length} latest badge scans
                    ${Object.keys(filters).length > 0 ? "(filtered)" : ""}
                </span>
            `;
    }
  }
}

function updateFilterInfo() {
  const filterInfo = document.getElementById("filter-info");
  if (filterInfo) {
    let filterText = "Latest 50 badge scans";
    const activeFilters = [];

    if (filters.day) activeFilters.push(`<strong>Day:</strong> ${filters.day}`);
    if (filters.month) activeFilters.push(`<strong>Month:</strong> ${filters.month}`);
    if (filters.start_date && filters.end_date) {
      activeFilters.push(`<strong>Range:</strong> ${filters.start_date} to ${filters.end_date}`);
    }
    if (filters.badge_code) activeFilters.push(`<strong>Badge:</strong> ${filters.badge_code}`);
    if (filters.user) activeFilters.push(`<strong>Person:</strong> ${filters.user}`);

    if (activeFilters.length > 0) {
      filterText = `<i class="ri-filter-line"></i> Latest 50 filtered by: ${activeFilters.join(", ")}`;
      filterInfo.className = "alert alert-warning";
    } else {
      filterText = `<i class="ri-list-check-line"></i> ${filterText}`;
      filterInfo.className = "alert alert-info";
    }

    filterInfo.innerHTML = filterText;
  }
}

// Filter functions - aangepast om laatste 50 met filter te tonen
function applyDayFilter() {
  const day = document.getElementById("filter-day")?.value;
  if (day) {
    fetchBadges({ day: day });
  }
}

function applyMonthFilter() {
  const month = document.getElementById("filter-month")?.value;
  if (month) {
    fetchBadges({ month: month });
  }
}

function applyBadgeFilter() {
  const badgeCode = document.getElementById("filter-badge")?.value;
  if (badgeCode) {
    fetchBadges({ badge_code: badgeCode });
  }
}

function applyUserFilter() {
  const user = document.getElementById("filter-user")?.value;
  if (user) {
    fetchBadges({ user: user });
  }
}

function clearBadgeFilters() {
  // Clear all filter inputs
  const inputs = ["filter-day", "filter-month", "filter-badge", "filter-user"];
  inputs.forEach((id) => {
    const element = document.getElementById(id);
    if (element) element.value = "";
  });

  // Fetch latest 50 badges zonder filters
  fetchBadges();
}

function refreshBadgeData() {
  // Re-apply current filters for latest 50
  const currentFilters = {};
  const day = document.getElementById("filter-day")?.value;
  const month = document.getElementById("filter-month")?.value;
  const badgeCode = document.getElementById("filter-badge")?.value;
  const user = document.getElementById("filter-user")?.value;

  if (day) currentFilters.day = day;
  if (month) currentFilters.month = month;
  if (badgeCode) currentFilters.badge_code = badgeCode;
  if (user) currentFilters.user = user;

  fetchBadges(currentFilters);
}

function showLoading() {
  const badgeContainer = document.getElementById("badges");
  badgeContainer.innerHTML = `
        <div class="text-center p-4">
            <div class="spinner-border text-primary" role="status">
                <span class="sr-only">Loading...</span>
            </div>
            <p class="mt-2">Loading latest badge data...</p>
        </div>
    `;
}

function showError(message) {
  const errorContainer = document.getElementById("badge-error");
  if (errorContainer) {
    errorContainer.innerHTML = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="ri-error-warning-line"></i> ${message}
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span>
            </button>
        </div>
    `;
  }
}

function clearError() {
  const errorContainer = document.getElementById("badge-error");
  if (errorContainer) {
    errorContainer.innerHTML = "";
  }
}

// Auto-refresh function (optional) - refresh laatste 50
function startAutoRefresh(intervalSeconds = 30) {
  setInterval(() => {
    refreshBadgeData();
  }, intervalSeconds * 1000);
}

// Initialize on page load - laad laatste 50
document.addEventListener("DOMContentLoaded", function () {
  console.debug("Page loaded, starting badge fetch...");
  console.debug("Environment detected - API URL:", url);

  fetchBadges(); // Laadt automatisch de laatste 50
  // Optional: Start auto-refresh every 30 seconds
  // startAutoRefresh(30);
});

// Voeg deze functie toe na je andere functies
function exportToCSV() {
  if (!badgeData || badgeData.length === 0) {
    alert("Geen data om te exporteren. Laad eerst badge data.");
    return;
  }

  try {
    // CSV headers
    const headers = ["Badge Code", "Timestamp", "Username", "Action", "Device"];

    // Convert badge data to CSV format
    const csvRows = [];

    // Add headers
    csvRows.push(headers.join(","));

    // Add data rows
    badgeData.forEach((badge) => {
      const row = [`"${badge.badgecode || badge.badge_code || "N/A"}"`, `"${formatDateTime(badge.timestamp)}"`, `"${badge.username || badge.user || "Unknown"}"`, `"${badge.action || "N/A"}"`, `"${badge.device_id || badge.device || "N/A"}"`];
      csvRows.push(row.join(","));
    });

    // Create CSV content
    const csvContent = csvRows.join("\n");

    // Create filename with current date/time
    const now = new Date();
    const timestamp = now.toISOString().slice(0, 19).replace(/[:T]/g, "-");
    const filename = `badge-export-${timestamp}.csv`;

    // Create and trigger download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");

    if (link.download !== undefined) {
      // Feature detection for download attribute
      const url = URL.createObjectURL(blob);
      link.setAttribute("href", url);
      link.setAttribute("download", filename);
      link.style.visibility = "hidden";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      console.log(`CSV exported: ${filename} with ${badgeData.length} records`);

      // Show success message
      showExportSuccess(`Exported ${badgeData.length} records to ${filename}`);
    } else {
      // Fallback for older browsers
      alert("CSV export not supported in this browser");
    }
  } catch (error) {
    console.error("Error exporting CSV:", error);
    alert("Error exporting CSV: " + error.message);
  }
}

// Helper function to show export success message
function showExportSuccess(message) {
  const successContainer = document.getElementById("export-success") || document.getElementById("badge-error");
  if (successContainer) {
    successContainer.innerHTML = `
      <div class="alert alert-success alert-dismissible fade show" role="alert">
        <i class="ri-download-line"></i> ${message}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close">
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
    `;

    // Auto-hide after 3 seconds
    setTimeout(() => {
      if (successContainer) {
        successContainer.innerHTML = "";
      }
    }, 3000);
  }
}

// Enhanced export function with filter information
function exportToCSVWithFilters() {
  if (!badgeData || badgeData.length === 0) {
    alert("Geen data om te exporteren. Laad eerst badge data.");
    return;
  }

  try {
    // CSV headers
    const headers = ["Badge Code", "Timestamp", "Username", "Action", "Device"];

    // Convert badge data to CSV format
    const csvRows = [];

    // Add filter info as comments if filters are applied
    if (Object.keys(filters).length > 0) {
      csvRows.push("# Badge Export with Filters Applied");
      Object.entries(filters).forEach(([key, value]) => {
        csvRows.push(`# ${key}: ${value}`);
      });
      csvRows.push("# Export Date: " + new Date().toISOString());
      csvRows.push(""); // Empty line
    }

    // Add headers
    csvRows.push(headers.join(","));

    // Add data rows
    badgeData.forEach((badge) => {
      const row = [`"${badge.badgecode || badge.badge_code || "N/A"}"`, `"${formatDateTime(badge.timestamp)}"`, `"${badge.username || badge.user || "Unknown"}"`, `"${badge.action || "N/A"}"`, `"${badge.device_id || badge.device || "N/A"}"`];
      csvRows.push(row.join(","));
    });

    // Create CSV content
    const csvContent = csvRows.join("\n");

    // Create filename with current date/time and filter info
    const now = new Date();
    const timestamp = now.toISOString().slice(0, 19).replace(/[:T]/g, "-");
    const filterSuffix = Object.keys(filters).length > 0 ? "-filtered" : "";
    const filename = `badge-export${filterSuffix}-${timestamp}.csv`;

    // Create and trigger download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");

    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute("href", url);
      link.setAttribute("download", filename);
      link.style.visibility = "hidden";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      console.log(`CSV exported: ${filename} with ${badgeData.length} records`);

      // Show success message
      const filterInfo = Object.keys(filters).length > 0 ? " (filtered data)" : "";
      showExportSuccess(`Exported ${badgeData.length} records${filterInfo} to ${filename}`);
    } else {
      alert("CSV export not supported in this browser");
    }
  } catch (error) {
    console.error("Error exporting CSV:", error);
    alert("Error exporting CSV: " + error.message);
  }
}
