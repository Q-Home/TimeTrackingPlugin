document.addEventListener("DOMContentLoaded", () => {
  const role = (localStorage.getItem("role") || "").toLowerCase();
  const token = localStorage.getItem("access_token");
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

  if (!token) {
    window.location.href = "/index.html";
    return;
  }

  if (role !== "admin") {
    notify("Je hebt geen toegang tot deze pagina.", "warning");
    window.location.href = "/badgelist.html";
    return;
  }

  const hostname = window.location.hostname;
  const url = `http://${hostname}:5000`;
  const apiUrl = `${url}/api/v1`;

  const form = document.querySelector(".new-user-info form");
  if (!form) {
    console.error("Form not found.");
    return;
  }

  const submitButton = form.querySelector('button[type="submit"]');
  const profilePic = document.querySelector(".profile-pic");
  const blockedStatusRadios = document.querySelectorAll('input[name="blockedStatus"]');

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

  async function checkUsernameUnique(username) {
    try {
      const response = await fetch(`${apiUrl}/users/${encodeURIComponent(username)}`, {
        method: "GET",
        headers: authHeaders(false),
      });

      if (response.status === 404) {
        return false;
      }

      if (handleAuthError(response)) return true;

      return response.ok;
    } catch (err) {
      console.error("Error checking username uniqueness:", err);
      return false;
    }
  }

  async function checkEmailUnique(email) {
    try {
      const response = await fetch(`${apiUrl}/users/`, {
        method: "GET",
        headers: authHeaders(false),
      });

      if (handleAuthError(response)) return true;

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || result.message || "Failed to check email");
      }

      const users = result?.data?.users || result?.users || [];
      return users.some(
        (user) => (user.email || "").toLowerCase() === email.toLowerCase()
      );
    } catch (err) {
      console.error("Error checking email uniqueness:", err);
      return false;
    }
  }

  async function checkBadgeCodeUnique(badgeCode) {
    if (!badgeCode) {
      return false;
    }

    try {
      const response = await fetch(`${apiUrl}/users/`, {
        method: "GET",
        headers: authHeaders(false),
      });

      if (handleAuthError(response)) return true;

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || result.message || "Failed to check badge code");
      }

      const users = result?.data?.users || result?.users || [];
      return users.some(
        (user) => (user.badge_code || user.primary_badge || "").toLowerCase() === badgeCode.toLowerCase()
      );
    } catch (err) {
      console.error("Error checking badge code uniqueness:", err);
      return false;
    }
  }

  blockedStatusRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      if (!profilePic) return;

      if (radio.value === "true" && radio.checked) {
        profilePic.src = "images/user/11.png";
      } else if (radio.value === "false" && radio.checked) {
        profilePic.src = "images/user/11_green.png";
      }
    });
  });

  submitButton.addEventListener("click", async (event) => {
    event.preventDefault();

    const username = (document.getElementById("uname")?.value || "").trim().toLowerCase();
    const firstName = (document.getElementById("fname")?.value || "").trim();
    const lastName = (document.getElementById("lname")?.value || "").trim();
    const companyName = (document.getElementById("cname")?.value || "").trim();
    const badgeCode = (document.getElementById("badgeCode")?.value || "").trim();
    const email = (document.getElementById("email")?.value || "").trim();
    const selectedRole = (document.getElementById("selectuserrole")?.value || "").trim();
    const password = (document.getElementById("pass")?.value || "").trim();
    const repeatPassword = (document.getElementById("rpass")?.value || "").trim();
    const blocked =
      document.querySelector('input[name="blockedStatus"]:checked')?.value === "true";

    const errors = [];

    if (!username) errors.push("User Name is required.");
    if (!firstName) errors.push("First Name is required.");
    if (!lastName) errors.push("Last Name is required.");
    if (!email) errors.push("Email address is required.");
    if (!selectedRole || selectedRole === "Select") errors.push("Please select a User Role.");
    if (!password) errors.push("Password is required.");
    if (password.length < 6) errors.push("Password must be at least 6 characters.");
    if (password !== repeatPassword) errors.push("Passwords do not match.");

    if (username) {
      const usernameExists = await checkUsernameUnique(username);
      if (usernameExists) {
        errors.push("Username already exists. Please choose another.");
      }
    }

    if (email) {
      const emailExists = await checkEmailUnique(email);
      if (emailExists) {
        errors.push("Email address already exists. Please choose another.");
      }
    }

    if (badgeCode) {
      const badgeCodeExists = await checkBadgeCodeUnique(badgeCode);
      if (badgeCodeExists) {
        errors.push("Badge code already exists. Please choose another.");
      }
    }

    if (errors.length > 0) {
      notify(errors.join(" "), "warning");
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/users/`, {
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify({
          username: username,
          first_name: firstName,
          last_name: lastName,
          company_name: companyName,
          badge_code: badgeCode,
          email: email,
          role: selectedRole,
          password: password,
          blocked: blocked,
        }),
      });

      if (handleAuthError(response)) return;

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || result.message || "Unknown error occurred.");
      }

      notify(result.message || "Gebruiker succesvol aangemaakt.", "success");

      form.reset();

      if (profilePic) {
        profilePic.src = "images/user/11_green.png";
      }

      window.location.href = "/user-list.html";
    } catch (err) {
      console.error("Create user error:", err);
      notify(err.message || "Er is een netwerkfout opgetreden. Probeer opnieuw.", "error");
    }
  });
});
