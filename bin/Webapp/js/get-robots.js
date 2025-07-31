document.addEventListener("DOMContentLoaded", function () {
   
  const url = process.env.URL || 'http://127.0.0.1:5000';  // Basis-URL
    let robots = [];
    let currentPage = 1;
    const itemsPerPage = 20;
    let filteredRobots = [];
  
    const tableBody = document.querySelector(".js-users");
    const searchInput = document.getElementById("exampleInputSearch");
  
    searchInput.addEventListener("input", debounce((event) => {
      const searchTerm = event.target.value.toLowerCase();
      filterUsers(searchTerm);
    }, 300));

    function addEditListeners() {
      const editButtons = document.querySelectorAll(".edit-robot");
    
      editButtons.forEach((button) => {
        button.addEventListener("click", (event) => {
          event.preventDefault(); // Voorkom standaard navigatiegedrag
          const macAddress = button.getAttribute("data-mac");
          // Navigeer naar robot-page.html met het MAC-adres als queryparameter
          window.location.href = `robot-page.html?mac=${encodeURIComponent(macAddress)}`;
        });
      });
    }
    
  
    async function fetchRobots() {
      try {
        const response = await fetch(`${url}/api/v1/robots/`);
        if (!response.ok) throw new Error("Fout bij ophalen robots");
  
        const data = await response.json();
        console.log("Response JSON:", data);
  
        if (!data.robots || !Array.isArray(data.robots)) {
          throw new Error("Invalid response format: 'robots' is not an array");
        }
  
        robots = data.robots;
        filteredRobots = [...robots];
        renderTable(filteredRobots);
      } catch (error) {
        console.error("Er is een fout opgetreden:", error);
      }
    }
  
    function renderTable(data) {
      tableBody.innerHTML = "";
      const start = (currentPage - 1) * itemsPerPage;
      const end = start + itemsPerPage;
      const pageData = data.slice(start, end);
    
      pageData.forEach((robot) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td class="text-center"><img class="img-fluid avatar-40" src="images/conciergerobot.jpg" alt="profile"></td>
          <td>${robot.nickname}</td>
          <td>${robot.mac_address}</td>
          <td>${robot.location}</td>
          <td>${robot.robot_type}</td>
          <td><span class="badge ${robot.status === "Online" ? "iq-bg-primary" : "iq-bg-danger"}">${robot.status}</span></td>
          <td>
            <div class="d-flex align-items-center list-user-action">
              <a class="iq-bg-primary edit-robot" data-mac="${robot.mac_address}" data-toggle="tooltip" data-placement="top" title="Edit" href="#"><i class="ri-pencil-line"></i></a>
            </div>
          </td>
        `;
        tableBody.appendChild(row);
      });
    
      addEditListeners(); // Voeg event listeners toe na het maken van de rijen
      renderPagination(data.length);
    }
    
     // ${robot.status === "Online" ? `<a class="iq-bg-primary" data-toggle="tooltip" data-placement="top" title="Turn off" href="#">🚫</a>` : ""}    ---> knop voor offline te maken
  
    function renderPagination(totalItems) {
      const totalPages = Math.ceil(totalItems / itemsPerPage);
      const paginationContainer = document.querySelector(".pagination");
  
      if (!paginationContainer) {
        const pagination = document.createElement("div");
        pagination.className = "pagination mt-4";
        tableBody.parentElement.appendChild(pagination);
      }
  
      paginationContainer.innerHTML = "";
  
      for (let i = 1; i <= totalPages; i++) {
        const pageButton = document.createElement("button");
        pageButton.className = "btn btn-primary mx-1";
        pageButton.textContent = i;
        pageButton.disabled = i === currentPage;
  
        pageButton.addEventListener("click", () => {
          currentPage = i;
          renderTable(filteredRobots);
        });
  
        paginationContainer.appendChild(pageButton);
      }
    }
  
    function filterUsers(searchTerm) {
      filteredRobots = robots.filter((robot) => {
        return (
          robot.nickname.toLowerCase().includes(searchTerm) ||
          robot.mac_address.toLowerCase().includes(searchTerm) ||
          robot.location.toLowerCase().includes(searchTerm) ||
          robot.robot_type.toLowerCase().includes(searchTerm) ||
          robot.status.toLowerCase().includes(searchTerm)
        );
      });
      renderTable(filteredRobots);
    }
  
    function debounce(func, delay) {
      let timer;
      return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => func.apply(this, args), delay);
      };
    }
  
    fetchRobots();
  });
  