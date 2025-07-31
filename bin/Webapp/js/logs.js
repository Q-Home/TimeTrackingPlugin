document.addEventListener("DOMContentLoaded", () => {
  // const url = "http://173.212.225.50:8000"; process.env.URL || "http://173.212.225.50:8000"; // Basis-URL
  const url = "http://173.212.225.50:8000";
  const logsEndpoint = url + "/api/v1/transactie/all/"; // Endpoint om logs op te halen
  const tableBody = document.querySelector(".js-Logs");
  const paginationContainer = document.getElementById("pagination");

  const logsPerPage = 20; // Aantal logs per pagina
  let currentPage = 1;
  let logsData = [];

  // Event listener voor zoekbalk en filter
  const searchInput = document.getElementById("exampleInputSearch");
  const logTypeFilter = document.getElementById("logTypeFilter");

  searchInput.addEventListener(
    "input",
    debounce(() => filterLogs(), 300)
  );
  logTypeFilter.addEventListener(
    "change",
    debounce(() => filterLogs(), 300)
  );

  // Functie om logs te filteren
  function filterLogs() {
    const searchTerm = searchInput.value.toLowerCase();
    const selectedType = logTypeFilter.value;

    const filteredLogs = logsData.filter((log) => {
      const matchesSearch = log.message.toLowerCase().includes(searchTerm);
      const matchesType = selectedType === "all" || log.type.toLowerCase() === selectedType;
      return matchesSearch && matchesType;
    });

    renderLogs(filteredLogs);
  }

  // Logs ophalen van de API
  async function fetchLogs() {
    try {
      const response = await fetch(logsEndpoint);
      if (!response.ok) throw new Error("Fout bij het ophalen van logs");

      const data = await response.json();
      console.debug("Logs succesvol opgehaald:", data); // Debugging
      logsData = data.transactions || [];
      renderLogs(logsData); // We renderen de logs nadat ze opgehaald zijn
    } catch (error) {
      console.error("Er is een fout opgetreden:", error);
      tableBody.innerHTML = "<tr><td colspan='3'>Fout bij het laden van logs. Probeer later opnieuw.</td></tr>";
    }
  }

  // Logs weergeven voor de huidige pagina
  function renderLogs(filteredLogs) {
    tableBody.innerHTML = "";

    if (filteredLogs.length === 0) {
      tableBody.innerHTML = "<tr><td colspan='5'>Geen logs beschikbaar.</td></tr>";
      return;
    }

    const startIndex = (currentPage - 1) * logsPerPage;
    const endIndex = Math.min(startIndex + logsPerPage, filteredLogs.length);

    filteredLogs.slice(startIndex, endIndex).forEach((log) => {
      // Zet duur (in seconden) om naar "uur min" formaat
      let duurText = "0min";
      if (log.duur && !isNaN(log.duur)) {
        const totalMinutes = Math.floor(log.duur / 60);
        const hours = Math.floor(totalMinutes / 60);
        const minutes = totalMinutes % 60;
        duurText = hours > 0 ? `${hours}u ${minutes}min` : `${minutes}min`;
      }

      // Formatteer timestamp naar "dd-mm-yyyy HH:MM"
      let formattedTimestamp = "";
      if (log.timestamp) {
        const date = new Date(log.timestamp);
        const day = String(date.getDate()).padStart(2, "0");
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const year = date.getFullYear();
        const hours = String(date.getHours()).padStart(2, "0");
        const minutes = String(date.getMinutes()).padStart(2, "0");
        formattedTimestamp = `${day}-${month}-${year} ${hours}:${minutes}`;
      }

      const row = `
        <tr>
          <td>${log.user || ""}</td>
          <td>${duurText}</td>
          <td>${log.verbruik || ""}</td>
          <td>${log.laadpaalId || ""}</td>
          <td>${log.kostprijs || "0"}€</td>
          <td>${formattedTimestamp}</td>
        </tr>
      `;
      tableBody.insertAdjacentHTML("beforeend", row);
    });

    renderPagination(filteredLogs);
  }

  // Paginering weergeven
  function renderPagination(filteredLogs) {
    paginationContainer.innerHTML = "";

    const totalPages = Math.ceil(filteredLogs.length / logsPerPage);
    if (totalPages <= 1) return;

    const prevButton = document.createElement("li");
    prevButton.classList.add("page-item", currentPage === 1 && "disabled");
    prevButton.innerHTML = `<span class="page-link">Previous</span>`;
    if (currentPage > 1) prevButton.onclick = () => changePage(currentPage - 1);
    paginationContainer.appendChild(prevButton);

    for (let i = 1; i <= totalPages; i++) {
      const pageButton = document.createElement("li");
      pageButton.classList.add("page-item", i === currentPage && "active");
      pageButton.innerHTML = `<a class="page-link" href="#">${i}</a>`;
      pageButton.onclick = () => changePage(i);
      paginationContainer.appendChild(pageButton);
    }

    const nextButton = document.createElement("li");
    nextButton.classList.add("page-item", currentPage === totalPages && "disabled");
    nextButton.innerHTML = `<span class="page-link">Next</span>`;
    if (currentPage < totalPages) nextButton.onclick = () => changePage(currentPage + 1);
    paginationContainer.appendChild(nextButton);
  }

  // Verander van pagina
  function changePage(page) {
    const totalPages = Math.ceil(logsData.length / logsPerPage);
    if (page >= 1 && page <= totalPages) {
      currentPage = page;
      filterLogs();
    }
  }

  // Hulp functie voor debounce (om te voorkomen dat de functie te snel achter elkaar wordt aangeroepen)
  function debounce(func, delay) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => func.apply(this, args), delay);
    };
  }

  fetchLogs();
});
