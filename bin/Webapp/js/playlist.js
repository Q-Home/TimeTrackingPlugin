document.addEventListener("DOMContentLoaded", () => {
  const url = process.env.URL || 'http://127.0.0.1:5000';  // Basis-URL
  const playlistsEndpoint = url + "/api/v1/playlists/";
  const deleteplaylistsEndpoint = url +"/api/v1/playlist/";
  const container = document.getElementById("playlist-container");
  const paginationContainer = document.getElementById("pagination");

  const playlistsPerPage = 4;
  let currentPage = 1;
  let playlistsData = [];

  // Function to fetch playlists
  async function fetchPlaylists() {
    try {
      const response = await fetch(playlistsEndpoint);
      if (!response.ok) throw new Error("Network error while fetching playlists");

      const data = await response.json();
      playlistsData = data;
      renderPlaylists();
    } catch (error) {
      console.error("Error fetching playlists:", error);
      container.innerHTML = "<p>Error loading playlists. Please try again later.</p>";
    }
  }

  // Function to render playlists for the current page
  function renderPlaylists() {
    if (playlistsData.length === 0) {
      container.innerHTML = "<p>No playlists available.</p>";
      return;
    }

    const startIndex = (currentPage - 1) * playlistsPerPage;
    const endIndex = Math.min(startIndex + playlistsPerPage, playlistsData.length);

    let html = "";
    playlistsData.slice(startIndex, endIndex).forEach((playlist) => {
      html += `
                <div class="col-sm-12 col-lg-6">
                    <div class="iq-card" style="height: 500px; overflow: hidden;">
                        <div class="iq-card-header d-flex justify-content-between">
                            <div class="iq-header-title">
                                <h4 class="card-title">${playlist.name}</h4>
                            </div>
                        </div>
                        <div class="iq-card-body" style="height: 100%; padding: 5;">
                            <div class="m-2" style="padding-bottom: 50px;">
                                <h5>${playlist.description}</h5>
                            </div>
                            <div id="carouselExampleSlidesOnly" class="carousel slide" data-ride="carousel">
                            <div class="carousel-inner text-center">
                            ${playlist.images
                                .map((image, index) => {
                                    const isVideo = image.endsWith(".mp4");
                                    return `
                                    <div class="carousel-item ${index === 0 ? "active" : ""}">
                                        ${isVideo
                                            ? `<video class="d-block w-100" style="max-height: 300px; max-width: 500px; object-fit: contain;" controls>
                                            <source src="/mnt/signage/${playlist.name}/${image}" type="video/mp4">
                                            Your browser does not support the video tag.
                                        </video>`
                                            : `<img src="/mnt/signage/${playlist.name.replace(/\s+/g, "_")}/${image.replace(/\s+/g, "_")}" class="d-block w-100" style="max-height: 300px; max-width: 500px; object-fit: contain;" alt="Playlist image ${playlist.name}">`
                                        }
                                    </div>
                                    `;
                                })
                                .join("")}
                            </div>
                            </div>

                            <div class="text-right" style="position: absolute; bottom: 40px; right: 40px;">
                                <a href="edit-playlist.html?playlist=${encodeURIComponent(playlist.name)}" class="btn btn-primary">Edit playlist</a>
                            </div>
                            <div class="text-right" style="position: absolute; bottom: 40px; right: 170px;">
                                <button class="btn btn-danger" id="delete-btn-${playlist.name}" >Delete playlist</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
    });

    container.innerHTML = html;
    renderPagination();
    // Bind delete buttons dynamically after playlists are rendered
    playlistsData.forEach((playlist) => {
      const deleteButton = document.getElementById(`delete-btn-${playlist.name}`);
      if (deleteButton) {
        deleteButton.addEventListener("click", () => deletePlaylist(playlist.name));
      }
    });
  }

  // Function to delete playlist
  async function deletePlaylist(playlistName) {
    const confirmDelete = confirm(`Weet je zeker dat je de playlist "${playlistName}" wilt verwijderen?`);

    if (confirmDelete) {
      try {
        const response = await fetch(deleteplaylistsEndpoint, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json", // Zet de juiste content-type header
          },
          body: JSON.stringify({
            playlistName: playlistName, // Naam van de playlist als bijlage
          }),
        });

        if (!response.ok) throw new Error("Het verwijderen van de playlist is mislukt");

        alert("Playlist succesvol verwijderd!");
        // Na het verwijderen, haal de bijgewerkte playlists op
        fetchPlaylists();
      } catch (error) {
        console.error("Fout bij het verwijderen van de playlist:", error);
        alert("Er is een fout opgetreden bij het verwijderen van de playlist. Probeer het later opnieuw.");
      }
    }
  }

  function renderPagination() {
    paginationContainer.innerHTML = "";

    const totalPages = Math.ceil(playlistsData.length / playlistsPerPage);
    if (totalPages <= 1) return;

    const prevButton = document.createElement("li");
    prevButton.classList.add("page-item", currentPage === 1 && "disabled");
    prevButton.innerHTML = `<span class="page-link">Previous</span>`;
    if (currentPage > 1) prevButton.onclick = () => changePage(currentPage - 1);
    paginationContainer.appendChild(prevButton);

    for (let i = 1; i <= totalPages; i++) {
      const pageButton = document.createElement("li");
      pageButton.classList.add("page-item", i === currentPage && "active");
      pageButton.innerHTML = `<a class="page-link" href="#">${i}</a>`;
      pageButton.onclick = () => changePage(i);
      paginationContainer.appendChild(pageButton);
    }

    const nextButton = document.createElement("li");
    nextButton.classList.add("page-item", currentPage === totalPages && "disabled");
    nextButton.innerHTML = `<span class="page-link">Next</span>`;
    if (currentPage < totalPages) nextButton.onclick = () => changePage(currentPage + 1);
    paginationContainer.appendChild(nextButton);
  }

  function changePage(page) {
    const totalPages = Math.ceil(playlistsData.length / playlistsPerPage);
    if (page >= 1 && page <= totalPages) {
      currentPage = page;
      renderPlaylists();
    }
  }

  fetchPlaylists();
});
