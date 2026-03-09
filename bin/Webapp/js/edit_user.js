const urlParams = new URLSearchParams(window.location.search);
const username = urlParams.get("username");

const role = (localStorage.getItem("role") || "").toLowerCase();
const token = localStorage.getItem("access_token");
const hostname = window.location.hostname;
const url = `http://${hostname}:5000`;
const apiUrl = `${url}/api/v1`;

let originalUsername = "";
let originalEmail = "";
let userId = "";

const blockedStatusRadios = document.querySelectorAll('input[name="blockedStatus"]');
const profilePic = document.getElementById("profilePic");
const userDataSubmitButton = document.querySelector(".change-info-btn");
const passwordSubmitButton = document.querySelector(".change-password-btn");

document.addEventListener("DOMContentLoaded", function () {
  if (!token) {
    window.location.href = "/index.html";
    return;
  }

  if (!username) {
    console.error("No username provided in the URL.");
    alert("Geen gebruikersnaam gevonden in de URL.");
    window.location.href = "/users-list.html";
    return;
  }

  initializeBlockedStatusListeners();
  fetchUserData(username);
  bindEvents();
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

function bindEvents() {
  if (userDataSubmitButton) {
    userDataSubmitButton.addEventListener("click", handleUserDataFormSubmit);
  } else {
    console.error("Element with class 'change-info-btn' not found in the DOM.");
  }

  if (passwordSubmitButton) {
    passwordSubmitButton.addEventListener("click", handlePasswordFormSubmit);
  } else {
    console.error("Element with class 'change-password-btn' not found in the DOM.");
  }
}

function initializeBlockedStatusListeners() {
  blockedStatusRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      if (profilePic) {
        profilePic.src =
          radio.value === "true" ? "images/user/11.png" : "images/user/11_green.png";
      }
    });
  });
}

async function fetchUserData(targetUsername) {
  try {
    const response = await fetch(`${apiUrl}/users/${encodeURIComponent(targetUsername)}`, {
      method: "GET",
      headers: authHeaders(false),
    });

    if (handleAuthError(response)) return;

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || `HTTP ${response.status}`);
    }

    const data = result?.data || result;

    originalUsername = data.username || "";
    originalEmail = data.email || "";
    userId = data.user_id || "";

    setValue("uname", originalUsername);
    setValue("fname", data.first_name || "");
    setValue("lname", data.last_name || "");
    setValue("cname", data.company_name || "");
    setValue("email", originalEmail);

    const roleSelect = document.getElementById("selectuserrole");
    if (roleSelect) {
      roleSelect.value = data.user_role || "user";
      if (role !== "admin") {
        roleSelect.disabled = true;
      }
    }

    const blockedStatus = data.blocked ? "true" : "false";
    blockedStatusRadios.forEach((radio) => {
      radio.checked = radio.value === blockedStatus;

      if (role !== "admin") {
        radio.disabled = true;
      }
    });

    if (profilePic) {
      profilePic.src =
        blockedStatus === "true" ? "images/user/11.png" : "images/user/11_green.png";
    }
  } catch (error) {
    console.error("Error fetching user data:", error);
    alert(`Kon gebruikersgegevens niet ophalen: ${error.message}`);
  }
}

