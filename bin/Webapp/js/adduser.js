document.addEventListener("DOMContentLoaded", () => {
    const role = sessionStorage.getItem('role');

    // if (role !== 'Admin') {
    //     alert("You are not authorized to access this page.");
    //     window.location.href = "dashboard.html";
    // }

    const url = "http://173.212.225.50:5000";  // Basis-URL

    const form = document.querySelector(".new-user-info form");
    const submitButton = form.querySelector('button[type="submit"]');
    const profilePic = document.querySelector(".profile-pic"); // Selecteer de afbeelding
    const blockedStatusRadios = document.querySelectorAll('input[name="blockedStatus"]'); // Radio-knoppen voor blocked status

    const checkUsernameUnique = async (username) => {
        try {
            const response = await fetch(`${url}/api/v1/users/exists/${username}`);
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

    // Luister naar wijzigingen in de radio-knoppen en wijzig de afbeelding
    blockedStatusRadios.forEach(radio => {
        radio.addEventListener("change", () => {
            if (radio.value === "true" && radio.checked) {
                profilePic.src = "images/user/11.png"; // Blokkeerafbeelding
            } else if (radio.value === "false" && radio.checked) {
                profilePic.src = "images/user/11_green.png"; // Niet-geblokkeerde afbeelding
            }
        });
    });

    submitButton.addEventListener("click", async (event) => {
        event.preventDefault(); // Voorkomt standaardformulierverzending

        // Verzamel formuliergegevens
        const formData = {
            username: document.getElementById("uname").value.toLowerCase(),
            first_name: document.getElementById("fname").value.trim(),
            last_name: document.getElementById("lname").value.trim(),
            company_name: document.getElementById("cname").value.trim(),
            email: document.getElementById("email").value.trim(),
            user_role: document.getElementById("selectuserrole").value,
            password: document.getElementById("pass").value.trim(),
            repeatPassword: document.getElementById("rpass").value.trim(),
            blocked: document.querySelector('input[name="blockedStatus"]:checked').value === "true"
        };

        // Validatie
        const errors = [];
        if (!formData.username) errors.push("User Name is required.");
        if (!formData.first_name) errors.push("First Name is required.");
        if (!formData.last_name) errors.push("Last Name is required.");
        if (!formData.email) errors.push("Email address is required.");
        if (!formData.user_role || formData.user_role === "Select") errors.push("Please select a User Role.");
        if (!formData.password) errors.push("Password is required.");
        if (formData.password !== formData.repeatPassword) errors.push("Passwords do not match.");

        // // Controleer of de gebruikersnaam uniek is
        // if (formData.username) {
        //     const usernameExists = await checkUsernameUnique(formData.username);
        //     if (usernameExists) errors.push("Username already exists. Please choose another.");
        // }

        // // Controleer of het e-mailadres uniek is
        // if (formData.email) {
        //     const emailExists = await checkEmailUnique(formData.email);
        //     if (emailExists) errors.push("Email address already exists. Please choose another.");
        // }

        // Als er validatiefouten zijn, toon ze en stop de verwerking
        if (errors.length > 0) {
            alert("Validation Errors:\n" + errors.join("\n"));
            return;
        }

        try {
            // Verstuur de gegevens naar de server
            const response = await fetch(`${url}/api/v1/user/add/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    username: formData.username,
                    first_name: formData.first_name,
                    last_name: formData.last_name,
                    company_name: formData.company_name,
                    email: formData.email,
                    user_role: formData.user_role,
                    password: formData.password,
                    blocked: formData.blocked
                })
            });

            if (response.ok) {
                const result = await response.json();
                alert("User created successfully with ID: " + result.user_id);
                form.reset(); // Reset het formulier na succesvolle invoer
                profilePic.src = "images/user/11_green.png"; // Reset afbeelding naar niet-geblokkeerd
            } else {
                const error = await response.json();
                alert("Error: " + (error.message || "Unknown error occurred."));
            }
        } catch (err) {
            console.error("Network error:", err);
            alert("A network error occurred. Please try again.");
        }
    });
});
