const url = "http://172.28.0.15:8000"; // Basis-URL

// Haal de rol van de huidige gebruiker op uit sessionStorage
const role = sessionStorage.getItem("role"); // Verwacht "Admin" of andere rollen (bijv. "User")

const showAvatar = function (blocked) {
  if (blocked) {
    return "images/user/11.png";
  } else {
    return "images/user/11_green.png";
  }
};

const showBlockStatus = function (blocked) {
  if (blocked) {
    return "✅";
  } else {
    return "🚫";
  }
};

const showJsBlockStatus = function (blocked) {
  if (blocked) {
    return "js-unblock-user";
  } else {
    return "js-block-user";
  }
};

const showUsers = function (jsonObject) {
  try {
    console.info(jsonObject);
    let htmlusers = ``;

    for (const user of jsonObject.users) {
      console.info(user);
      htmlusers += `
      <tr data-username="${user.username}">
        <td class="text-center"><img class="rounded img-fluid avatar-40" src=${showAvatar(user.blocked)} alt="profile"></td>
        <td>${user.first_name}</td>
        <td>${user.last_name}</td>
        <td>${user.username}</td>
        <td>${user.user_role}</td>
        <td>${user.company_name}</td>
        <td>${user.email}</td>
        <td>
            <div class="d-flex align-items-center list-user-action">
                <a class="iq-bg-primary ${showJsBlockStatus(user.blocked)} " data-toggle="tooltip" data-placement="top" title="" data-original-title="Block" href="#">${showBlockStatus(user.blocked)}<i class="text-center"></i></a>
                <a class="iq-bg-primary js-edit-user" data-toggle="tooltip" data-placement="top" title="" data-original-title="Edit" href="#"><i class="ri-pencil-line"></i></a>
                <a class="iq-bg-primary js-delete-user" data-toggle="tooltip" data-placement="top" title="" data-original-title="Delete" href="#"><i class="ri-delete-bin-line"></i></a>
            </div>
        </td>
      </tr>`;
    }

    console.info(htmlusers);
    document.querySelector(".js-users").innerHTML = htmlusers;

    // Alleen Admins mogen bewerken, blokkeren en verwijderen
    if (role !== "Admin") {
      document.querySelectorAll(".js-block-user").forEach((btn) => {
        btn.style.pointerEvents = "none"; // Disable bewerken
        btn.style.opacity = "0.5"; // Maak de knop semi-transparant
        btn.style.cursor = "not-allowed"; // Verander de cursor naar 'not-allowed'
      });

      document.querySelectorAll(".js-edit-user").forEach((btn) => {
        btn.style.pointerEvents = "none"; // Disable bewerken
        btn.style.opacity = "0.5"; // Maak de knop semi-transparant
        btn.style.cursor = "not-allowed"; // Verander de cursor naar 'not-allowed'
      });

      document.querySelectorAll(".js-delete-user").forEach((btn) => {
        btn.style.pointerEvents = "none"; // Disable bewerken
        btn.style.opacity = "0.5"; // Maak de knop semi-transparant
        btn.style.cursor = "not-allowed"; // Verander de cursor naar 'not-allowed'
      });
    }

    // Voeg de event listeners toe voor de Admin acties
    document.querySelectorAll(".js-block-user").forEach((btn) => {
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        const username = this.closest("tr").getAttribute("data-username");
        confirmBlockUser(username);
      });
    });

    document.querySelectorAll(".js-unblock-user").forEach((btn) => {
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        const username = this.closest("tr").getAttribute("data-username");
        confirmUnBlockUser(username);
      });
    });

    document.querySelectorAll(".js-delete-user").forEach((btn) => {
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        const username = this.closest("tr").getAttribute("data-username");
        confirmDeleteUser(username);
      });
    });

    document.querySelectorAll(".js-edit-user").forEach((btn) => {
      btn.addEventListener("click", function (event) {
        event.preventDefault();
        const username = this.closest("tr").getAttribute("data-username");
        window.location.href = `edit-user.html?username=${username}`;
      });
    });
  } catch (err) {
    console.error(err);
  }
};

const showError = function (error) {
  console.error(error);
};

const getUsers = function () {
  handleData(`${url}/api/v1/user/all/`, showUsers, showError);
};

