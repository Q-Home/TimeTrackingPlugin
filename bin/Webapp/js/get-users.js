

const url = "http://173.212.225.50:8000";  // Basis-URL

// Haal de rol van de huidige gebruiker op uit sessionStorage
const role = sessionStorage.getItem('role'); // Verwacht "Admin" of andere rollen (bijv. "User")

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
  const userConfirmed = confirm(
    `Weet je zeker dat je de gebruiker "${username}" wilt verwijderen?`
  );
  if (userConfirmed) {
    deleteUser(username);
  }
};

const confirmBlockUser = function (username) {
  const userConfirmed = confirm(
    `Weet je zeker dat je de gebruiker "${username}" wilt blokeren?`
  );
  if (userConfirmed) {
    blockUser(username);
  }
};

const confirmUnBlockUser = function (username) {
  const userConfirmed = confirm(
    `Weet je zeker dat je de gebruiker "${username}" wilt Deblokeren?`
  );
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

    if (
      username.includes(searchTerm) ||
      firstName.includes(searchTerm) ||
      lastName.includes(searchTerm)
    ) {
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

const init = function () {
  getUsers();

  document.querySelector(".user-list-files").addEventListener("click", (event) => {
    const target = event.target;

    if (target.textContent.trim() === "Print") {
      handleExport("print");
    } else if (target.textContent.trim() === "Excel") {
      handleExport("excel");
    } else if (target.textContent.trim() === "Pdf") {
      handleExport("pdf");
    }
  });

  const searchInput = document.getElementById("exampleInputSearch");
  searchInput.addEventListener("input", debounce((event) => {
    const searchTerm = event.target.value.toLowerCase();
    filterUsers(searchTerm);
  }, 300));
};

document.addEventListener("DOMContentLoaded", function () {
  console.info("DOM geladen");
  init();
});
