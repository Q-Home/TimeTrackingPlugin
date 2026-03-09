// Global variables
let currentUser = null;
let currentPeriod = "week";
let timesheetData = [];
let dailyHoursChart = null;
let hoursBreakdownChart = null;
const currentHost = window.location.hostname;
// Dynamische URL configuratie op basis van omgeving

const url = `http://${currentHost}:5000`;
console.debug("Detected API URL:", url);

// Simple local-time helpers
function formatDateTime(dateTimeString) {
  if (!dateTimeString) return "N/A";
  try {
    const d = new Date(dateTimeString);
    return d.toLocaleString();
  } catch (e) {
    return dateTimeString;
  }
}

function formatDateForFilename(dateObj) {
  try {
    const d = dateObj instanceof Date ? dateObj : new Date(dateObj);
    return d.toISOString().slice(0, 19).replace(/[:T]/g, "-");
  } catch (e) {
    return new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  }
}

function belgiumDateKey(dateTimeString) {
  // fallback: use the local date part (YYYY-MM-DD)
  try {
    const d = new Date(dateTimeString);
    return d.toISOString().slice(0, 10);
  } catch (e) {
    return new Date().toISOString().slice(0, 10);
  }
}

// Get username from URL parameters
function getUsernameFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get("username") || urlParams.get("user");
}

// Initialize page
document.addEventListener("DOMContentLoaded", function () {
  currentUser = getUsernameFromUrl();
  console.log("[DOMContentLoaded] currentUser from URL:", currentUser);
  if (!currentUser) {
    console.error("[DOMContentLoaded] No username provided in URL.");
    showError("No username provided in URL. Please access this page with ?username=<username> parameter.");
    return;
  }
  document.getElementById("user-name").textContent = currentUser;
  document.getElementById("user-id").textContent = currentUser;
  loadTimesheetData();
});

// --- Period selection logic ---
let currentPeriodType = "week"; // 'week' or 'month'
let currentWeek = null;
let currentMonth = null;

function setPeriod(type, skipLoad) {
  currentPeriodType = type;
  currentPeriod = type; // for legacy code
  const btnWeek = document.getElementById("btn-week");
  const btnMonth = document.getElementById("btn-month");
  const weekSelector = document.getElementById("week-selector");
  const monthSelector = document.getElementById("month-selector");
  if (type === "week") {
    btnWeek.classList.add("active");
    btnMonth.classList.remove("active");
    weekSelector.style.display = "";
    monthSelector.style.display = "none";
    fillWeekSelector();
  } else {
    btnWeek.classList.remove("active");
    btnMonth.classList.add("active");
    weekSelector.style.display = "none";
    monthSelector.style.display = "";
    fillMonthSelector();
  }
  updatePeriodLabel();
  if (!skipLoad) loadTimesheetData();
}

function fillWeekSelector() {
  const weekSelector = document.getElementById("week-selector");
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
  // Keep selection if possible
  if (currentWeek && Array.from(weekSelector.options).some((opt) => opt.value === currentWeek)) {
    weekSelector.value = currentWeek;
  } else {
    currentWeek = weekSelector.options[0].value;
    weekSelector.value = currentWeek;
  }
}

function fillMonthSelector() {
  const monthSelector = document.getElementById("month-selector");
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
  // Keep selection if possible
  if (currentMonth && Array.from(monthSelector.options).some((opt) => opt.value === currentMonth)) {
    monthSelector.value = currentMonth;
  } else {
    currentMonth = monthSelector.options[0].value;
    monthSelector.value = currentMonth;
  }
}

function updatePeriodLabel() {
  const label = document.getElementById("period-label");
  if (currentPeriodType === "week") {
    label.textContent = currentWeek.replace("-", " Week ");
  } else {
    const [year, month] = currentMonth.split("-");
    label.textContent = `${getMonthName(parseInt(month) - 1)} ${year}`;
  }
}

// Helper: get week number (ISO)
function getWeekNumber(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
}

// Helper: get number of weeks in a year
function getWeeksInYear(year) {
  const d = new Date(year, 11, 31);
  const week = getWeekNumber(d);
  return week === 1 ? 52 : week;
}

