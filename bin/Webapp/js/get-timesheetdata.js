let currentUser = null;
let currentPeriodType = "week";
let currentWeek = null;
let currentMonth = null;

let timesheetDays = [];
let currentSummary = null;

let dailyHoursChart = null;
let hoursBreakdownChart = null;

const currentHost = window.location.hostname;
const url = `http://${currentHost}:5000`;
const apiUrl = `${url}/api/v1`;

document.addEventListener("DOMContentLoaded", function () {
  const token = localStorage.getItem("access_token");

  if (!token) {
    window.location.href = "/index.html";
    return;
  }

  currentUser = getUsernameFromUrl();

  if (!currentUser) {
    showError("No username provided in URL. Use ?username=<username>");
    return;
  }

  setText("user-name", currentUser);
  setText("user-id", currentUser);

  bindPeriodEvents();
  setPeriod("week", true);
  loadTimesheetData();
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

function getUsernameFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get("username") || urlParams.get("user");
}

function bindPeriodEvents() {
  document.getElementById("btn-week")?.addEventListener("click", function () {
    setPeriod("week");
  });

  document.getElementById("btn-month")?.addEventListener("click", function () {
    setPeriod("month");
  });

  document.getElementById("week-selector")?.addEventListener("change", function (e) {
    currentWeek = e.target.value;
    updatePeriodLabel();
    loadTimesheetData();
  });

  document.getElementById("month-selector")?.addEventListener("change", function (e) {
    currentMonth = e.target.value;
    updatePeriodLabel();
    loadTimesheetData();
  });
}

function setPeriod(type, skipLoad = false) {
  currentPeriodType = type;

  const btnWeek = document.getElementById("btn-week");
  const btnMonth = document.getElementById("btn-month");
  const weekSelector = document.getElementById("week-selector");
  const monthSelector = document.getElementById("month-selector");

  if (type === "week") {
    btnWeek?.classList.add("active");
    btnMonth?.classList.remove("active");

    if (weekSelector) weekSelector.style.display = "";
    if (monthSelector) monthSelector.style.display = "none";

    fillWeekSelector();
  } else {
    btnWeek?.classList.remove("active");
    btnMonth?.classList.add("active");

    if (weekSelector) weekSelector.style.display = "none";
    if (monthSelector) monthSelector.style.display = "";

    fillMonthSelector();
  }

  updatePeriodLabel();

  if (!skipLoad) {
    loadTimesheetData();
  }
}

function fillWeekSelector() {
  const weekSelector = document.getElementById("week-selector");
  if (!weekSelector) return;

  weekSelector.innerHTML = "";

  const now = new Date();
  let currentYear = now.getFullYear();
  let currentWeekNumber = getWeekNumber(now);

  for (let i = 0; i < 12; i++) {
    let weekNum = currentWeekNumber - i;
    let weekYear = currentYear;

    if (weekNum <= 0) {
      weekYear--;
      weekNum += getWeeksInYear(weekYear);
    }

    const option = document.createElement("option");
    option.value = `${weekYear}-W${weekNum.toString().padStart(2, "0")}`;
    option.text = `Week ${weekNum}, ${weekYear}`;
    weekSelector.appendChild(option);
  }

  if (currentWeek && Array.from(weekSelector.options).some((opt) => opt.value === currentWeek)) {
    weekSelector.value = currentWeek;
  } else {
    currentWeek = weekSelector.options[0]?.value || null;
    weekSelector.value = currentWeek;
  }
}

function fillMonthSelector() {
  const monthSelector = document.getElementById("month-selector");
  if (!monthSelector) return;

  monthSelector.innerHTML = "";

  const now = new Date();
  let currentYear = now.getFullYear();
  let currentMonthNum = now.getMonth();

  for (let i = 0; i < 12; i++) {
    let monthNum = currentMonthNum - i;
    let monthYear = currentYear;

    if (monthNum < 0) {
      monthYear--;
      monthNum += 12;
    }

    const option = document.createElement("option");
    option.value = `${monthYear}-${(monthNum + 1).toString().padStart(2, "0")}`;
    option.text = `${getMonthName(monthNum)} ${monthYear}`;
    monthSelector.appendChild(option);
  }

  if (currentMonth && Array.from(monthSelector.options).some((opt) => opt.value === currentMonth)) {
    monthSelector.value = currentMonth;
  } else {
    currentMonth = monthSelector.options[0]?.value || null;
    monthSelector.value = currentMonth;
  }
}

function updatePeriodLabel() {
  const label = document.getElementById("period-label");
  if (!label) return;

  if (currentPeriodType === "week" && currentWeek) {
    label.textContent = currentWeek.replace("-W", " Week ");
  } else if (currentPeriodType === "month" && currentMonth) {
    const [year, month] = currentMonth.split("-");
    label.textContent = `${getMonthName(parseInt(month, 10) - 1)} ${year}`;
  }
}

function getWeekNumber(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
}

function getWeeksInYear(year) {
  const d = new Date(year, 11, 31);
  const week = getWeekNumber(d);
  return week === 1 ? 52 : week;
}

function getMonthName(monthIdx) {
  const months = [
    "Januari",
    "Februari",
    "Maart",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Augustus",
    "September",
    "Oktober",
    "November",
    "December",
  ];
  return months[monthIdx];
}

function getRangeForCurrentPeriod() {
  if (currentPeriodType === "week") {
    const [year, week] = currentWeek.split("-W");
    const simple = new Date(year, 0, 1 + (parseInt(week, 10) - 1) * 7);
    const dow = simple.getDay();
    const monday = new Date(simple);

    if (dow <= 4) {
      monday.setDate(simple.getDate() - simple.getDay() + 1);
    } else {
      monday.setDate(simple.getDate() + 8 - simple.getDay());
    }

    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    return {
      start: formatDateKey(monday),
      end: formatDateKey(sunday),
    };
  }

  const [year, month] = currentMonth.split("-");
  const start = `${year}-${month}-01`;
  const lastDay = new Date(parseInt(year, 10), parseInt(month, 10), 0).getDate();
  const end = `${year}-${month}-${String(lastDay).padStart(2, "0")}`;

  return { start, end };
}

async function loadTimesheetData() {
  try {
    showLoading();

    const range = getRangeForCurrentPeriod();
    const endpoint = `${apiUrl}/timesheets/${encodeURIComponent(currentUser)}/range?start=${encodeURIComponent(range.start)}&end=${encodeURIComponent(range.end)}`;

    const response = await fetch(endpoint, {
      method: "GET",
      headers: authHeaders(false),
    });

    if (handleAuthError(response)) return;

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || `HTTP ${response.status}`);
    }

    const data = result?.data || result;

    timesheetDays = Array.isArray(data.days) ? data.days : [];
    currentSummary = data.summary || {
      total_days: 0,
      worked_days: 0,
      complete_days: 0,
      total_work_seconds: 0,
      total_break_seconds: 0,
      total_work_hours_decimal: 0,
      total_break_hours_decimal: 0,
      average_work_hours_per_worked_day: 0,
    };

    updateStatistics(currentSummary);
    updateCharts(timesheetDays, currentSummary);
    updateTable(timesheetDays);
    hideLoading();

    if (timesheetDays.length === 0 || !timesheetDays.some((d) => Number(d.work_hours_decimal || 0) > 0 || Number(d.break_hours_decimal || 0) > 0)) {
      showNoData();
    }
  } catch (error) {
    console.error("Error loading timesheet data:", error);
    showError(`Error loading timesheet data: ${error.message}`);
  }
}

