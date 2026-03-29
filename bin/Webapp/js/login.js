document.addEventListener("DOMContentLoaded", function () {
  const hostname = window.location.hostname;
  const url = `http://${hostname}:5000`;
  const loginError = document.getElementById("loginError");
  const loadingOverlay = document.getElementById("loading");

  if (loadingOverlay) {
    loadingOverlay.style.display = "none";
  }

  console.debug("URL voor API:", url);
  console.debug("Document is geladen, event listeners worden ingesteld.");

  const loginForm = document.getElementById("loginForm");

  if (!loginForm) {
    console.error("loginForm niet gevonden");
    return;
  }

  function showLoginError(message) {
    if (!loginError) {
      alert(message);
      return;
    }

    loginError.textContent = message;
    loginError.style.display = "block";
  }

  function clearLoginError() {
    if (!loginError) {
      return;
    }

    loginError.textContent = "";
    loginError.style.display = "none";
  }

  loginForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearLoginError();

    const usernameOrEmail = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();

    console.debug("Formulier verzonden met gegevens:", {
      usernameOrEmail,
      password: password ? "***" : ""
    });

    if (!usernameOrEmail || !password) {
      showLoginError("Gebruikersnaam en wachtwoord mogen niet leeg zijn.");
      return;
    }

    const data = {
      username: usernameOrEmail,
      password: password
    };

    try {
      const response = await fetch(`${url}/api/v1/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
      });

      const responseData = await response.json();
      console.debug("Login response:", responseData);

      if (response.status === 200) {
        const token = responseData?.data?.access_token;
        const username = responseData?.data?.username;
        const role = responseData?.data?.role || "user";

        if (!token || !username) {
          throw new Error("Login response bevat geen geldig token of username.");
        }

        localStorage.setItem("access_token", token);
        localStorage.setItem("username", username);
        localStorage.setItem("role", role);

        console.log("Ingelogd als:", username, "met rol:", role);
        if (String(role).toLowerCase() === "admin") {
          window.location.href = "/dashboard.html";
        } else {
          window.location.href = `/timesheet.html?username=${encodeURIComponent(username)}`;
        }
      } else if (response.status === 401) {
        showLoginError(responseData.error || "Onjuiste inloggegevens. Probeer het opnieuw.");
      } else if (response.status === 403) {
        showLoginError(responseData.error || "Uw account is geblokkeerd of u heeft geen toegang.");
      } else if (response.status === 500) {
        window.location.href = "/pages-error-500.html";
      } else {
        throw new Error(`Onverwachte response status: ${response.status}`);
      }
    } catch (error) {
      console.error("Fout tijdens het inloggen:", error);
      showLoginError("De loginservice is momenteel niet bereikbaar. Probeer het straks opnieuw.");
    }
  });
});
