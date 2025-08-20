
const url = "http://172.28.0.15:5000";

document.addEventListener("DOMContentLoaded", function () {
    console.debug('Document is geladen, event listeners worden ingesteld.'); // Debugging

    document.getElementById('loginForm').addEventListener('submit', async function (event) {
        event.preventDefault(); // Voorkom standaard verzending

        const usernameOrEmail = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();

        console.debug('Formulier verzonden met gegevens:', { usernameOrEmail, password }); // Debugging

        if (!usernameOrEmail || !password) {
            alert("Gebruikersnaam/e-mail en wachtwoord mogen niet leeg zijn!");
            return;
        }

        const data = { username: usernameOrEmail, password };

        try {
            const response = await fetch(`${url}/api/v1/login/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (response.status === 200) {
                const responseData = await response.json();
                sessionStorage.setItem("username", responseData.username);
                sessionStorage.setItem("role", responseData.role || 'user');
                console.log('Ingelogd als:', responseData.username, 'met rol:', responseData.role || 'user');
                window.location.href = "/dashboard.html";
            } else if (response.status === 401) {
                alert("Onjuiste inloggegevens. Probeer het opnieuw.");
            } else if (response.status === 403) {
                alert("Uw account is geblokkeerd of u heeft geen toegang. Neem contact op met de beheerder.");
                window.location.href = "/index.html";
            } else if (response.status === 500) {
                window.location.href = "/pages-error-500.html";
            } else {
                throw new Error(`Onverwachte response status: ${response.status}`);
            }
        } catch (error) {
            console.error('Fout tijdens het inloggen:', error);
            window.location.href = "/pages-error-500.html";
        }
    });
});
