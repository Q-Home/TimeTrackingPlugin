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
let originalExtraFields = {};

const blockedStatusRadios = document.querySelectorAll('input[name="blockedStatus"]');
const profilePic = document.getElementById("profilePic");
const userDataSubmitButton = document.querySelector(".change-info-btn");
const passwordSubmitButton = document.querySelector(".change-password-btn");
const feedback = document.getElementById("app-form-feedback");

function notify(message, type = "info") {
  if (feedback) {
    feedback.innerHTML = `<div class="alert alert-${type === "error" ? "danger" : type}" role="alert">${message}</div>`;
  }

  if (window.appShell?.showNotice) {
    window.appShell.showNotice(message, type);
    return;
  }

  alert(message);
}

document.addEventListener("DOMContentLoaded", function () {
  if (!token) {
    window.location.href = "/index.html";
    return;
  }

  if (!username) {
    console.error("No username provided in the URL.");
    notify("Geen gebruikersnaam gevonden in de URL.", "warning");
    window.location.href = role === "admin" ? "/user-list.html" : "/timesheet.html";
    return;
  }

  configureAccountFormForRole();
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
    notify("Geen toegang.", "warning");
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
    originalExtraFields = data.extra_fields || {};

    setValue("userId", userId);
    setValue("createdAt", formatDateValue(data.created_at));
    setValue("updatedAt", formatDateValue(data.updated_at));
    setValue("uname", originalUsername);
    setValue("fname", data.first_name || "");
    setValue("lname", data.last_name || "");
    setValue("cname", data.company_name || "");
    setValue("badgeCode", data.badge_code || "");
    setValue("email", originalEmail);
    setValue("extraFields", JSON.stringify(originalExtraFields, null, 2));

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
    notify(`Kon gebruikersgegevens niet ophalen: ${error.message}`, "error");
  }
}

async function handleUserDataFormSubmit(event) {
  event.preventDefault();

  const currentUsername = (document.getElementById("uname")?.value || "").trim().toLowerCase();
  const currentEmail = (document.getElementById("email")?.value || "").trim();
  const currentBadgeCode = (document.getElementById("badgeCode")?.value || "").trim();

  if (!currentUsername || !currentEmail) {
    notify("Gebruikersnaam en e-mail mogen niet leeg zijn.", "warning");
    return;
  }

  try {
    if (role === "admin" && currentUsername !== originalUsername) {
      const isUsernameTaken = await checkUsernameUnique(currentUsername);
      if (isUsernameTaken) {
        notify("Gebruikersnaam is al in gebruik.", "warning");
        return;
      }
    }

    if (role === "admin" && currentEmail !== originalEmail) {
      const isEmailTaken = await checkEmailUnique(currentEmail);
      if (isEmailTaken) {
        notify("E-mailadres is al in gebruik.", "warning");
        return;
      }
    }

    const roleSelect = document.getElementById("selectuserrole");
    const blockedRadio = document.querySelector('input[name="blockedStatus"]:checked');
    const extraFields = parseExtraFields();
    if (extraFields === null) {
      return;
    }

    const userData = {
      username: role === "admin" ? currentUsername : originalUsername,
      first_name: (document.getElementById("fname")?.value || "").trim(),
      last_name: (document.getElementById("lname")?.value || "").trim(),
      company_name: (document.getElementById("cname")?.value || "").trim(),
      badge_code: role === "admin" ? currentBadgeCode : "",
      email: currentEmail,
      user_role: roleSelect ? roleSelect.value : "user",
      blocked: blockedRadio ? blockedRadio.value === "true" : false,
      extra_fields: role === "admin" ? extraFields : {},
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

    notify(result.message || "Accountgegevens succesvol bijgewerkt.", "success");

    originalUsername = role === "admin" ? currentUsername : originalUsername;
    originalEmail = currentEmail;
    originalExtraFields = role === "admin" ? extraFields : originalExtraFields;

    window.location.href = role === "admin"
      ? "/user-list.html"
      : `/timesheet.html?username=${encodeURIComponent(originalUsername)}`;
  } catch (error) {
    console.error("Error during user data submission:", error);
    notify(error.message || "Er is een fout opgetreden bij het opslaan.", "error");
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

  const password = (document.getElementById("pass")?.value || "").trim();
  const repeatPassword = (document.getElementById("rpass")?.value || "").trim();

  if (!password || !repeatPassword) {
    notify("Wachtwoordvelden mogen niet leeg zijn.", "warning");
    return;
  }

  if (password.length < 6) {
    notify("Wachtwoord moet minstens 6 tekens bevatten.", "warning");
    return;
  }

  if (password !== repeatPassword) {
    notify("Wachtwoorden komen niet overeen.", "warning");
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

    notify(result.message || "Wachtwoord succesvol bijgewerkt.", "success");

    setValue("pass", "");
    setValue("rpass", "");
  } catch (error) {
    console.error("Error updating password:", error);
    notify(error.message || "Er is een fout opgetreden bij het wijzigen van het wachtwoord.", "error");
  }
}

function setValue(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.value = value;
  }
}

function configureAccountFormForRole() {
  if (role === "admin") return;

  document.getElementById("uname")?.setAttribute("readonly", "readonly");
  document.getElementById("badgeCode")?.setAttribute("readonly", "readonly");
  document.getElementById("extraFields")?.setAttribute("readonly", "readonly");

  const backLink = document.getElementById("account-back-link");
  if (backLink && username) {
    backLink.setAttribute("href", `timesheet.html?username=${encodeURIComponent(username)}`);
  }
}

function parseExtraFields() {
  const rawValue = document.getElementById("extraFields")?.value?.trim() || "";
  if (!rawValue) {
    return {};
  }

  try {
    const parsed = JSON.parse(rawValue);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      notify("Extra databasevelden moeten een geldig JSON-object zijn.", "warning");
      return null;
    }
    return parsed;
  } catch (error) {
    notify("Extra databasevelden bevatten ongeldige JSON.", "warning");
    return null;
  }
}

function formatDateValue(value) {
  if (!value) {
    return "";
  }

  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString("nl-BE");
  } catch (error) {
    return value;
  }
}
