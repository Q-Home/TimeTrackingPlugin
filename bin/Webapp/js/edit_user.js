// Haal de gebruikersnaam en de rol op uit de URL-parameters en sessionStorage
const urlParams = new URLSearchParams(window.location.search);
const username = urlParams.get("username");
const role = sessionStorage.getItem('role');
const url = process.env.URL || 'http://127.0.0.1:5000';  // Basis-URL
const apiUrl = url + '/api/v1'; // Basis-URL van de backend

console.log("Username from URL parameters:", username);

// Sla originele waarden op
let originalUsername = "";
let originalEmail = "";
let user_id = "";

// Selecteer elementen
const blockedStatusRadios = document.querySelectorAll('input[name="blockedStatus"]');
const profilePic = document.getElementById("profilePic");
const userDataSubmitButton = document.querySelector(".change-info-btn");
const passwordSubmitButton = document.querySelector(".change-password-btn");

if (!profilePic) {
    console.error("Element with id 'profilePic' not found in the DOM.");
}

if (!userDataSubmitButton) {
    console.error("Element with class 'change-info-btn' not found in the DOM.");
}

if (!passwordSubmitButton) {
    console.error("Element with class 'change-password-btn' not found in the DOM.");
}

// Voeg eventlisteners toe voor blokkadestatus
blockedStatusRadios.forEach(radio => {
    radio.addEventListener("change", () => {
        console.log("Blocked status changed:", radio.value);
        if (profilePic) {
            profilePic.src = radio.value === "true" ? "images/user/11.png" : "images/user/11_green.png";
        } else {
            console.error("Cannot set profile picture, element is null.");
        }
    });
});

// Haal gebruikersgegevens op en vul het formulier
async function fetchUserData(username) {
    console.log("Fetching user data for username:", username);
    try {
        const response = await fetch(`${url}/api/v1/users/${username}`);
        if (!response.ok) {
            console.error(`Failed to fetch user data. Status: ${response.status}`);
            return;
        }

        const data = await response.json();
        console.log("Fetched user data:", data);

        // Sla originele waarden op
        originalUsername = data.username;
        originalEmail = data.email;
        user_id = data.user_id;

        // Vul het formulier in met de opgehaalde gegevens
        document.getElementById("uname").value = originalUsername;
        document.getElementById("fname").value = data.first_name;
        document.getElementById("lname").value = data.last_name;
        document.getElementById("cname").value = data.company_name;
        document.getElementById("email").value = originalEmail;
        
        // Stel gebruikersrol in, als de gebruiker admin is
        const roleSelect = document.getElementById("selectuserrole");
        if (roleSelect) {
            // Alleen de admin mag de rol aanpassen
            if (role !== 'Admin') {
                roleSelect.disabled = true;  // Maak het rolkeuzeveld niet beschikbaar voor niet-admins
            }
            roleSelect.value = data.user_role;
            console.log("User role set to:", data.user_role);
        } else {
            console.error("Element with id 'selectuserrole' not found in the DOM.");
        }

        // Stel blokkadestatus in, alleen voor admins
        const blockedStatus = data.blocked ? 'true' : 'false';
        blockedStatusRadios.forEach(radio => {
            if (radio.value === blockedStatus) {
                radio.checked = true;
                if (profilePic) {
                    profilePic.src = blockedStatus === "true" ? "images/user/11.png" : "images/user/11_green.png";
                } else {
                    console.error("Cannot set profile picture, element is null.");
                }
            }
        });

        // Als de gebruiker geen admin is, maak de blokkadestatus niet aanpasbaar
        if (role !== 'Admin') {
            blockedStatusRadios.forEach(radio => {
                radio.disabled = true;
            });
        }

    } catch (error) {
        console.error("Error fetching user data:", error);
    }
}

