// Global variables
let currentUser = null;
let currentPeriod = 'week';
let timesheetData = [];
let dailyHoursChart = null;
let hoursBreakdownChart = null;

// API URL configuration (same as other pages)
function getApiUrl() {
  const currentPort = window.location.port;
  const currentHost = window.location.hostname;
  
  if (currentPort === '8080') {
    return "http://172.28.0.15:5000";
  }
  
  if (currentHost === 'localhost' || currentHost === '127.0.0.1') {
    return "http://localhost:5000";
  }
  
  if (currentHost.match(/^\d+\.\d+\.\d+\.\d+$/)) {
    return `http://${currentHost}:5000`;
  }
  
  return "http://192.168.0.196:5000";
}

const apiUrl = getApiUrl();

// Get username from URL parameters
function getUsernameFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('username') || urlParams.get('user');
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
  currentUser = getUsernameFromUrl();
  
  if (!currentUser) {
    showError('No username provided in URL. Please access this page with ?username=<username> parameter.');
    return;
  }
  
  console.log('Loading timesheet for user:', currentUser);
  document.getElementById('user-name').textContent = currentUser;
  document.getElementById('user-id').textContent = currentUser;
  
  loadTimesheetData();
});

// Set time period
function setPeriod(period) {
  currentPeriod = period;
  
  // Update button states
  document.getElementById('btn-week').classList.remove('active');
  document.getElementById('btn-month').classList.remove('active');
  document.getElementById(`btn-${period}`).classList.add('active');
  
  loadTimesheetData();
}