function smartRound(val) {
  return (Math.round(Number(val || 0) * 10) / 10).toFixed(1);
}

function updateStatistics(summary) {
  setText("total-hours", `${smartRound(summary.total_work_hours_decimal)}h`);
  setText("working-days", summary.worked_days || 0);
  setText("avg-hours", `${smartRound(summary.average_work_hours_per_worked_day)}h`);
  setText("break-time", `${smartRound(summary.total_break_hours_decimal)}h`);
  setText("last-updated", formatDateTime(new Date().toISOString()));
}

function updateCharts(days, summary) {
  const hasData = days.some(
    (d) => Number(d.work_hours_decimal || 0) > 0 || Number(d.break_hours_decimal || 0) > 0
  );

  if (!hasData) {
    if (dailyHoursChart) {
      dailyHoursChart.destroy();
      dailyHoursChart = null;
    }
    if (hoursBreakdownChart) {
      hoursBreakdownChart.destroy();
      hoursBreakdownChart = null;
    }
    return;
  }

  updateDailyHoursChart(days);
  updateHoursBreakdownChart(days, summary);
}

function updateDailyHoursChart(days) {
  const chartCanvas = document.getElementById("dailyHoursChart");
  if (!chartCanvas) return;

  const ctx = chartCanvas.getContext("2d");

  if (dailyHoursChart) {
    dailyHoursChart.destroy();
  }

  const labels = days.map((day) =>
    new Date(day.date).toLocaleDateString("nl-NL", {
      weekday: "short",
      month: "short",
      day: "numeric",
    })
  );

  const workHours = days.map((day) => Number(day.work_hours_decimal || 0));
  const breakHours = days.map((day) => Number(day.break_hours_decimal || 0));
  const overtime = workHours.map((h) => (h > 8 ? h - 8 : 0));
  const normalHours = workHours.map((h) => (h > 8 ? 8 : h));

  dailyHoursChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Normale uren (max 8)",
          data: normalHours,
          backgroundColor: "rgba(54, 162, 235, 0.7)",
          borderColor: "rgba(54, 162, 235, 1)",
          borderWidth: 1,
          stack: "stack-hours",
        },
        {
          label: "Overuren",
          data: overtime,
          backgroundColor: "rgba(255, 99, 132, 0.7)",
          borderColor: "rgba(255, 99, 132, 1)",
          borderWidth: 1,
          stack: "stack-hours",
        },
        {
          label: "Pauze (uren)",
          data: breakHours,
          backgroundColor: "rgba(255, 206, 86, 0.7)",
          borderColor: "rgba(255, 206, 86, 1)",
          borderWidth: 1,
          stack: "stack-hours",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          mode: "index",
          intersect: false,
        },
      },
      scales: {
        x: {
          stacked: true,
        },
        y: {
          stacked: true,
          beginAtZero: true,
          title: {
            display: true,
            text: "Uren",
          },
        },
      },
    },
  });
}

