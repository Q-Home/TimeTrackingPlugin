document.addEventListener("DOMContentLoaded", function () {
    // Controleer of de gebruiker is ingelogd door username en role uit localStorage te halen
    const username = sessionStorage.getItem('username');
    const role = sessionStorage.getItem('role');

    if (!username || !role) {
        console.error("Gebruiker is niet ingelogd.");
        console.log(username, role);
        window.location.href = "index.html";}

    if (role !== 'Admin') {
        const addUserLink = document.querySelector('a[href="add-user.html"]'); 
        if (addUserLink) {
            // Voorkom dat de link werkt door de href leeg te maken
            addUserLink.removeAttribute('href');
            
            // Voeg een 'disabled' klasse toe voor visuele indicatie (optioneel)
            addUserLink.classList.add('disabled');
    
            // Voeg eventueel een mouse cursor verandering toe voor visuele feedback
            addUserLink.style.cursor = 'not-allowed';
        }
    }
    // Zoek naar het element met de id "js-nametag"
    const nametagElement = document.getElementById('js-nametag');

    // Controleer of het element bestaat
    if (nametagElement) {
        // Vul de naam in het element met de id "js-nametag"
        nametagElement.textContent = `Hello ${username}`;
    } else {
        console.error("Element met id 'js-nametag' niet gevonden.");
    }

    // Zoek de link met id "editUserLink"
    const editUserLink = document.getElementById('editUserLink');

    // Controleer of de link bestaat
    if (editUserLink) {
        // Pas de href van de link aan naar de gewenste URL
        editUserLink.href = `edit-user.html?username=${username}`;
    } else {
        console.error("Element met id 'editUserLink' niet gevonden.");
    }

    // Zoek de logout knop
    const logoutBtn = document.getElementById('logoutBtn');

    // Voeg een click event listener toe aan de logout knop
    if (logoutBtn) {
        logoutBtn.addEventListener("click", function (event) {
            event.preventDefault(); // Voorkomt dat de link de pagina onmiddellijk verlaat

            sessionStorage.removeItem('username');
            sessionStorage.removeItem('role');
            window.location.href = "index.html";
        });
    }
});
