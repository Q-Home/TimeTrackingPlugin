const imagesPerPage = 10;
let currentPage = 1;
let mediaData = [];

const url = process.env.URL || 'http://127.0.0.1:5000';  // Basis-URL

async function fetchMedia() {
    try {
        const response = await fetch(`${url}/api/v1/media`);  // Ensure this matches your API endpoint
        const data = await response.json();
        mediaData = data.media || [];
        renderMedia();
    } catch (error) {
        console.error("Error fetching media data:", error);
    }
}

function renderMedia() {
    // Clear the media section before rendering
    const mediaContainer = document.getElementById("media");
    let images = ``

    // Calculate the indices for the current page
    const startIndex = (currentPage - 1) * imagesPerPage;
    const endIndex = Math.min(startIndex + imagesPerPage, mediaData.length);

    // Create image elements for the current page
    for (let i = startIndex; i < endIndex; i++) {
    
        images += `<img src="images/promomateriaal/${mediaData[i]}"" alt="Media" style="max-height: 200px; max-width: 250px">`;
    }
    console.log(images);
    document.querySelector(".js-images").innerHTML = images;
    // Update the pagination
    renderPagination();
}

function renderPagination() {
    const paginationContainer = document.getElementById("pagination");
    paginationContainer.innerHTML = '';

    // Calculate total pages
    const totalPages = Math.ceil(mediaData.length / imagesPerPage);

    // Add "Previous" button
    const prevButton = document.createElement("li");
    prevButton.classList.add("page-item");
    if (currentPage === 1) {
        prevButton.classList.add("disabled");
    }
    prevButton.innerHTML = `<span class="page-link">Previous</span>`;
    prevButton.onclick = () => changePage(currentPage - 1);
    paginationContainer.appendChild(prevButton);

    // Add page number buttons
    for (let i = 1; i <= totalPages; i++) {
        const pageButton = document.createElement("li");
        pageButton.classList.add("page-item");
        if (i === currentPage) {
            pageButton.classList.add("active");
        }
        pageButton.innerHTML = `<a class="page-link" href="#">${i}</a>`;
        pageButton.onclick = () => changePage(i);
        paginationContainer.appendChild(pageButton);
    }

    // Add "Next" button
    const nextButton = document.createElement("li");
    nextButton.classList.add("page-item");
    if (currentPage === totalPages) {
        nextButton.classList.add("disabled");
    }
    nextButton.innerHTML = `<a class="page-link" href="#">Next</a>`;
    nextButton.onclick = () => changePage(currentPage + 1);
    paginationContainer.appendChild(nextButton);
}

function changePage(page) {
    const totalPages = Math.ceil(mediaData.length / imagesPerPage);
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        renderMedia();
    }
}

// Fetch media on page load
window.onload = fetchMedia;