function updateHoursBreakdownChart(days, summary) {
  const chartCanvas = document.getElementById("hoursBreakdownChart");
  if (!chartCanvas) return;

  const ctx = chartCanvas.getContext("2d");

  if (hoursBreakdownChart) {
    hoursBreakdownChart.destroy();
  }

  const standardWorkHours = days.length * 8;
  const totalHours = Number(summary.total_work_hours_decimal || 0);
  const overtime = Math.max(0, totalHours - standardWorkHours);
  const regular = Math.min(totalHours, standardWorkHours);
  const missing = Math.max(0, standardWorkHours - totalHours);

  hoursBreakdownChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Regular Hours", "Overtime", "Missing Hours"],
      datasets: [
        {
          data: [regular, overtime, missing],
          backgroundColor: [
            "rgba(75, 192, 192, 0.6)",
            "rgba(255, 206, 86, 0.6)",
            "rgba(255, 99, 132, 0.6)",
          ],
          borderColor: [
            "rgba(75, 192, 192, 1)",
            "rgba(255, 206, 86, 1)",
            "rgba(255, 99, 132, 1)",
          ],
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  });
}

function updateTable(days) {
  const tbody = document.getElementById("timesheet-tbody");
  if (!tbody) return;

  tbody.innerHTML = "";

  const sortedDays = [...days].sort((a, b) => new Date(b.date) - new Date(a.date));

  sortedDays.forEach((day) => {
    const row = document.createElement("tr");

    const statusClass =
      day.is_complete === true
        ? "success"
        : day.open_status === "working" || day.open_status === "on_break"
        ? "warning"
        : "danger";

    const statusLabel =
      day.is_complete === true
        ? "Complete"
        : day.open_status === "working"
        ? "Working"
        : day.open_status === "on_break"
        ? "On Break"
        : "Incomplete";

    const firstStart = getFirstEventTime(day.events, "START");
    const lastStop = getLastEventTime(day.events, "STOP");

    row.innerHTML = `
      <td>${escapeHtml(formatDayLabel(day.date))}</td>
      <td>${escapeHtml(firstStart || "-")}</td>
      <td>${escapeHtml(lastStop || "-")}</td>
      <td>${smartRound(day.break_hours_decimal)}h</td>
      <td><strong>${smartRound(day.work_hours_decimal)}h</strong></td>
      <td><span class="badge badge-${statusClass}">${escapeHtml(statusLabel)}</span></td>
    `;

    tbody.appendChild(row);
  });

  document.getElementById("timesheet-table")?.classList.remove("d-none");
}

