document.addEventListener("DOMContentLoaded", function () {
  const hostname = window.location.hostname;
  const url = `http://${hostname}:5000`;

  console.debug("URL voor API:", url);
  console.debug("Document is geladen, event listeners worden ingesteld.");

  const loginForm = document.getElementById("loginForm");

  if (!loginForm) {
    console.error("loginForm niet gevonden");
    return;
  }

  loginForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    const usernameOrEmail = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();

    console.debug("Formulier verzonden met gegevens:", {
      usernameOrEmail,
      password: password ? "***" : ""
    });

    if (!usernameOrEmail || !password) {
      alert("Gebruikersnaam/e-mail en wachtwoord mogen niet leeg zijn.");
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
        window.location.href = "/badgelist.html";
      } else if (response.status === 401) {
        alert(responseData.error || "Onjuiste inloggegevens. Probeer het opnieuw.");
      } else if (response.status === 403) {
        alert(responseData.error || "Uw account is geblokkeerd of u heeft geen toegang.");
        window.location.href = "/index.html";
      } else if (response.status === 500) {
        window.location.href = "/pages-error-500.html";
      } else {
        throw new Error(`Onverwachte response status: ${response.status}`);
      }
    } catch (error) {
      console.error("Fout tijdens het inloggen:", error);
      window.location.href = "/pages-error-500.html";
    }
  });
});