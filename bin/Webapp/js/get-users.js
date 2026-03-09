const hostname = window.location.hostname;
const url = `http://${hostname}:5000`;
const token = localStorage.getItem("access_token");
const role = (localStorage.getItem("role") || "").toLowerCase();

let allUsers = [];
let filteredUsers = [];
let currentPage = 1;
let usersPerPage = 10;

document.addEventListener("DOMContentLoaded", function () {
  if (!token) {
    window.location.href = "/index.html";
    return;
  }

  initializeEventListeners();
  loadUsers();
});

function authHeaders() {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${localStorage.getItem("access_token")}`,
  };
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
    alert("Geen toegang.");
    return true;
  }

  return false;
}

function initializeEventListeners() {
  const searchInput = document.getElementById("userSearch");
  if (searchInput) {
    searchInput.addEventListener("input", debounce(filterUsers, 250));
  }

  const sortSelect = document.getElementById("sortBy");
  if (sortSelect) {
    sortSelect.addEventListener("change", sortUsers);
  }
}

async function loadUsers() {
  try {
    showLoading();

    const response = await fetch(`${url}/api/v1/users/`, {
      method: "GET",
      headers: authHeaders(),
    });

    if (handleAuthError(response)) return;

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || `HTTP ${response.status}`);
    }

    const users = result?.data?.users || result?.users || [];
    allUsers = users.map(normalizeUser);
    filteredUsers = [...allUsers];

    sortUsers(false);
    updateStats();
    hideLoading();

    if (filteredUsers.length === 0) {
      showNoUsers();
      return;
    }

    renderUsers();
  } catch (error) {
    console.error("Error loading users:", error);
    showError(`Error loading users: ${error.message}`);
  }
}

function normalizeUser(user) {
  const firstName = user.first_name || "";
  const lastName = user.last_name || "";
  const username = user.username || "";
  const badgeCodes = Array.isArray(user.badge_codes) ? user.badge_codes : [];

  return {
    username: username,
    user_id: user.user_id || "",
    first_name: firstName,
    last_name: lastName,
    company_name: user.company_name || "",
    email: user.email || "",
    user_role: user.user_role || user.role || "user",
    blocked: Boolean(user.blocked),
    badge_codes: badgeCodes,
    primary_badge: badgeCodes[0] || "N/A",
    total_scans: Number(user.total_scans || 0),
    last_activity: user.last_activity || null,
    first_activity: user.first_activity || null,
    display_name: `${firstName} ${lastName}`.trim() || username || "Unknown",
    activity_status: getActivityStatus(user.last_activity),
  };
}

function renderUsers() {
  const tbody =
    document.getElementById("users-tbody") ||
    document.querySelector(".js-users");

  if (!tbody) {
    console.error("Geen tbody gevonden (#users-tbody of .js-users).");
    return;
  }

  tbody.innerHTML = "";

  if (filteredUsers.length === 0) {
    showNoUsers();
    return;
  }

  const startIndex = (currentPage - 1) * usersPerPage;
  const endIndex = Math.min(startIndex + usersPerPage, filteredUsers.length);
  const pageUsers = filteredUsers.slice(startIndex, endIndex);

  pageUsers.forEach((user) => {
    const row = document.createElement("tr");
    row.setAttribute("data-username", user.username);

    const statusClass =
      user.activity_status === "Today"
        ? "success"
        : user.activity_status === "Yesterday"
        ? "warning"
        : "secondary";

    row.innerHTML = `
      <td class="text-center">
        <div class="avatar-sm bg-primary rounded-circle d-flex align-items-center justify-content-center">
          <span class="text-white font-weight-bold">${escapeHtml(getInitials(user.display_name))}</span>
        </div>
      </td>
      <td>${escapeHtml(user.first_name || "-")}</td>
      <td>${escapeHtml(user.last_name || "-")}</td>
      <td><strong>${escapeHtml(user.username || "-")}</strong></td>
      <td>${escapeHtml(user.user_role || "user")}</td>
      <td>${escapeHtml(user.company_name || "-")}</td>
      <td>${escapeHtml(user.email || "-")}</td>
      <td>
        <span class="badge badge-outline-primary">${escapeHtml(user.primary_badge)}</span>
        ${
          user.badge_codes.length > 1
            ? `<small class="text-muted">+${user.badge_codes.length - 1} more</small>`
            : ""
        }
      </td>
      <td>
        <span class="badge badge-${statusClass}">${escapeHtml(user.activity_status)}</span>
        <br><small class="text-muted">${escapeHtml(formatDateTime(user.last_activity))}</small>
      </td>
      <td><span class="badge badge-info">${user.total_scans}</span></td>
      <td>
        <div class="d-flex align-items-center list-user-action">
          <a class="iq-bg-primary js-view-user mr-1" href="#" title="View Details">
            <i class="ri-eye-line"></i>
          </a>
          <a class="iq-bg-primary js-edit-user mr-1" href="#" title="Edit">
            <i class="ri-pencil-line"></i>
          </a>
          <a class="iq-bg-primary ${user.blocked ? "js-unblock-user" : "js-block-user"} mr-1" href="#" title="${user.blocked ? "Unblock" : "Block"}">
            ${user.blocked ? "✅" : "🚫"}
          </a>
          <a class="iq-bg-primary js-delete-user" href="#" title="Delete">
            <i class="ri-delete-bin-line"></i>
          </a>
        </div>
      </td>
    `;

    tbody.appendChild(row);
  });

  applyRoleRestrictions();
  bindRowActions();
  updatePagination();
  updateUsersInfo();

  const tableContainer = document.getElementById("users-table-container");
  if (tableContainer) {
    tableContainer.classList.remove("d-none");
  }
}

function applyRoleRestrictions() {
  if (role === "admin") return;

  document.querySelectorAll(".js-block-user, .js-unblock-user, .js-edit-user, .js-delete-user").forEach((btn) => {
    btn.style.pointerEvents = "none";
    btn.style.opacity = "0.5";
    btn.style.cursor = "not-allowed";
  });
}

function bindRowActions() {
  document.querySelectorAll(".js-view-user").forEach((btn) => {
    btn.addEventListener("click", function (event) {
      event.preventDefault();
      const username = this.closest("tr")?.getAttribute("data-username");
      if (username) viewUserDetails(username);
    });
  });

  document.querySelectorAll(".js-edit-user").forEach((btn) => {
    btn.addEventListener("click", function (event) {
      event.preventDefault();
      const username = this.closest("tr")?.getAttribute("data-username");
      if (username) {
        window.location.href = `edit-user.html?username=${encodeURIComponent(username)}`;
      }
    });
  });

  document.querySelectorAll(".js-block-user").forEach((btn) => {
    btn.addEventListener("click", function (event) {
      event.preventDefault();
      const username = this.closest("tr")?.getAttribute("data-username");
      if (username) confirmBlockUser(username);
    });
  });

  document.querySelectorAll(".js-unblock-user").forEach((btn) => {
    btn.addEventListener("click", function (event) {
      event.preventDefault();
      const username = this.closest("tr")?.getAttribute("data-username");
      if (username) confirmUnblockUser(username);
    });
  });

  document.querySelectorAll(".js-delete-user").forEach((btn) => {
    btn.addEventListener("click", function (event) {
      event.preventDefault();
      const username = this.closest("tr")?.getAttribute("data-username");
      if (username) confirmDeleteUser(username);
    });
  });
}

async function viewUserDetails(username) {
  try {
    const response = await fetch(`${url}/api/v1/users/${encodeURIComponent(username)}`, {
      method: "GET",
      headers: authHeaders(),
    });

    if (handleAuthError(response)) return;

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || `HTTP ${response.status}`);
    }

    const user = result?.data || result;
    alert(
      `User Details:\n\n` +
        `Name: ${(user.first_name || "")} ${(user.last_name || "")}\n` +
        `Username: ${user.username || "-"}\n` +
        `Email: ${user.email || "-"}\n` +
        `Company: ${user.company_name || "-"}\n` +
        `Role: ${user.user_role || user.role || "-"}\n` +
        `Blocked: ${user.blocked ? "Yes" : "No"}`
    );
  } catch (error) {
    console.error("Error loading user details:", error);
    alert(`Kon gebruiker niet ophalen: ${error.message}`);
  }
}

function confirmDeleteUser(username) {
  if (role !== "admin") {
    alert("Alleen admins mogen gebruikers verwijderen.");
    return;
  }

  const userConfirmed = confirm(`Weet je zeker dat je de gebruiker "${username}" wilt verwijderen?`);
  if (userConfirmed) {
    deleteUser(username);
  }
}

function confirmBlockUser(username) {
  if (role !== "admin") {
    alert("Alleen admins mogen gebruikers blokkeren.");
    return;
  }

  const userConfirmed = confirm(`Weet je zeker dat je de gebruiker "${username}" wilt blokkeren?`);
  if (userConfirmed) {
    blockUser(username);
  }
}

function confirmUnblockUser(username) {
  if (role !== "admin") {
    alert("Alleen admins mogen gebruikers deblokkeren.");
    return;
  }

  const userConfirmed = confirm(`Weet je zeker dat je de gebruiker "${username}" wilt deblokkeren?`);
  if (userConfirmed) {
    unblockUser(username);
  }
}

async function blockUser(username) {
  try {
    const response = await fetch(`${url}/api/v1/users/${encodeURIComponent(username)}/block`, {
      method: "PUT",
      headers: authHeaders(),
    });

    if (handleAuthError(response)) return;

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || "Unknown error occurred.");
    }

    alert(result.message || "Gebruiker geblokkeerd.");
    loadUsers();
  } catch (error) {
    console.error("Block user error:", error);
    alert(error.message || "Er is een netwerkfout opgetreden.");
  }
}

async function unblockUser(username) {
  try {
    const response = await fetch(`${url}/api/v1/users/${encodeURIComponent(username)}/unblock`, {
      method: "PUT",
      headers: authHeaders(),
    });

    if (handleAuthError(response)) return;

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || "Unknown error occurred.");
    }

    alert(result.message || "Gebruiker gedeblokkeerd.");
    loadUsers();
  } catch (error) {
    console.error("Unblock user error:", error);
    alert(error.message || "Er is een netwerkfout opgetreden.");
  }
}

async function deleteUser(username) {
  try {
    const response = await fetch(`${url}/api/v1/users/${encodeURIComponent(username)}`, {
      method: "DELETE",
      headers: authHeaders(),
    });

    if (handleAuthError(response)) return;

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || "Unknown error occurred.");
    }

    alert(result.message || "Gebruiker verwijderd.");
    loadUsers();
  } catch (error) {
    console.error("Delete user error:", error);
    alert(error.message || "Er is een netwerkfout opgetreden.");
  }
}

function filterUsers() {
  const searchInput = document.getElementById("userSearch");
  const searchTerm = (searchInput?.value || "").toLowerCase().trim();

  if (!searchTerm) {
    filteredUsers = [...allUsers];
  } else {
    filteredUsers = allUsers.filter((user) => {
      return (
        (user.username || "").toLowerCase().includes(searchTerm) ||
        (user.first_name || "").toLowerCase().includes(searchTerm) ||
        (user.last_name || "").toLowerCase().includes(searchTerm) ||
        (user.display_name || "").toLowerCase().includes(searchTerm) ||
        (user.email || "").toLowerCase().includes(searchTerm) ||
        (user.company_name || "").toLowerCase().includes(searchTerm) ||
        user.badge_codes.some((badge) => (badge || "").toLowerCase().includes(searchTerm))
      );
    });
  }

  currentPage = 1;
  renderUsers();
}

function sortUsers(render = true) {
  const sortBy = document.getElementById("sortBy")?.value || "username";

  filteredUsers.sort((a, b) => {
    switch (sortBy) {
      case "username":
        return (a.username || "").localeCompare(b.username || "");
      case "last_activity":
        return new Date(b.last_activity || 0) - new Date(a.last_activity || 0);
      case "total_scans":
        return (b.total_scans || 0) - (a.total_scans || 0);
      default:
        return 0;
    }
  });

  if (render) {
    renderUsers();
  }
}

function updateStats() {
  const totalUsers = allUsers.length;
  const activeToday = allUsers.filter((user) => user.activity_status === "Today").length;
  const totalScans = allUsers.reduce((sum, user) => sum + (user.total_scans || 0), 0);

  const weekAgo = new Date();
  weekAgo.setDate(weekAgo.getDate() - 7);

  const thisWeekActive = allUsers.filter(
    (user) => user.last_activity && new Date(user.last_activity) >= weekAgo
  ).length;

  setText("stats-total-users", totalUsers);
  setText("stats-active-today", activeToday);
  setText("stats-total-scans", totalScans.toLocaleString());
  setText("stats-this-week", thisWeekActive);
}

function getActivityStatus(lastActivity) {
  if (!lastActivity) return "Never";

  const now = new Date();
  const lastDate = new Date(lastActivity);
  const daysDiff = Math.floor((now - lastDate) / (1000 * 60 * 60 * 24));

  if (daysDiff <= 0) return "Today";
  if (daysDiff === 1) return "Yesterday";
  if (daysDiff <= 7) return `${daysDiff} days ago`;
  if (daysDiff <= 30) return `${Math.floor(daysDiff / 7)} weeks ago`;
  return `${Math.floor(daysDiff / 30)} months ago`;
}

function getInitials(name) {
  if (!name) return "U";
  const parts = name.trim().split(" ").filter(Boolean);
  if (parts.length === 0) return "U";
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

function formatDateTime(dateString) {
  if (!dateString) return "Never";

  return new Date(dateString).toLocaleString("nl-NL", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function changePage(page) {
  const totalPages = Math.ceil(filteredUsers.length / usersPerPage);
  if (page < 1 || page > totalPages) return;

  currentPage = page;
  renderUsers();
}

function updatePagination() {
  const totalPages = Math.ceil(filteredUsers.length / usersPerPage);
  const pagination = document.getElementById("users-pagination");

  if (!pagination) return;

  pagination.innerHTML = "";

  if (totalPages <= 1) return;

  const prevLi = document.createElement("li");
  prevLi.className = `page-item ${currentPage === 1 ? "disabled" : ""}`;
  prevLi.innerHTML = `<a class="page-link" href="#">Previous</a>`;
  prevLi.addEventListener("click", function (e) {
    e.preventDefault();
    changePage(currentPage - 1);
  });
  pagination.appendChild(prevLi);

  for (let i = 1; i <= totalPages; i++) {
    const li = document.createElement("li");
    li.className = `page-item ${i === currentPage ? "active" : ""}`;
    li.innerHTML = `<a class="page-link" href="#">${i}</a>`;
    li.addEventListener("click", function (e) {
      e.preventDefault();
      changePage(i);
    });
    pagination.appendChild(li);
  }

  const nextLi = document.createElement("li");
  nextLi.className = `page-item ${currentPage === totalPages ? "disabled" : ""}`;
  nextLi.innerHTML = `<a class="page-link" href="#">Next</a>`;
  nextLi.addEventListener("click", function (e) {
    e.preventDefault();
    changePage(currentPage + 1);
  });
  pagination.appendChild(nextLi);
}

function updateUsersInfo() {
  const info = document.getElementById("users-info");
  if (!info) return;

  if (filteredUsers.length === 0) {
    info.innerHTML = "No users found";
    return;
  }

  const startIndex = (currentPage - 1) * usersPerPage;
  const endIndex = Math.min(startIndex + usersPerPage, filteredUsers.length);
  info.innerHTML = `Showing ${startIndex + 1} to ${endIndex} of ${filteredUsers.length} users`;
}

function exportUsers() {
  if (allUsers.length === 0) {
    alert("No users to export");
    return;
  }

  const headers = [
    "Username",
    "First Name",
    "Last Name",
    "Email",
    "Company",
    "Role",
    "Primary Badge",
    "Total Scans",
    "Last Activity",
  ];

  const csvRows = [headers.join(",")];

  allUsers.forEach((user) => {
    const row = [
      `"${(user.username || "").replace(/"/g, '""')}"`,
      `"${(user.first_name || "").replace(/"/g, '""')}"`,
      `"${(user.last_name || "").replace(/"/g, '""')}"`,
      `"${(user.email || "").replace(/"/g, '""')}"`,
      `"${(user.company_name || "").replace(/"/g, '""')}"`,
      `"${(user.user_role || "").replace(/"/g, '""')}"`,
      `"${(user.primary_badge || "").replace(/"/g, '""')}"`,
      user.total_scans || 0,
      `"${formatDateTime(user.last_activity).replace(/"/g, '""')}"`,
    ];
    csvRows.push(row.join(","));
  });

  const csvContent = csvRows.join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const exportUrl = URL.createObjectURL(blob);

  link.setAttribute("href", exportUrl);
  link.setAttribute("download", `users-export-${new Date().toISOString().slice(0, 10)}.csv`);
  link.style.visibility = "hidden";

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function refreshUsers() {
  loadUsers();
}

function showLoading() {
  document.getElementById("users-loading")?.classList.remove("d-none");
  document.getElementById("users-table-container")?.classList.add("d-none");
  document.getElementById("no-users")?.classList.add("d-none");
  document.getElementById("users-error")?.classList.add("d-none");
}

function hideLoading() {
  document.getElementById("users-loading")?.classList.add("d-none");
}

function showNoUsers() {
  hideLoading();
  document.getElementById("no-users")?.classList.remove("d-none");
  document.getElementById("users-table-container")?.classList.add("d-none");
}

function showError(message) {
  hideLoading();

  const errorDiv = document.getElementById("users-error");
  if (!errorDiv) {
    console.error(message);
    return;
  }

  errorDiv.innerHTML = `
    <div class="alert alert-danger" role="alert">
      <i class="las la-exclamation-triangle"></i> ${escapeHtml(String(message))}
    </div>
  `;
  errorDiv.classList.remove("d-none");
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function debounce(func, delay) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), delay);
  };
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/* Optional: globally expose functions if your HTML uses inline onclick */
window.changePage = changePage;
window.exportUsers = exportUsers;
window.refreshUsers = refreshUsers;
window.viewUserDetails = viewUserDetails;