function getFirstEventTime(events = [], actionName) {
  const found = events.find((e) => String(e.action || "").toUpperCase() === actionName);
  if (!found?.timestamp) return null;

  return new Date(found.timestamp).toLocaleTimeString("nl-NL", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getLastEventTime(events = [], actionName) {
  const filtered = events.filter((e) => String(e.action || "").toUpperCase() === actionName);
  if (filtered.length === 0) return null;

  const found = filtered[filtered.length - 1];
  return new Date(found.timestamp).toLocaleTimeString("nl-NL", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDayLabel(dateString) {
  return new Date(dateString).toLocaleDateString("nl-NL", {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatDateTime(dateTimeString) {
  if (!dateTimeString) return "N/A";

  try {
    return new Date(dateTimeString).toLocaleString("nl-NL");
  } catch (e) {
    return dateTimeString;
  }
}

function formatDateKey(dateObj) {
  const year = dateObj.getFullYear();
  const month = String(dateObj.getMonth() + 1).padStart(2, "0");
  const day = String(dateObj.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) {
    el.textContent = value;
  }
}

function showLoading() {
  document.getElementById("table-loading")?.classList.remove("d-none");
  document.getElementById("timesheet-table")?.classList.add("d-none");
  document.getElementById("no-data")?.classList.add("d-none");
  document.getElementById("table-error")?.classList.add("d-none");
}

function hideLoading() {
  document.getElementById("table-loading")?.classList.add("d-none");
}

function showNoData() {
  hideLoading();
  document.getElementById("no-data")?.classList.remove("d-none");
  updateStatistics({
    total_work_hours_decimal: 0,
    total_break_hours_decimal: 0,
    worked_days: 0,
    average_work_hours_per_worked_day: 0,
  });
}

function showError(message) {
  hideLoading();
  const errorDiv = document.getElementById("table-error");
  if (!errorDiv) return;

  errorDiv.innerHTML = `
    <div class="alert alert-danger" role="alert">
      <i class="las la-exclamation-triangle"></i> ${escapeHtml(message)}
    </div>
  `;
  errorDiv.classList.remove("d-none");
}

function exportTimesheet() {
  if (!timesheetDays || timesheetDays.length === 0) {
    alert("No data to export");
    return;
  }

  const headers = ["Date", "Clock In", "Clock Out", "Break Hours", "Work Hours", "Status"];
  const csvRows = [headers.join(",")];

  timesheetDays.forEach((day) => {
    const firstStart = getFirstEventTime(day.events, "START") || "-";
    const lastStop = getLastEventTime(day.events, "STOP") || "-";

    const statusLabel =
      day.is_complete === true
        ? "Complete"
        : day.open_status === "working"
        ? "Working"
        : day.open_status === "on_break"
        ? "On Break"
        : "Incomplete";

    csvRows.push(
      [
        `"${formatDayLabel(day.date).replace(/"/g, '""')}"`,
        `"${firstStart.replace(/"/g, '""')}"`,
        `"${lastStop.replace(/"/g, '""')}"`,
        `"${smartRound(day.break_hours_decimal)}"`,
        `"${smartRound(day.work_hours_decimal)}"`,
        `"${statusLabel.replace(/"/g, '""')}"`,
      ].join(",")
    );
  });

  downloadCsv(csvRows.join("\n"), `timesheet-${currentUser}-${new Date().toISOString().slice(0, 10)}.csv`);
}

function exportDetailedLog() {
  if (!timesheetDays || timesheetDays.length === 0) {
    alert("No data to export");
    return;
  }

  const headers = ["Date", "Action", "Timestamp", "Badge Code"];
  const csvRows = [headers.join(",")];

  timesheetDays.forEach((day) => {
    (day.events || []).forEach((event) => {
      csvRows.push(
        [
          `"${day.date}"`,
          `"${String(event.action || "").replace(/"/g, '""')}"`,
          `"${String(event.timestamp || "").replace(/"/g, '""')}"`,
          `"${String(event.badge_code || "").replace(/"/g, '""')}"`,
        ].join(",")
      );
    });
  });

  downloadCsv(csvRows.join("\n"), `timesheet-events-${currentUser}-${new Date().toISOString().slice(0, 10)}.csv`);
}

function downloadCsv(content, filename) {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const blobUrl = URL.createObjectURL(blob);

  link.setAttribute("href", blobUrl);
  link.setAttribute("download", filename);
  link.style.visibility = "hidden";

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function refreshData() {
  loadTimesheetData();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

window.exportTimesheet = exportTimesheet;
window.exportDetailedLog = exportDetailedLog;
window.refreshData = refreshData;