async function handleUserDataFormSubmit(event) {
  event.preventDefault();

  if (role !== "admin") {
    alert("Alleen admins mogen gebruikersgegevens wijzigen.");
    return;
  }

  const currentUsername = (document.getElementById("uname")?.value || "").trim().toLowerCase();
  const currentEmail = (document.getElementById("email")?.value || "").trim();

  if (!currentUsername || !currentEmail) {
    alert("Gebruikersnaam en e-mail mogen niet leeg zijn.");
    return;
  }

  try {
    if (currentUsername !== originalUsername) {
      const isUsernameTaken = await checkUsernameUnique(currentUsername);
      if (isUsernameTaken) {
        alert("Gebruikersnaam is al in gebruik.");
        return;
      }
    }

    if (currentEmail !== originalEmail) {
      const isEmailTaken = await checkEmailUnique(currentEmail);
      if (isEmailTaken) {
        alert("E-mailadres is al in gebruik.");
        return;
      }
    }

    const roleSelect = document.getElementById("selectuserrole");
    const blockedRadio = document.querySelector('input[name="blockedStatus"]:checked');

    const userData = {
      username: currentUsername,
      first_name: (document.getElementById("fname")?.value || "").trim(),
      last_name: (document.getElementById("lname")?.value || "").trim(),
      company_name: (document.getElementById("cname")?.value || "").trim(),
      email: currentEmail,
      user_role: roleSelect ? roleSelect.value : "user",
      blocked: blockedRadio ? blockedRadio.value === "true" : false,
    };

    const response = await fetch(`${apiUrl}/users/${encodeURIComponent(userId)}`, {
      method: "PUT",
      headers: authHeaders(true),
      body: JSON.stringify(userData),
    });

    if (handleAuthError(response)) return;

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || "Failed to update user data.");
    }

    alert(result.message || "Gebruikersgegevens succesvol bijgewerkt.");

    originalUsername = currentUsername;
    originalEmail = currentEmail;

    window.location.href = "/users-list.html";
  } catch (error) {
    console.error("Error during user data submission:", error);
    alert(error.message || "Er is een fout opgetreden bij het opslaan.");
  }
}

async function checkUsernameUnique(usernameToCheck) {
  try {
    const response = await fetch(`${apiUrl}/users/${encodeURIComponent(usernameToCheck)}`, {
      method: "GET",
      headers: authHeaders(false),
    });

    if (response.status === 404) {
      return false;
    }

    if (handleAuthError(response)) return true;

    return response.ok;
  } catch (error) {
    console.error("Error checking username uniqueness:", error);
    return false;
  }
}

async function checkEmailUnique(emailToCheck) {
  try {
    const response = await fetch(`${apiUrl}/users/`, {
      method: "GET",
      headers: authHeaders(false),
    });

    if (handleAuthError(response)) return true;

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || "Failed to check email.");
    }

    const users = result?.data?.users || result?.users || [];
    return users.some(
      (user) =>
        (user.email || "").toLowerCase() === emailToCheck.toLowerCase() &&
        (user.username || "").toLowerCase() !== originalUsername.toLowerCase()
    );
  } catch (error) {
    console.error("Error checking email uniqueness:", error);
    return false;
  }
}

async function handlePasswordFormSubmit(event) {
  event.preventDefault();

  if (role !== "admin") {
    alert("Alleen admins mogen wachtwoorden wijzigen.");
    return;
  }

  const password = (document.getElementById("pass")?.value || "").trim();
  const repeatPassword = (document.getElementById("rpass")?.value || "").trim();

  if (!password || !repeatPassword) {
    alert("Wachtwoordvelden mogen niet leeg zijn.");
    return;
  }

  if (password.length < 6) {
    alert("Wachtwoord moet minstens 6 tekens bevatten.");
    return;
  }

  if (password !== repeatPassword) {
    alert("Wachtwoorden komen niet overeen.");
    return;
  }

  try {
    const response = await fetch(`${apiUrl}/users/${encodeURIComponent(userId)}/password`, {
      method: "PUT",
      headers: authHeaders(true),
      body: JSON.stringify({ password }),
    });

    if (handleAuthError(response)) return;

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || result.message || "Failed to update password.");
    }

    alert(result.message || "Wachtwoord succesvol bijgewerkt.");

    setValue("pass", "");
    setValue("rpass", "");
  } catch (error) {
    console.error("Error updating password:", error);
    alert(error.message || "Er is een fout opgetreden bij het wijzigen van het wachtwoord.");
  }
}

function setValue(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.value = value;
  }
}