// Helper: get month name
function getMonthName(monthIdx) {
  const months = ["Januari", "Februari", "Maart", "April", "Mei", "Juni", "Juli", "Augustus", "September", "Oktober", "November", "December"];
  return months[monthIdx];
}

// --- Event listeners for period selection ---
document.getElementById("btn-week").addEventListener("click", function () {
  setPeriod("week");
});
document.getElementById("btn-month").addEventListener("click", function () {
  setPeriod("month");
});
document.getElementById("week-selector").addEventListener("change", function (e) {
  currentWeek = e.target.value;
  updatePeriodLabel();
  loadTimesheetData();
});
document.getElementById("month-selector").addEventListener("change", function (e) {
  currentMonth = e.target.value;
  updatePeriodLabel();
  loadTimesheetData();
});

// --- On page load, initialize selectors and data ---
document.addEventListener("DOMContentLoaded", function () {
  currentUser = getUsernameFromUrl();
  console.log("[DOMContentLoaded] currentUser from URL:", currentUser);
  if (!currentUser) {
    console.error("[DOMContentLoaded] No username provided in URL.");
    showError("No username provided in URL. Please access this page with ?username=<username> parameter.");
    return;
  }
  document.getElementById("user-name").textContent = currentUser;
  document.getElementById("user-id").textContent = currentUser;
  setPeriod("week", true); // default to week, don't load data yet
  document.getElementById("week-selector").style.display = "";
  document.getElementById("month-selector").style.display = "none";
  updatePeriodLabel();
  loadTimesheetData();
});

// Load timesheet data
async function loadTimesheetData() {
  try {
    console.log("[loadTimesheetData] Called.");
    showLoading();
    let startDate, endDate;
    if (currentPeriodType === "week") {
      // currentWeek format: YYYY-Wxx
      const [year, week] = currentWeek.split("-W");
      // ISO week: get Monday
      const simple = new Date(year, 0, 1 + (week - 1) * 7);
      const dow = simple.getDay();
      const monday = new Date(simple);
      if (dow <= 4) monday.setDate(simple.getDate() - simple.getDay() + 1);
      else monday.setDate(simple.getDate() + 8 - simple.getDay());
      startDate = new Date(monday);
      endDate = new Date(monday);
      endDate.setDate(startDate.getDate() + 6); // Sunday
      startDate.setHours(0, 0, 0, 0);
      endDate.setHours(23, 59, 59, 999);
      console.log("[loadTimesheetData] Period: week", currentWeek, "startDate:", startDate, "endDate:", endDate);
    } else {
      // currentMonth format: YYYY-MM
      const [year, month] = currentMonth.split("-");
      startDate = new Date(parseInt(year), parseInt(month) - 1, 1, 0, 0, 0, 0);
      endDate = new Date(parseInt(year), parseInt(month), 0, 23, 59, 59, 999); // last day of month
      console.log("[loadTimesheetData] Period: month", currentMonth, "startDate:", startDate, "endDate:", endDate);
    }
    const requestBody = {
      filters: {
        user: currentUser,
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
      },
      limit: 1000,
      sort: { timestamp: 1 },
    };
    console.log("[loadTimesheetData] Fetching timesheet data with:", requestBody);
    const fetchUrl = `${url}/api/v1/badges/search`;
    console.log("[loadTimesheetData] Fetch URL:", fetchUrl);
    let response;
    try {
      response = await fetch(fetchUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify(requestBody),
      });
    } catch (fetchErr) {
      console.error("[loadTimesheetData] Network or CORS error during fetch:", fetchErr, "URL:", fetchUrl);
      showError(`Netwerk- of CORS-fout bij ophalen timesheet data: ${fetchErr} (URL: ${fetchUrl})`);
      return;
    }
    console.log("[loadTimesheetData] Fetch response:", response);
    if (!response.ok) {
      console.error("[loadTimesheetData] HTTP error:", response.status, response.statusText, "URL:", fetchUrl);
      throw new Error(`HTTP ${response.status}: ${response.statusText} (URL: ${fetchUrl})`);
    }
    const data = await response.json();
    console.log("[loadTimesheetData] Received data:", data);
    timesheetData = data.badges || [];
    console.log("[loadTimesheetData] Parsed timesheetData:", timesheetData);
    processTimesheetData();
  } catch (error) {
    console.error("[loadTimesheetData] Error:", error, "API URL:", url);
    showError(`Error loading timesheet data: ${error.message} (API URL: ${url})`);
  }
}

