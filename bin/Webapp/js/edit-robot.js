document.addEventListener("DOMContentLoaded", async () => {
    const params = new URLSearchParams(window.location.search);
    const macAddress = params.get("mac");
    const url = process.env.URL || 'http://127.0.0.1:5000';  // Basis-URL
    const apiUrl = url + '/api/v1'; // Basis-URL van de backend
    const locationSelect = document.getElementById("location");
    const customLocationInput = document.getElementById("customLocation");
  
    console.log("MAC Address:", macAddress);
  
    if (!macAddress) {
      alert("No MAC address provided!");
      return;
    }
  
    // Haal robotgegevens op en vul formulier
    try {
      const response = await fetch(`${apiUrl}/robots/${macAddress}`);
      if (!response.ok) {
        throw new Error("Failed to fetch robot data.");
      }
  
      const robot = await response.json();
      console.log("Robot data:", robot);
  
      // Vul de velden in
      document.getElementById("nname").value = robot.nickname || "";
      document.getElementById("maddress").value = robot.mac_address || macAddress; // Gebruik MAC-adres uit URL als fallback
      document.getElementById("rtype").value = robot.robot_type || "none";
  
      // Toon het custom location veld afhankelijk van de geselecteerde locatie
      locationSelect.addEventListener("change", function () {
        if (locationSelect.value === "Custom") {
          customLocationInput.classList.remove("d-none"); // Maak het custom location veld zichtbaar
        } else {
          customLocationInput.classList.add("d-none"); // Verberg het custom location veld
          customLocationInput.value = ""; // Reset de waarde
        }
      });
  
      if (robot.location && !["Core", "Forum", "Aula Major", "Onthaal"].includes(robot.location)) {
        locationSelect.value = "Custom";
        customLocationInput.value = robot.location;
        customLocationInput.classList.remove("d-none"); // Zorgt ervoor dat het customLocation veld zichtbaar is
      } else {
        locationSelect.value = robot.location || "Core"; // Standaard locatie
        customLocationInput.classList.add("d-none"); // Verberg het customLocation veld als de locatie geen 'Custom' is
        customLocationInput.value = ""; // Reset custom input
      }
  
      // Haal playlists op en voeg ze toe aan de select-lijst
      try {
        const playlistResponse = await fetch(`${apiUrl}/playlists`);
        if (!playlistResponse.ok) {
          throw new Error("Failed to fetch playlists.");
        }
  
        const playlists = await playlistResponse.json();
        console.log("Playlists response:", playlists);
  
        // Controleer of playlists een array is
        if (!Array.isArray(playlists)) {
          throw new Error("Unexpected playlists format. Expected an array.");
        }
  
        const playlistSelect = document.getElementById("playlist");
        playlists.forEach((playlist) => {
          const option = document.createElement("option");
          option.value = playlist.name; // Naam van de playlist als waarde
          option.textContent = playlist.name; // Naam van de playlist als weergegeven tekst
          playlistSelect.appendChild(option);
        });
  
        // Selecteer de huidige playlist van de robot
        playlistSelect.value = robot.playlist || "none"; // Standaardoptie
      } catch (playlistError) {
        console.error("Error fetching playlists:", playlistError);
        alert("Failed to fetch playlists. Please try again.");
      }
  
      document.getElementById("status-label").value = robot.status ? `${robot.status === "Online" ? "✅ Online" : "🚫 Offline"}` : "Unknown";
    } catch (error) {
      console.error("Error fetching robot data:", error);
      alert("Failed to fetch robot data. Please try again.");
    }
  
    // Voeg een event listener toe voor het verzenden van het formulier
    const submitButton = document.getElementById("submitbutton");
  
    submitButton.addEventListener("click", async (event) => {
      event.preventDefault(); // Voorkom standaard formulierverzending
  
      // Verzamel formulierdata
      const updatedRobotData = {
        nickname: document.getElementById("nname").value,
        mac_address: macAddress,
        robot_type: document.getElementById("rtype").value,
        location: document.getElementById("location").value === "Custom" ? document.getElementById("customLocation").value : document.getElementById("location").value,
        playlist: document.getElementById("playlist").value,
      };
  
      console.log("Verzonden data:", updatedRobotData);
  
      // Verstuur data naar backend
      try {
        const updateResponse = await fetch(`${apiUrl}/robots/${macAddress}`, {
          method: "PUT", // Gebruik PUT om data te updaten
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(updatedRobotData),
        });
  
        if (!updateResponse.ok) {
          throw new Error("Failed to update robot data.");
        }
  
        const result = await updateResponse.json();
        console.log("Resultaat van update:", result);
        alert("Robotgegevens succesvol bijgewerkt!");
  
        // Optioneel: doorsturen of pagina herladen
        // window.location.href = "overzicht.html"; // Voorbeeld redirect
      } catch (error) {
        console.error("Fout bij updaten robotgegevens:", error);
        alert("Fout bij updaten van robotgegevens.");
      }
    });
  });
  