// Verwerk het formulier voor gebruikersgegevens
async function handleUserDataFormSubmit(event) {
    event.preventDefault();
    console.log("Submitting user data form.");

    const currentUsername = document.getElementById("uname").value.toLowerCase();
    const currentEmail = document.getElementById("email").value;

    try {
        // Controleer of de waarden zijn gewijzigd
        if (currentUsername !== originalUsername) {
            const isUsernameTaken = await checkUsernameUnique(currentUsername);
            if (isUsernameTaken) {
                alert("Username is already in use. Please choose a different username.");
                console.error("Username is already in use:", currentUsername);
                return;
            }
        }

        if (currentEmail !== originalEmail) {
            const isEmailTaken = await checkEmailUnique(currentEmail);
            if (isEmailTaken) {
                alert("Email is already in use. Please provide a different email address.");
                console.error("Email is already in use:", currentEmail);
                return;
            }
        }

        // Als er wijzigingen zijn en deze uniek zijn, ga verder met de update
        const userData = {
            username: currentUsername,
            first_name: document.getElementById("fname").value,
            last_name: document.getElementById("lname").value,
            company_name: document.getElementById("cname").value,
            email: currentEmail,
            user_role: document.getElementById("selectuserrole").value,
            blocked: document.querySelector('input[name="blockedStatus"]:checked').value === 'true',
        };

        console.log("User data to be submitted:", userData);

        const response = await fetch(`${url}/api/v1/users/${user_id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData),
        });
        console.log("Response:", response); 

        if (response.status === 200) {
            alert("User data updated successfully!");
            console.log("User data updated successfully!");
            // Update originele waarden
            originalUsername = currentUsername;
            originalEmail = currentEmail;
            window.location.href = "/Backoffice/Frontend/users-list.html";
        } else {
            alert("Failed to update user data.");
            console.error("Error updating user data:", data.message || "Unknown error.");
        }
    } catch (error) {
        console.error("Error during user data submission:", error);
    }
}

// Functie om te controleren of de gebruikersnaam uniek is
const checkUsernameUnique = async (username) => {
    try {
        const response = await fetch(`${url}/api/v1/users/exists/${username}/`);
        if (response.ok) {
            const result = await response.json();
            return result.exists; // Retourneer true als de gebruikersnaam bestaat
        }
        return false;
    } catch (err) {
        console.error("Error checking username uniqueness:", err);
        return false;
    }
};

// Functie om te controleren of het e-mailadres uniek is
const checkEmailUnique = async (email) => {
    try {
        const response = await fetch(`${url}/api/v1/users/existsEmail/${email}`);
        if (response.ok) {
            const result = await response.json();
            return result.exists; // Retourneer true als het e-mailadres bestaat
        }
        return false;
    } catch (err) {
        console.error("Error checking email uniqueness:", err);
        return false;
    }
};

// Verwerk het wachtwoordformulier
async function handlePasswordFormSubmit(event) {
    event.preventDefault();
    console.log("Submitting password form.");

    const password = document.getElementById("pass").value;
    const repeatPassword = document.getElementById("rpass").value;

    if (!password || !repeatPassword) {
        alert("Password fields cannot be empty!");
        console.error("Password fields are empty.");
        return;
    }

    if (password !== repeatPassword) {
        alert("Passwords do not match!");
        console.error("Passwords do not match.");
        return;
    }

    console.log("Passwords validated successfully.");
    const userData = {
        password: password
    };
    try {
        const response = await fetch(`${url}/api/v1/users/${user_id}/`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData),
        });
        const data = await response.json();

        if (data.success) {
            alert("Password updated successfully!");
            console.log("Password updated successfully!");
        } else {
            alert("Failed to update password.");
            console.error("Error updating password:", data.message || "Unknown error.");
        }
    } catch (error) {
        console.error("Error updating password:", error);
    }
}

// Initialiseer de pagina met gebruikersgegevens
if (username) {
    fetchUserData(username);
} else {
    console.error("No username provided in the URL.");
}

// Voeg eventlisteners toe aan de knoppen
if (userDataSubmitButton) {
    userDataSubmitButton.addEventListener("click", handleUserDataFormSubmit);
}
if (passwordSubmitButton) {
    passwordSubmitButton.addEventListener("click", handlePasswordFormSubmit);
}
