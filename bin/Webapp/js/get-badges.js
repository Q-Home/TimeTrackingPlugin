let badgesPerPage = 50;
let currentPage = 1;
let badgeData = [];
let filters = {};

const url = "http://172.28.0.15:5000";

async function fetchBadges(filterParams = {}) {
  try {
    showLoading();

    // Verstuur filters via POST request body in plaats van URL parameters
    const requestBody = {
      filters: filterParams,
      limit: 50, // Altijd de laatste 50 records
      sort: { timestamp: -1 }, // Sorteer op timestamp, nieuwste eerst
    };

    const response = await fetch(`${url}/api/v1/badges/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || "Failed to fetch badge data");
    }

    badgeData = data.badges || [];
    filters = data.filters_applied || {};

    // Reset to first page when new data is loaded
    currentPage = 1;
    renderBadges();
    updateFilterInfo();
    clearError();
  } catch (error) {
    console.error("Error fetching badge data:", error);
    showError(`Error loading badge data: ${error.message}`);
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
                    <th><i class="ri-user-line"></i> User</th>
                    <th><i class="ri-time-line"></i> Scan Time</th>
                    <th><i class="ri-play-circle-line"></i> Action</th>
                    <th><i class="ri-calendar-line"></i> Timestamp</th>
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
    const actionClass = badge.action === "START" ? "text-success" : badge.action === "STOP" ? "text-danger" : "text-info";
    const actionIcon = badge.action === "START" ? "ri-play-circle-line" : badge.action === "STOP" ? "ri-stop-circle-line" : "ri-question-line";

    badgeTable += `
            <tr>
                <td><strong><i class="ri-qr-code-line text-primary"></i> ${badge.badgecode || badge.badge_code || "N/A"}</strong></td>
                <td><i class="ri-user-line text-info"></i> ${badge.user || badge.username || "Unknown"}</td>
                <td><i class="ri-time-line text-secondary"></i> ${formatDateTime(badge.scan_time || badge.timestamp)}</td>
                <td><span class="${actionClass}"><i class="${actionIcon}"></i> ${badge.action || "N/A"}</span></td>
                <td><i class="ri-calendar-line text-muted"></i> ${formatDateTime(badge.timestamp)}</td>
            </tr>
        `;
  }

  badgeTable += `
            </tbody>
        </table>
    `;

  badgeContainer.innerHTML = badgeTable;

  // Update the pagination - aangepast voor max 50 records
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
  errorContainer.innerHTML = `
        <div class="alert alert-danger alert-dismissible fade show" role="alert">
            <i class="ri-error-warning-line"></i> ${message}
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span>
            </button>
        </div>
    `;
}

function clearError() {
  const errorContainer = document.getElementById("badge-error");
  errorContainer.innerHTML = "";
}

// Auto-refresh function (optional) - refresh laatste 50
function startAutoRefresh(intervalSeconds = 30) {
  setInterval(() => {
    refreshBadgeData();
  }, intervalSeconds * 1000);
}

// Initialize on page load - laad laatste 50
document.addEventListener("DOMContentLoaded", function () {
  fetchBadges(); // Laadt automatisch de laatste 50
  // Optional: Start auto-refresh every 30 seconds
  // startAutoRefresh(30);
});