// Process badge data to calculate work hours
function processTimesheetData() {
  console.log("[processTimesheetData] Called. timesheetData:", timesheetData);
  if (timesheetData.length === 0) {
    console.warn("[processTimesheetData] No data.");
    showNoData();
    return;
  }
  const dailyRecords = {};
  let totalHours = 0;
  let totalBreakTime = 0;
  let workingDays = 0;
  // Group badges by Belgium date (YYYY-MM-DD)
  timesheetData.forEach((badge, idx) => {
    const date = belgiumDateKey(badge.timestamp);
    if (!dailyRecords[date]) {
      dailyRecords[date] = {
        date: date,
        badges: [],
        clockIn: null,
        clockOut: null,
        breaks: [],
        totalHours: 0,
        breakTime: 0,
        status: "Incomplete",
      };
    }
    dailyRecords[date].badges.push(badge);
    console.log(`[processTimesheetData] Badge #${idx}:`, badge, "Grouped to", date);
  });
  // Calculate daily hours with break logic
  Object.keys(dailyRecords).forEach((date) => {
    const record = dailyRecords[date];
    const sortedBadges = record.badges.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    let startTime = null;
    let stopTime = null;
    let breakStart = null;
    let breakTime = 0;
    // Find Start and Stop
    sortedBadges.forEach((badge, idx) => {
      const action = badge.action ? badge.action.toLowerCase() : "";
      if (action === "start") {
        if (!startTime) {
          startTime = new Date(badge.timestamp);
          // store ISO timestamp for later formatting to avoid locale parsing issues
          record.clockIn = startTime.toISOString();
          console.log(`[processTimesheetData] [${date}] Start at`, badge.timestamp);
        }
      } else if (action === "stop") {
        stopTime = new Date(badge.timestamp);
        record.clockOut = stopTime.toISOString();
        console.log(`[processTimesheetData] [${date}] Stop at`, badge.timestamp);
      } else if (action === "breakstart") {
        breakStart = new Date(badge.timestamp);
        console.log(`[processTimesheetData] [${date}] BreakStart at`, badge.timestamp);
      } else if (action === "breakend") {
        if (breakStart) {
          const breakEnd = new Date(badge.timestamp);
          const thisBreak = (breakEnd - breakStart) / (1000 * 60 * 60);
          breakTime += thisBreak;
          // store ISO strings for break start/end
          record.breaks.push({ start: breakStart.toISOString(), end: breakEnd.toISOString(), hours: thisBreak });
          console.log(`[processTimesheetData] [${date}] BreakEnd at`, badge.timestamp, "break duration:", thisBreak);
          breakStart = null;
        }
      }
    });
    // Calculate work hours
    if (startTime && stopTime) {
      let workHours = (stopTime - startTime) / (1000 * 60 * 60) - breakTime;
      if (workHours < 0) workHours = 0;
      record.totalHours = workHours;
      record.breakTime = breakTime;
      totalHours += workHours;
      totalBreakTime += breakTime;
      workingDays++;
      record.status = "Complete";
      console.log(`[processTimesheetData] [${date}] Work:`, workHours, "Break:", breakTime);
    } else {
      record.totalHours = 0;
      record.breakTime = breakTime;
      record.status = "Incomplete";
      console.log(`[processTimesheetData] [${date}] Incomplete day. Start or Stop missing.`);
    }
  });
  console.log("[processTimesheetData] dailyRecords:", dailyRecords);
  updateStatistics(totalHours, workingDays, totalBreakTime);
  updateCharts(dailyRecords);
  updateTable(dailyRecords);
  hideLoading();
}

// Globale afrondhulp zodat alle functies dezelfde gebruiken
function smartRound(val) {
  // Altijd afronden op 1 cijfer na de komma
  return (Math.round(val * 10) / 10).toFixed(1);
}

// Update statistics cards
function updateStatistics(totalHours, workingDays, breakTime) {
  console.log("[updateStatistics] totalHours:", totalHours, "workingDays:", workingDays, "breakTime:", breakTime);
  document.getElementById("total-hours").textContent = `${smartRound(totalHours)}h`;
  document.getElementById("working-days").textContent = workingDays;
  document.getElementById("avg-hours").textContent = workingDays > 0 ? `${smartRound(totalHours / workingDays)}h` : "0.0h";
  document.getElementById("break-time").textContent = `${smartRound(breakTime)}h`;
  document.getElementById("last-updated").textContent = formatDateTime(new Date().toISOString());
}