// Load timesheet data
async function loadTimesheetData() {
  try {
    showLoading();
    
    const endDate = new Date();
    const startDate = new Date();
    
    if (currentPeriod === 'week') {
      startDate.setDate(endDate.getDate() - 7);
    } else {
      startDate.setMonth(endDate.getMonth() - 1);
    }
    
    const requestBody = {
      filters: {
        user: currentUser,
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString()
      },
      limit: 1000,
      sort: { timestamp: 1 }
    };
    
    console.log('Fetching timesheet data:', requestBody);
    
    const response = await fetch(`${apiUrl}/api/v1/badges/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('Received timesheet data:', data);
    
    timesheetData = data.badges || [];
    processTimesheetData();
    
  } catch (error) {
    console.error('Error loading timesheet data:', error);
    showError(`Error loading timesheet data: ${error.message}`);
  }
}

// Process badge data to calculate work hours
function processTimesheetData() {
  if (timesheetData.length === 0) {
    showNoData();
    return;
  }
  
  const dailyRecords = {};
  let totalHours = 0;
  let totalBreakTime = 0;
  let workingDays = 0;
  
  // Group badges by date
  timesheetData.forEach(badge => {
    const date = new Date(badge.timestamp).toDateString();
    
    if (!dailyRecords[date]) {
      dailyRecords[date] = {
        date: date,
        badges: [],
        clockIn: null,
        clockOut: null,
        breaks: [],
        totalHours: 0,
        breakTime: 0,
        status: 'Incomplete'
      };
    }
    
    dailyRecords[date].badges.push(badge);
  });
  
  // Calculate daily hours
  Object.keys(dailyRecords).forEach(date => {
    const record = dailyRecords[date];
    const sortedBadges = record.badges.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    
    let workingSessions = [];
    let currentStart = null;
    
    sortedBadges.forEach(badge => {
      if (badge.action === 'START' || badge.action === 'RETURN') {
        if (!currentStart) {
          currentStart = new Date(badge.timestamp);
          if (!record.clockIn) {
            record.clockIn = badge.timestamp;
          }
        }
      } else if (badge.action === 'STOP' || badge.action === 'BREAK') {
        if (currentStart) {
          const endTime = new Date(badge.timestamp);
          const sessionHours = (endTime - currentStart) / (1000 * 60 * 60);
          
          if (badge.action === 'STOP') {
            workingSessions.push(sessionHours);
            record.clockOut = badge.timestamp;
            currentStart = null;
          } else if (badge.action === 'BREAK') {
            workingSessions.push(sessionHours);
            currentStart = null;
          }
        }
      }
    });
    
    record.totalHours = workingSessions.reduce((sum, hours) => sum + hours, 0);
    
    if (record.totalHours > 0) {
      totalHours += record.totalHours;
      workingDays++;
      record.status = record.clockOut ? 'Complete' : 'In Progress';
    }
  });
  
  updateStatistics(totalHours, workingDays, totalBreakTime);
  updateCharts(dailyRecords);
  updateTable(dailyRecords);
  hideLoading();
}

// Update statistics cards
function updateStatistics(totalHours, workingDays, breakTime) {
  document.getElementById('total-hours').textContent = `${totalHours.toFixed(1)}h`;
  document.getElementById('working-days').textContent = workingDays;
  document.getElementById('avg-hours').textContent = workingDays > 0 ? `${(totalHours / workingDays).toFixed(1)}h` : '0.0h';
  document.getElementById('break-time').textContent = `${breakTime.toFixed(1)}h`;
  document.getElementById('last-updated').textContent = new Date().toLocaleString();
}

// Update charts
function updateCharts(dailyRecords) {
  updateDailyHoursChart(dailyRecords);
  updateHoursBreakdownChart(dailyRecords);
}

// Update daily hours bar chart
function updateDailyHoursChart(dailyRecords) {
  const ctx = document.getElementById('dailyHoursChart').getContext('2d');
  
  if (dailyHoursChart) {
    dailyHoursChart.destroy();
  }
  
  const dates = Object.keys(dailyRecords).sort();
  const hours = dates.map(date => dailyRecords[date].totalHours);
  const labels = dates.map(date => new Date(date).toLocaleDateString('nl-NL', { weekday: 'short', month: 'short', day: 'numeric' }));
  
  dailyHoursChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Hours Worked',
        data: hours,
        backgroundColor: 'rgba(54, 162, 235, 0.6)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: 'Hours'
          }
        }
      }
    }
  });
}

// Update hours breakdown pie chart
function updateHoursBreakdownChart(dailyRecords) {
  const ctx = document.getElementById('hoursBreakdownChart').getContext('2d');
  
  if (hoursBreakdownChart) {
    hoursBreakdownChart.destroy();
  }
  
  const totalHours = Object.values(dailyRecords).reduce((sum, record) => sum + record.totalHours, 0);
  const standardWorkHours = Object.keys(dailyRecords).length * 8; // Assuming 8h work day
  const overtime = Math.max(0, totalHours - standardWorkHours);
  const regular = Math.min(totalHours, standardWorkHours);
  
  hoursBreakdownChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Regular Hours', 'Overtime', 'Missing Hours'],
      datasets: [{
        data: [regular, overtime, Math.max(0, standardWorkHours - totalHours)],
        backgroundColor: [
          'rgba(75, 192, 192, 0.6)',
          'rgba(255, 206, 86, 0.6)',
          'rgba(255, 99, 132, 0.6)'
        ],
        borderColor: [
          'rgba(75, 192, 192, 1)',
          'rgba(255, 206, 86, 1)',
          'rgba(255, 99, 132, 1)'
        ],
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true
    }
  });
}

// Update detailed table
function updateTable(dailyRecords) {
  const tbody = document.getElementById('timesheet-tbody');
  tbody.innerHTML = '';
  
  const sortedDates = Object.keys(dailyRecords).sort((a, b) => new Date(b) - new Date(a));
  
  sortedDates.forEach(date => {
    const record = dailyRecords[date];
    const row = document.createElement('tr');
    
    const statusClass = record.status === 'Complete' ? 'success' : 
                       record.status === 'In Progress' ? 'warning' : 'danger';
    
    row.innerHTML = `
      <td>${new Date(date).toLocaleDateString('nl-NL', { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' })}</td>
      <td>${record.clockIn ? new Date(record.clockIn).toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' }) : '-'}</td>
      <td>${record.clockOut ? new Date(record.clockOut).toLocaleTimeString('nl-NL', { hour: '2-digit', minute: '2-digit' }) : '-'}</td>
      <td>${record.breakTime.toFixed(1)}h</td>
      <td><strong>${record.totalHours.toFixed(1)}h</strong></td>
      <td><span class="badge badge-${statusClass}">${record.status}</span></td>
    `;
    
    tbody.appendChild(row);
  });
  
  document.getElementById('timesheet-table').classList.remove('d-none');
}

// UI Helper functions
function showLoading() {
  document.getElementById('table-loading').classList.remove('d-none');
  document.getElementById('timesheet-table').classList.add('d-none');
  document.getElementById('no-data').classList.add('d-none');
  document.getElementById('table-error').classList.add('d-none');
}

function hideLoading() {
  document.getElementById('table-loading').classList.add('d-none');
}

function showNoData() {
  hideLoading();
  document.getElementById('no-data').classList.remove('d-none');
  updateStatistics(0, 0, 0);
}

function showError(message) {
  hideLoading();
  const errorDiv = document.getElementById('table-error');
  errorDiv.innerHTML = `
    <div class="alert alert-danger" role="alert">
      <i class="las la-exclamation-triangle"></i> ${message}
    </div>
  `;
  errorDiv.classList.remove('d-none');
}

// Export functions
function exportTimesheet() {
  if (!timesheetData || timesheetData.length === 0) {
    alert('No data to export');
    return;
  }
  
  // Implementation for timesheet export
  console.log('Exporting timesheet for', currentUser);
}

function exportDetailedLog() {
  if (!timesheetData || timesheetData.length === 0) {
    alert('No data to export');
    return;
  }
  
  // Implementation for detailed log export
  console.log('Exporting detailed log for', currentUser);
}

function refreshData() {
  loadTimesheetData();
}