const confirmDeleteUser = function (username) {
  const userConfirmed = confirm(`Weet je zeker dat je de gebruiker "${username}" wilt verwijderen?`);
  if (userConfirmed) {
    deleteUser(username);
  }
};

const confirmBlockUser = function (username) {
  const userConfirmed = confirm(`Weet je zeker dat je de gebruiker "${username}" wilt blokeren?`);
  if (userConfirmed) {
    blockUser(username);
  }
};

const confirmUnBlockUser = function (username) {
  const userConfirmed = confirm(`Weet je zeker dat je de gebruiker "${username}" wilt Deblokeren?`);
  if (userConfirmed) {
    unblockUser(username);
  }
};

const blockUser = async function (username) {
  try {
    const response = await fetch(`${url}/api/v1/users/${username}/block`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (response.ok) {
      const result = await response.json();
      alert(result.message);
      getUsers();
    } else {
      const errorData = await response.json();
      alert("Error: " + (errorData.message || "Unknown error occurred."));
    }
  } catch (err) {
    console.error("Network error:", err);
    alert("A network error occurred. Please try again.");
  }
};

const unblockUser = async function (username) {
  try {
    const response = await fetch(`${url}/api/v1/users/${username}/unblock`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (response.ok) {
      const result = await response.json();
      alert(result.message);
      getUsers();
    } else {
      const errorData = await response.json();
      alert("Error: " + (errorData.message || "Unknown error occurred."));
    }
  } catch (err) {
    console.error("Network error:", err);
    alert("A network error occurred. Please try again.");
  }
};

const deleteUser = async function (username) {
  try {
    const response = await fetch(`${url}/api/v1/users/${username}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (response.ok) {
      const result = await response.json();
      alert(result.message);
      getUsers();
    } else {
      const errorData = await response.json();
      alert("Error: " + (errorData.message || "Unknown error occurred."));
    }
  } catch (err) {
    console.error("Network error:", err);
    alert("A network error occurred. Please try again.");
  }
};

const filterUsers = function (searchTerm) {
  const rows = document.querySelectorAll(".js-users tr");

  rows.forEach((row) => {
    const username = row.querySelector("td:nth-child(4)")?.textContent.toLowerCase() || "";
    const firstName = row.querySelector("td:nth-child(2)")?.textContent.toLowerCase() || "";
    const lastName = row.querySelector("td:nth-child(3)")?.textContent.toLowerCase() || "";

    if (username.includes(searchTerm) || firstName.includes(searchTerm) || lastName.includes(searchTerm)) {
      row.style.display = "";
    } else {
      row.style.display = "none";
    }
  });
};

const debounce = (func, delay) => {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), delay);
  };
};

const handleExport = function (type) {
  const table = document.querySelector("#user-list-table");

  if (!table) {
    console.error("Geen tabel gevonden om te exporteren!");
    alert("Geen gegevens om te exporteren.");
    return;
  }

  if (type === "print") {
    const printWindow = window.open("", "_blank");
    printWindow.document.write("<html><head><title>Print Logs</title></head><body>");
    printWindow.document.write(table.outerHTML);
    printWindow.document.write("</body></html>");
    printWindow.document.close();
    printWindow.print();
  } else if (type === "excel") {
    const tableHtml = table.outerHTML.replace(/ /g, "%20");
    const downloadLink = document.createElement("a");
    downloadLink.href = "data:application/vnd.ms-excel," + tableHtml;
    downloadLink.download = "logs.xls";
    downloadLink.click();
  } else if (type === "pdf") {
    if (window.jsPDF) {
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF();

      doc.text("Device Logs", 10, 10);

      const headers = [];
      const body = [];

      table.querySelectorAll("thead tr th").forEach((header) => {
        headers.push(header.textContent.trim());
      });

      table.querySelectorAll("tbody tr").forEach((row) => {
        const rowData = [];
        row.querySelectorAll("td").forEach((cell) => {
          rowData.push(cell.textContent.trim());
        });
        body.push(rowData);
      });

      doc.autoTable({
        head: [headers],
        body: body,
        startY: 20,
      });

      doc.save("logs.pdf");
    } else {
      console.error("jsPDF is niet geladen.");
      alert("PDF export vereist de jsPDF-bibliotheek.");
    }
  }
};

// Global variables
let allUsers = [];
let filteredUsers = [];
let currentPage = 1;
let usersPerPage = 10;

// API URL configuration (same as other pages)
function getApiUrl() {
  const currentPort = window.location.port;
  const currentHost = window.location.hostname;

  if (currentPort === "8080") {
    return "http://172.28.0.15:5000";
  }

  if (currentHost === "localhost" || currentHost === "127.0.0.1") {
    return "http://localhost:5000";
  }

  if (currentHost.match(/^\d+\.\d+\.\d+\.\d+$/)) {
    return `http://${currentHost}:5000`;
  }

  return "http://192.168.0.196:5000";
}

const apiUrl = getApiUrl();

// Initialize page
document.addEventListener("DOMContentLoaded", function () {
  console.log("Loading users list...");
  loadUsers();
});

// Load users from badge database
async function loadUsers() {
  try {
    showLoading();

    // Fetch all badges to extract unique users
    const requestBody = {
      filters: {},
      limit: 10000, // Large number to get all badges
      sort: { timestamp: -1 },
    };

    console.log("Fetching badge data to extract users...");

    const response = await fetch(`${apiUrl}/api/v1/badges/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log("Received badge data:", data);

    const badges = data.badges || [];
    processUsersFromBadges(badges);
  } catch (error) {
    console.error("Error loading users:", error);
    showError(`Error loading users: ${error.message}`);
  }
}

// Process badges to extract unique users
function processUsersFromBadges(badges) {
  if (badges.length === 0) {
    showNoUsers();
    return;
  }

  const usersMap = new Map();

  // Group badges by username
  badges.forEach((badge) => {
    const username = badge.username || badge.user || "Unknown";
    const userId = badge.user_id || username;
    const firstName = badge.first_name || "";
    const lastName = badge.last_name || "";
    const badgeCode = badge.badgecode || badge.badge_code || "";

    if (!usersMap.has(username)) {
      usersMap.set(username, {
        username: username,
        user_id: userId,
        first_name: firstName,
        last_name: lastName,
        badge_codes: new Set(),
        total_scans: 0,
        last_activity: null,
        first_activity: null,
        recent_badges: [],
      });
    }

    const user = usersMap.get(username);

    // Add badge code
    if (badgeCode) {
      user.badge_codes.add(badgeCode);
    }

    // Increment scan count
    user.total_scans++;

    // Update activity dates
    const badgeDate = new Date(badge.timestamp);
    if (!user.last_activity || badgeDate > new Date(user.last_activity)) {
      user.last_activity = badge.timestamp;
    }
    if (!user.first_activity || badgeDate < new Date(user.first_activity)) {
      user.first_activity = badge.timestamp;
    }

    // Store recent badge info
    user.recent_badges.push({
      badge_code: badgeCode,
      action: badge.action,
      timestamp: badge.timestamp,
      location: badge.location,
    });
  });

  // Convert Map to Array and process
  allUsers = Array.from(usersMap.values()).map((user) => ({
    ...user,
    badge_codes: Array.from(user.badge_codes),
    primary_badge: Array.from(user.badge_codes)[0] || "N/A",
    display_name: `${user.first_name} ${user.last_name}`.trim() || user.username,
    activity_status: getActivityStatus(user.last_activity),
  }));

  console.log("Processed users:", allUsers);

  filteredUsers = [...allUsers];
  sortUsers();
  renderUsers();
  hideLoading();
  updateStats();
}

// Update statistics
function updateStats() {
  const totalUsers = allUsers.length;
  const activeToday = allUsers.filter((user) => user.activity_status === "Today").length;
  const totalScans = allUsers.reduce((sum, user) => sum + user.total_scans, 0);

  const weekAgo = new Date();
  weekAgo.setDate(weekAgo.getDate() - 7);
  const thisWeekActive = allUsers.filter((user) => user.last_activity && new Date(user.last_activity) >= weekAgo).length;

  document.getElementById("stats-total-users").textContent = totalUsers;
  document.getElementById("stats-active-today").textContent = activeToday;
  document.getElementById("stats-total-scans").textContent = totalScans.toLocaleString();
  document.getElementById("stats-this-week").textContent = thisWeekActive;
}

// Get activity status based on last activity
function getActivityStatus(lastActivity) {
  if (!lastActivity) return "Never";

  const now = new Date();
  const lastDate = new Date(lastActivity);
  const daysDiff = Math.floor((now - lastDate) / (1000 * 60 * 60 * 24));

  if (daysDiff === 0) return "Today";
  if (daysDiff === 1) return "Yesterday";
  if (daysDiff <= 7) return `${daysDiff} days ago`;
  if (daysDiff <= 30) return `${Math.floor(daysDiff / 7)} weeks ago`;
  return `${Math.floor(daysDiff / 30)} months ago`;
}

// Render users table
function renderUsers() {
  const tbody = document.getElementById("users-tbody");
  tbody.innerHTML = "";

  if (filteredUsers.length === 0) {
    showNoUsers();
    return;
  }

  // Calculate pagination
  const startIndex = (currentPage - 1) * usersPerPage;
  const endIndex = Math.min(startIndex + usersPerPage, filteredUsers.length);
  const pageUsers = filteredUsers.slice(startIndex, endIndex);

  // Generate table rows
  pageUsers.forEach((user) => {
    const row = document.createElement("tr");

    // Activity status styling
    const statusClass = user.activity_status === "Today" ? "success" : user.activity_status === "Yesterday" ? "warning" : "secondary";

    row.innerHTML = `
      <td class="text-center">
        <div class="avatar-sm bg-primary rounded-circle d-flex align-items-center justify-content-center">
          <span class="text-white font-weight-bold">${getInitials(user.display_name)}</span>
        </div>
      </td>
      <td>${user.first_name || "-"}</td>
      <td>${user.last_name || "-"}</td>
      <td><strong>${user.username}</strong></td>
      <td>
        <span class="badge badge-outline-primary">${user.primary_badge}</span>
        ${user.badge_codes.length > 1 ? `<small class="text-muted">+${user.badge_codes.length - 1} more</small>` : ""}
      </td>
      <td>
        <span class="badge badge-${statusClass}">${user.activity_status}</span>
        <br><small class="text-muted">${formatDateTime(user.last_activity)}</small>
      </td>
      <td><span class="badge badge-info">${user.total_scans}</span></td>
      <td>
        <div class="d-flex align-items-center">
          <button class="btn btn-primary btn-sm mr-2" onclick="viewTimesheet('${user.username}')" 
                  title="View Timesheet">
            <i class="las la-clock"></i> View Timesheet
          </button>
          <div class="dropdown">
            <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" 
                    id="dropdownUser${user.username}" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
              <i class="las la-ellipsis-v"></i>
            </button>
            <div class="dropdown-menu" aria-labelledby="dropdownUser${user.username}">
              <a class="dropdown-item" href="#" onclick="viewUserDetails('${user.username}')">
                <i class="las la-eye"></i> View Details
              </a>
              <a class="dropdown-item" href="badgelist.html?user=${encodeURIComponent(user.username)}">
                <i class="las la-list"></i> Badge History
              </a>
            </div>
          </div>
        </div>
      </td>
    `;

    tbody.appendChild(row);
  });

  // Update pagination and info
  updatePagination();
  updateUsersInfo();

  document.getElementById("users-table-container").classList.remove("d-none");
}

// Get user initials for avatar
function getInitials(name) {
  if (!name) return "U";
  const parts = name.trim().split(" ");
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

// Format date time
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

// View user timesheet
function viewTimesheet(username) {
  window.open(`timesheet.html?username=${encodeURIComponent(username)}`, "_blank");
}

// View user details (modal or new page)
function viewUserDetails(username) {
  const user = allUsers.find((u) => u.username === username);
  if (!user) return;

  // Create details modal or navigate to details page
  alert(`User Details:\n\nName: ${user.display_name}\nUsername: ${user.username}\nBadge Codes: ${user.badge_codes.join(", ")}\nTotal Scans: ${user.total_scans}\nLast Activity: ${formatDateTime(user.last_activity)}`);
}

// Filter users
function filterUsers() {
  const searchTerm = document.getElementById("userSearch").value.toLowerCase();

  if (!searchTerm.trim()) {
    filteredUsers = [...allUsers];
  } else {
    filteredUsers = allUsers.filter((user) => user.username.toLowerCase().includes(searchTerm) || user.first_name.toLowerCase().includes(searchTerm) || user.last_name.toLowerCase().includes(searchTerm) || user.display_name.toLowerCase().includes(searchTerm) || user.badge_codes.some((badge) => badge.toLowerCase().includes(searchTerm)));
  }

  currentPage = 1; // Reset to first page
  renderUsers();
}

// Sort users
function sortUsers() {
  const sortBy = document.getElementById("sortBy").value;

  filteredUsers.sort((a, b) => {
    switch (sortBy) {
      case "username":
        return a.username.localeCompare(b.username);
      case "last_activity":
        return new Date(b.last_activity || 0) - new Date(a.last_activity || 0);
      case "total_scans":
        return b.total_scans - a.total_scans;
      default:
        return 0;
    }
  });

  renderUsers();
}

// Update pagination
function updatePagination() {
  const totalPages = Math.ceil(filteredUsers.length / usersPerPage);
  const pagination = document.getElementById("users-pagination");
  pagination.innerHTML = "";

  if (totalPages <= 1) return;

  // Previous button
  const prevLi = document.createElement("li");
  prevLi.className = `page-item ${currentPage === 1 ? "disabled" : ""}`;
  prevLi.innerHTML = `<a class="page-link" href="#" onclick="changePage(${currentPage - 1})">Previous</a>`;
  pagination.appendChild(prevLi);

  // Page numbers
  for (let i = 1; i <= totalPages; i++) {
    const li = document.createElement("li");
    li.className = `page-item ${i === currentPage ? "active" : ""}`;
    li.innerHTML = `<a class="page-link" href="#" onclick="changePage(${i})">${i}</a>`;
    pagination.appendChild(li);
  }

  // Next button
  const nextLi = document.createElement("li");
  nextLi.className = `page-item ${currentPage === totalPages ? "disabled" : ""}`;
  nextLi.innerHTML = `<a class="page-link" href="#" onclick="changePage(${currentPage + 1})">Next</a>`;
  pagination.appendChild(nextLi);
}

// Change page
function changePage(page) {
  const totalPages = Math.ceil(filteredUsers.length / usersPerPage);
  if (page < 1 || page > totalPages) return;

  currentPage = page;
  renderUsers();
}

// Update users info
function updateUsersInfo() {
  const startIndex = (currentPage - 1) * usersPerPage;
  const endIndex = Math.min(startIndex + usersPerPage, filteredUsers.length);

  document.getElementById("users-info").innerHTML = `Showing ${startIndex + 1} to ${endIndex} of ${filteredUsers.length} users`;
}

// Export users
function exportUsers() {
  if (allUsers.length === 0) {
    alert("No users to export");
    return;
  }

  const headers = ["Username", "First Name", "Last Name", "Primary Badge", "Total Scans", "Last Activity"];
  const csvRows = [headers.join(",")];

  allUsers.forEach((user) => {
    const row = [`"${user.username}"`, `"${user.first_name || ""}"`, `"${user.last_name || ""}"`, `"${user.primary_badge}"`, user.total_scans, `"${formatDateTime(user.last_activity)}"`];
    csvRows.push(row.join(","));
  });

  const csvContent = csvRows.join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);

  link.setAttribute("href", url);
  link.setAttribute("download", `users-export-${new Date().toISOString().slice(0, 10)}.csv`);
  link.style.visibility = "hidden";

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Refresh users
function refreshUsers() {
  loadUsers();
}

// UI Helper functions
function showLoading() {
  document.getElementById("users-loading").classList.remove("d-none");
  document.getElementById("users-table-container").classList.add("d-none");
  document.getElementById("no-users").classList.add("d-none");
  document.getElementById("users-error").classList.add("d-none");
}

function hideLoading() {
  document.getElementById("users-loading").classList.add("d-none");
}

function showNoUsers() {
  hideLoading();
  document.getElementById("no-users").classList.remove("d-none");
  document.getElementById("users-table-container").classList.add("d-none");
}

function showError(message) {
  hideLoading();
  const errorDiv = document.getElementById("users-error");
  errorDiv.innerHTML = `
    <div class="alert alert-danger" role="alert">
      <i class="las la-exclamation-triangle"></i> ${message}
    </div>
  `;
  errorDiv.classList.remove("d-none");
}