// Update charts
function updateCharts(dailyRecords) {
  console.log("[updateCharts] dailyRecords:", dailyRecords);
  // Check if there is any data to show
  const hasData = Object.values(dailyRecords).some((r) => r.totalHours > 0 || r.breakTime > 0);
  if (!hasData) {
    // Hide charts if no data
    if (dailyHoursChart) {
      dailyHoursChart.destroy();
      dailyHoursChart = null;
    }
    if (hoursBreakdownChart) {
      hoursBreakdownChart.destroy();
      hoursBreakdownChart = null;
    }
    document.getElementById("dailyHoursChart").getContext("2d").clearRect(0, 0, 400, 400);
    document.getElementById("hoursBreakdownChart").getContext("2d").clearRect(0, 0, 400, 400);
    return;
  }
  updateDailyHoursChart(dailyRecords);
  updateHoursBreakdownChart(dailyRecords);
}

// Update daily hours bar chart
function updateDailyHoursChart(dailyRecords) {
  console.log("[updateDailyHoursChart] dailyRecords:", dailyRecords);
  const chartCanvas = document.getElementById("dailyHoursChart");
  chartCanvas.height = 400;
  chartCanvas.width = 400;
  const ctx = chartCanvas.getContext("2d");
  if (dailyHoursChart) {
    dailyHoursChart.destroy();
  }
  // Sort dates chronologically (YYYY-MM-DD) for correct order in chart
  const dates = Object.keys(dailyRecords).sort((a, b) => new Date(a) - new Date(b));
  const hours = dates.map((date) => smartRound(Number(dailyRecords[date].totalHours || 0)));
  const breaks = dates.map((date) => smartRound(Number(dailyRecords[date].breakTime || 0)));
  // Overtime per dag: alles boven 8 uur
  const overtime = dates.map((date) => {
    const h = Number(dailyRecords[date].totalHours || 0);
    return h > 8 ? smartRound(h - 8) : "0.0";
  });
  // Voor de grafiek: normale uren max 8, rest is overtime
  const normalHours = dates.map((date) => {
    const h = Number(dailyRecords[date].totalHours || 0);
    return h > 8 ? "8.0" : smartRound(h);
  });
  const labels = dates.map((date) => new Date(date).toLocaleDateString("nl-NL", { weekday: "short", month: "short", day: "numeric" }));
  console.log("[updateDailyHoursChart] dates:", dates, "hours:", hours, "breaks:", breaks, "labels:", labels);
  dailyHoursChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Normale uren (max 8)",
          data: normalHours,
          backgroundColor: "rgba(54, 162, 235, 0.7)",
          borderColor: "rgba(54, 162, 235, 1)",
          borderWidth: 1,
          stack: "Stack 0",
        },
        {
          label: "Overuren",
          data: overtime,
          backgroundColor: "rgba(255, 99, 132, 0.7)",
          borderColor: "rgba(255, 99, 132, 1)",
          borderWidth: 1,
          stack: "Stack 0",
        },
        {
          label: "Pauze (uren)",
          data: breaks,
          backgroundColor: "rgba(255, 206, 86, 0.7)",
          borderColor: "rgba(255, 206, 86, 1)",
          borderWidth: 1,
          stack: "Stack 0",
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
          min: 0,
          max: 10,
          ticks: {
            stepSize: 1,
            callback: function (value) {
              if (value >= 0 && value <= 10) return value;
              return "";
            },
            autoSkip: false,
          },
          title: {
            display: true,
            text: "Uren",
          },
        },
      },
    },
  });
}

