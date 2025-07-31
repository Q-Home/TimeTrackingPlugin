document.addEventListener("DOMContentLoaded", async () => {
  const apiUrl = 'http://192.168.88.100:5000/api/v1'; // Basis-URL van de backend
  let cpuData = []; // Opslag voor CPU-gebruik per tijd
  let ramData = []; // Opslag voor RAM-gebruik per tijd
  let netUploadData = []; // Opslag voor CPU-gebruik per tijd
  let netDownloadData = []; // Opslag voor RAM-gebruik per tijd
  let timestampData = []; // Opslag voor tijdstempels

  // Haal online robots op
  async function fetchOnlineRobots() {
    try {
      const response = await fetch(`${apiUrl}/robots/online`);
      if (!response.ok) {
        throw new Error("Failed to fetch online robots.");
      }
      const robots = await response.json();
      console.log("Online robots:", robots);
      updateOnlineRobots(robots);
      updateRobotCount(robots.length); // Update het aantal robots
    } catch (error) {
      console.error("Error fetching online robots:", error);
    }
  }
  // Update het aantal online robots
  function updateRobotCount(count) {
    const robotCountElement = document.getElementById("robots");
    if (robotCountElement) {
      robotCountElement.textContent = count; // Toon het aantal robots
    }
  }

  // Update online robots in de HTML
  function updateOnlineRobots(robots) {
    const container = document.querySelector(".row.content-body > .col-lg-12");
    container.innerHTML = ""; // Reset de inhoud

    robots.forEach((robot) => {
      const robotCard = `
          <div class="col-sm-6 col-md-6 col-lg-3">
            <div class="iq-card iq-card-block iq-card-stretch iq-card-height">
              <div class="iq-card-body">
                <div class="text-center">
                  <img src="images/${robot.robot_type.toLowerCase()}.png" alt="${robot.type}" style="height: 200px;">
                </div>
                <div class="mt-4">
                  <h4 class="text-black text-uppercase">${robot.nickname}</h4>
                  <h5 class="text-black text-uppercase">${robot.mac_address}</h5>
                </div>
                <div class="text-right" style="margin-top: 20px;">
                  <a href="robot-page.html?mac=${encodeURIComponent(robot.mac_address)}" class="btn btn-primary">Meer info</a>
                </div>
              </div>
            </div>
          </div>
        `;
      container.insertAdjacentHTML("beforeend", robotCard);
    });
  }

  // Haal serverstatistieken op
  async function fetchServerStats() {
    try {
        const response = await fetch(`${apiUrl}/server-stats/`);
        if (!response.ok) {
          throw new Error("Failed to fetch server stats.");
        }
        const stats = await response.json();
        updateServerStats(stats);
      } catch (error) {
        console.error("Error fetching server stats:", error);
      }
    try {
      const response = await fetch(`${apiUrl}/server-stats/all/`);
      if (!response.ok) {
        throw new Error("Failed to fetch server stats.");
      }
      const stats = await response.json();
      
      updateCharts(stats); // Update grafieken met de opgehaalde stats
    } catch (error) {
      console.error("Error fetching server stats:", error);
    }
  }

  // Update serverstatistieken in de HTML
  function updateServerStats(stats) {
    // CPU-statistieken bijwerken
    document.querySelector("#cpu-usage").textContent = `${stats.cpu}%`; // Laat alleen de eerste stat zien
    document.querySelector("#cpu-progress-span").style.width = `${stats.cpu}%`;

    // RAM-statistieken bijwerken
    document.querySelector("#ram-usage").textContent = `${stats.ram}%`; // Laat alleen de eerste stat zien
    document.querySelector("#ram-progress-span").style.width = `${stats.ram}%`;

    // Schijfstatistieken bijwerken
    document.querySelector("#disk-usage").textContent = `${stats.disk}GB`;
    document.querySelector("#disk-progress-span").style.width = `${stats.disk_usage}%`;

    // Services-statistieken bijwerken
    document.querySelector("#services-usage").textContent = `${stats.net_upload_speed} KB/s`;
    document.querySelector("#services-progress-span").style.width = `${stats.net_upload_speed}%`;
  }

  // Haal de server-statistieken op en werk de grafieken bij
  async function fetchServerStatsPeriodically() {
    try {
      const response = await fetch("http://127.0.0.1:5000/api/v1/server-stats/all/");
      if (!response.ok) {
        throw new Error("Failed to fetch server stats.");
      }
      const stats = await response.json();

      // Werk de grafieken bij met de nieuwe data
      updateCharts(stats);
    } catch (error) {
      console.error("Error fetching server stats:", error);
    }
  }

  function updateCharts(stats) {
    // Log de ontvangen serverstatistieken
    // Log de ontvangen serverstatistieken
    console.log("Fetched server stats:", stats);

    // Controleer of we een array hebben ontvangen
    if (stats && Array.isArray(stats)) {
      // Voeg de nieuwe waarden toe aan de respectieve arrays
      stats.forEach((stat) => {
        cpuData.push(stat.cpu); // Voeg CPU-gebruik toe
        ramData.push(stat.ram); // Voeg RAM-gebruik toe
        netUploadData.push(stat.net_upload_speed); // Voeg net_upload_speed toe
        netDownloadData.push(stat.net_download_speed); // Voeg net_download_speed toe
        timestampData.push(formatTimestamp(new Date(stat.timestamp))); // Voeg tijdstempel toe
      });

      // Limiteer het aantal weergegeven datapunten tot de laatste 10 minuten
      if (cpuData.length > 10) {
        cpuData.shift(); // Verwijder de oudste CPU-data
        ramData.shift(); // Verwijder de oudste RAM-data
        netUploadData.shift(); // Verwijder de oudste net_upload_speed data
        netDownloadData.shift(); // Verwijder de oudste net_download_speed data
        timestampData.shift(); // Verwijder de oudste tijdstempel
      }

      // Verwijder dubbele tijdstempels door een Set te gebruiken
      const uniqueTimestamps = [...new Set(timestampData)];

      // Beperk de categorieën op de X-as tot maximaal 10 en unieke tijdstempels
      const xAxisCategories = uniqueTimestamps.slice(-10); // Beperk tot de laatste 10 unieke tijdstempels

      // Maak een filterfunctie om de juiste CPU, RAM, net_upload_speed en net_download_speed te verkrijgen die overeenkomen met de unieke tijdstempels
      const filteredCpuData = [];
      const filteredRamData = [];
      const filteredNetUploadData = [];
      const filteredNetDownloadData = [];

      // Filter de CPU, RAM, net_upload_speed en net_download_speed gegevens op basis van de unieke tijdstempels
      xAxisCategories.forEach((timestamp) => {
        const index = timestampData.indexOf(timestamp); // Zoek de index van de tijdstempel
        if (index !== -1) {
          filteredCpuData.push(cpuData[index]); // Voeg de bijbehorende CPU waarde toe
          filteredRamData.push(ramData[index]); // Voeg de bijbehorende RAM waarde toe
          filteredNetUploadData.push(netUploadData[index]); // Voeg de bijbehorende net_upload_speed waarde toe
          filteredNetDownloadData.push(netDownloadData[index]); // Voeg de bijbehorende net_download_speed waarde toe
        }
      });

      // Line Chart voor CPU en RAM (met de gefilterde gegevens)
      var optionsLineChart = {
        chart: {
          height: 350,
          type: "line",
          zoom: { enabled: false },
        },
        colors: ["#4e37b2", "#ff6347"], // Kleuren voor de grafieken
        series: [
          {
            name: "CPU Usage",
            data: filteredCpuData, // Gebruik de gefilterde CPU-data
          },
          {
            name: "RAM Usage",
            data: filteredRamData, // Gebruik de gefilterde RAM-data
          },
        ],
        dataLabels: { enabled: false },
        stroke: { curve: "smooth" },
        grid: {
          row: {
            colors: ["#f3f3f3", "transparent"],
            opacity: 0.5,
          },
        },
        xaxis: {
          categories: xAxisCategories, // Beperk de categorieën op de X-as tot de laatste 10 unieke tijdstempels
        },
        yaxis: {
          title: {
            text: "Usage (%)", // Voeg hier een titel toe voor de Y-as, zoals "CPU/RAM Usage"
          },
          labels: {
            formatter: function (value) {
              return `${value}%`; // Voeg een percentage toe aan de Y-as labels
            },
          },
        },
      };

      var chartLine = new ApexCharts(document.querySelector("#apex-basic"), optionsLineChart);
      chartLine.render();

      // Line Chart voor net_upload_speed en net_download_speed (met de gefilterde gegevens)
      var optionsLineChart2 = {
        chart: {
          height: 350,
          type: "line",
          zoom: { enabled: false },
        },
        colors: ["#28a745", "#dc3545"], // Kleuren voor de grafieken
        series: [
          {
            name: "Net Upload Speed",
            data: filteredNetUploadData, // Gebruik de gefilterde net_upload_speed data
          },
          {
            name: "Net Download Speed",
            data: filteredNetDownloadData, // Gebruik de gefilterde net_download_speed data
          },
        ],
        dataLabels: { enabled: false },
        stroke: { curve: "smooth" },
    
        grid: {
          row: {
            colors: ["#f3f3f3", "transparent"],
            opacity: 0.5,
          },
        },
        xaxis: {
          categories: xAxisCategories, // Beperk de categorieën op de X-as tot de laatste 10 unieke tijdstempels
        },
        yaxis: {
          title: {
            text: "Speed (KB/s)", // Voeg hier een titel toe voor de Y-as, zoals "Net Speed"
          },
          labels: {
            formatter: function (value) {
              return `${value.toFixed(2)} KB/s`; // Voeg een eenheid toe aan de Y-as labels
            },
          },
        },
      };

      var chartLine2 = new ApexCharts(document.querySelector("#apex2"), optionsLineChart2);
      chartLine2.render();
    } else {
      console.error("Expected an array but received:", stats);
    }
  }

  function formatTimestamp(date) {
    // Verkrijg de minuten als het dichtstbijzijnde veelvoud van 10
    const minutes = date.getMinutes();
    const roundedMinutes = Math.floor(minutes / 10) * 10; // Rond af naar het dichtstbijzijnde veelvoud van 10

    // Zet de minuten naar het afgeronde veelvoud van 10 en zet seconden en milliseconden naar 0
    date.setMinutes(roundedMinutes, 0, 0);

    // Formatteer de tijd naar "HH:MM"
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  // Verzamel gegevens elke 10 minuten (600 seconden)
  setInterval(fetchServerStatsPeriodically, 10 * 60 * 1000); // 10 minuten = 10 * 60 * 1000 milliseconden

  // Haal serverstatistieken op en werk grafieken bij
  await fetchServerStats(); // Haal serverstatistieken op
  await fetchOnlineRobots(); // Haal online robots op
});