// Update hours breakdown pie chart
function updateHoursBreakdownChart(dailyRecords) {
  console.log("[updateHoursBreakdownChart] dailyRecords:", dailyRecords);
  const chartCanvas = document.getElementById("hoursBreakdownChart");
  chartCanvas.height = 400;
  chartCanvas.width = 400;
  const ctx = chartCanvas.getContext("2d");
  if (hoursBreakdownChart) {
    hoursBreakdownChart.destroy();
  }
  const totalHours = Object.values(dailyRecords).reduce((sum, record) => sum + record.totalHours, 0);
  const standardWorkHours = Object.keys(dailyRecords).length * 8; // Assuming 8h work day
  const overtime = Math.max(0, totalHours - standardWorkHours);
  const regular = Math.min(totalHours, standardWorkHours);
  console.log("[updateHoursBreakdownChart] totalHours:", totalHours, "standardWorkHours:", standardWorkHours, "overtime:", overtime, "regular:", regular);
  // Pie chart: afgerond
  const pieData = [smartRound(regular), smartRound(overtime), smartRound(Math.max(0, standardWorkHours - totalHours))];
  hoursBreakdownChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Regular Hours", "Overtime", "Missing Hours"],
      datasets: [
        {
          data: pieData,
          backgroundColor: ["rgba(75, 192, 192, 0.6)", "rgba(255, 206, 86, 0.6)", "rgba(255, 99, 132, 0.6)"],
          borderColor: ["rgba(75, 192, 192, 1)", "rgba(255, 206, 86, 1)", "rgba(255, 99, 132, 1)"],
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

// Update detailed table
function updateTable(dailyRecords) {
  console.log("[updateTable] dailyRecords:", dailyRecords);
  const tbody = document.getElementById("timesheet-tbody");
  tbody.innerHTML = "";
  const sortedDates = Object.keys(dailyRecords).sort((a, b) => new Date(b) - new Date(a));
  sortedDates.forEach((date) => {
    const record = dailyRecords[date];
    const row = document.createElement("tr");
    const statusClass = record.status === "Complete" ? "success" : record.status === "In Progress" ? "warning" : "danger";
    row.innerHTML = `
      <td>${new Date(date).toLocaleDateString("nl-NL", { weekday: "short", year: "numeric", month: "short", day: "numeric" })}</td>
      <td>${record.clockIn ? new Date(record.clockIn).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" }) : "-"}</td>
      <td>${record.clockOut ? new Date(record.clockOut).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" }) : "-"}</td>
  <td>${smartRound(Number(record.breakTime))}h</td>
  <td><strong>${smartRound(Number(record.totalHours))}h</strong></td>
      <td><span class="badge badge-${statusClass}">${record.status}</span></td>
    `;
    tbody.appendChild(row);
    console.log(`[updateTable] Row for ${date}:`, record);
  });
  document.getElementById("timesheet-table").classList.remove("d-none");
}

// UI Helper functions
function showLoading() {
  console.log("[showLoading] Show loading spinner/table.");
  document.getElementById("table-loading").classList.remove("d-none");
  document.getElementById("timesheet-table").classList.add("d-none");
  document.getElementById("no-data").classList.add("d-none");
  document.getElementById("table-error").classList.add("d-none");
}

function hideLoading() {
  console.log("[hideLoading] Hide loading spinner/table.");
  document.getElementById("table-loading").classList.add("d-none");
}

function showNoData() {
  console.warn("[showNoData] No data to show.");
  hideLoading();
  document.getElementById("no-data").classList.remove("d-none");
  updateStatistics(0, 0, 0);
}

function showError(message) {
  console.error("[showError]", message);
  hideLoading();
  const errorDiv = document.getElementById("table-error");
  errorDiv.innerHTML = `
    <div class="alert alert-danger" role="alert">
      <i class="las la-exclamation-triangle"></i> ${message}
    </div>
  `;
  errorDiv.classList.remove("d-none");
}

// Export functions
function exportTimesheet() {
  if (!timesheetData || timesheetData.length === 0) {
    console.warn("[exportTimesheet] No data to export");
    alert("No data to export");
    return;
  }
  // Implementation for timesheet export
  console.log("[exportTimesheet] Exporting timesheet for", currentUser);
}

function exportDetailedLog() {
  if (!timesheetData || timesheetData.length === 0) {
    console.warn("[exportDetailedLog] No data to export");
    alert("No data to export");
    return;
  }
  // Implementation for detailed log export
  console.log("[exportDetailedLog] Exporting detailed log for", currentUser);
}

function refreshData() {
  console.log("[refreshData] Refreshing data...");
  loadTimesheetData();
}
