const fileInput = document.getElementById("files");
const mediaList = document.querySelector(".js-media-list");
const errorMessage = document.getElementById("error-message");
const uploadForm = document.getElementById("uploadForm");
const submitButton = document.getElementById("submitbutton");
const faqContainer = document.getElementById("faq-container");
const addFaqButton = document.getElementById("add-faq");
const imageView = document.getElementById("fotolijst");

const url = process.env.URL || 'http://127.0.0.1:5000';  // Basis-URL
let originalName = "";
let id = "";
let lijst = [];

// Set the file input to accept only images and videos
fileInput.setAttribute("accept", "image/*,video/*");

// Define addImageClickEvents function
function addImageClickEvents() {
  // Select all delete buttons in image containers
  const imageContainers = document.querySelectorAll('.image-container .js-delete-file');
  
  imageContainers.forEach((imageContainer) => {
    // Add click event listener to each delete button
    imageContainer.addEventListener("click", (event) => {
      event.preventDefault();
      const fileName = imageContainer.getAttribute("data-file");
      console.log(`Deleting file: ${fileName}`);

      // Remove the file from the lijst array
      const index = lijst.indexOf(fileName);
      if (index !== -1) {
        lijst.splice(index, 1);
      }

      // Remove the file from the DOM (image preview)
      const imageElement = imageContainer.closest(".image-container");
      if (imageElement) {
        imageElement.remove();
      }


      console.log(`Updated files in list: ${lijst}`);
    });
  });
}

// Open image modal
function openImageModal(imageSrc) {
  const modal = document.getElementById("image-modal");
  const modalImage = document.getElementById("modal-image");

  modalImage.src = imageSrc;
  modal.style.display = "flex";

  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      closeModal();
    }
  });
}

// Close modal
function closeModal() {
  const modal = document.getElementById("image-modal");
  modal.style.display = "none";
}

// Modify addImageClickEvents to handle deletion of images/videos
function addImageClickEvents() {
  
  // Select all delete buttons in image/video containers
  const deleteButtons = document.querySelectorAll('.js-delete-file');
  
  deleteButtons.forEach((button) => {
    // Add click event listener to each delete button
    button.addEventListener("click", (event) => {
      event.preventDefault();
      
      const fileName = button.getAttribute("data-file");
      console.log(`Deleting file: ${fileName}`);

      // Remove the file from the lijst array
      const index = lijst.indexOf(fileName);
      if (index !== -1) {
        lijst.splice(index, 1);
      }

      // Remove the image/video preview from the DOM
      const mediaItem = button.closest(".media-item");
      if (mediaItem) {
        mediaItem.remove();
      }

      console.log(`Updated files in list: ${lijst}`);
    });
  });
}

// Close modal on close button click
document.getElementById("close-modal").addEventListener("click", closeModal);

// Dynamically add FAQ
addFaqButton.addEventListener("click", () => {
  const faqItem = document.createElement("div");
  faqItem.classList.add("faq-item", "mb-3");
  faqItem.innerHTML = `
    <div class="row">
      <div class="col-md-5">
        <textarea class="form-control" name="question[]" placeholder="Question" rows="2" required maxlength="100"></textarea>
      </div>
      <div class="col-md-5">
        <textarea class="form-control" name="answer[]" placeholder="Answer" rows="2" required></textarea>
      </div>
      <div class="col-md-2 text-right">
        <button type="button" class="btn btn-danger remove-faq">Remove</button>
      </div>
    </div>
  `;
  faqContainer.appendChild(faqItem);

  // Remove specific FAQ
  faqItem.querySelector(".remove-faq").addEventListener("click", () => {
    faqItem.remove();
  });
});

// When a file is selected
fileInput.addEventListener("change", function (event) {
  const files = Array.from(event.target.files);
  console.log(`Files selected: ${files.map((file) => file.name).join(", ")}`);

  let invalidFile = false;

  files.forEach((file) => {
    if (file.type.startsWith("image/") || file.type.startsWith("video/")) {
      if (!lijst.includes(file.name)) {
        lijst.push(file.name);

        let previewHTML = "";
        const fileReader = new FileReader();
        
        fileReader.onload = function (event) {
          if (file.type.startsWith("image/")) {
            previewHTML = `
              <div class="image-container media-item">
                <img src="${event.target.result}" alt="${file.name}" class="img-fluid">
                <small class="form-text text-muted">${file.name}</small>
                <div class="media-action">
                  <a href="#" class="js-delete-file" data-file="${file.name}" title="Delete" style="height:25px;width:25px;position:absolute;top:10px;right:10px;background:#f00;color:#fff;padding:5px;border-radius:50%;display:flex;align-items:center;justify-content:center;text-decoration:none;">
                    <i class="ri-delete-bin-line"></i>
                  </a>
                </div>
              </div>`;
          } else if (file.type.startsWith("video/")) {
            previewHTML = `
              <div class="image-container media-item">
                <video src="${event.target.result}" class="img-fluid" controls></video>
                <small class="form-text text-muted">${file.name}</small>
                <div class="media-action">
                  <a href="#" class="js-delete-file" data-file="${file.name}" title="Delete" style="height:25px;width:25px;position:absolute;top:10px;right:10px;background:#f00;color:#fff;padding:5px;border-radius:50%;display:flex;align-items:center;justify-content:center;text-decoration:none;">
                    <i class="ri-delete-bin-line"></i>
                  </a>
                </div>
              </div>`;
          }

          // Append the preview to imageView
          imageView.innerHTML += previewHTML;
          addImageClickEvents(); // Ensure the delete button and image/video click functionalities are reattached
        };
        
        fileReader.readAsDataURL(file);
      }
    } else {
      invalidFile = true;
    }
  });

  if (invalidFile) {
    errorMessage.style.display = "block";
    errorMessage.textContent = "Error: Only image and video files are allowed!";
  } else {
    errorMessage.style.display = "none";
  }
});


// Handle form submit (AJAX)
submitButton.addEventListener("click", async (event) => {
  event.preventDefault();

  if (!uploadForm) {
    console.error("Form element with ID 'uploadForm' not found.");
    return;
  }

  const formData = new FormData(uploadForm);
  const currentName = document.getElementById("name").value;

  if (currentName !== originalName) {
    formData.append("name", currentName);
  }

  formData.append("existing_files[]", lijst);
  formData.append("id", id);
  console.log("Form id:", id);

  const xhr = new XMLHttpRequest();
  const requestUrl = `${url}/api/v1/playlist/${originalName}`;

  xhr.open("POST", requestUrl, true);

  xhr.onload = function () {
    if (xhr.status === 200) {
      alert("Playlist updated successfully!");
    } else {
      const errorMsg = xhr.responseText || "An error occurred while updating the playlist.";
      alert(`Error: ${errorMsg}`);
    }
  };

  xhr.send(formData);
});

// Fetch playlist data on page load
document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const playlistName = urlParams.get("playlist");

  if (!playlistName) {
    console.error("Geen playlistnaam gevonden in de URL.");
    return;
  }

  try {
    const response = await fetch(`${url}/api/v1/playlist/${playlistName}`);
    if (!response.ok) {
      throw new Error(`Kan playlistgegevens niet ophalen: ${response.statusText}`);
    }

    const Data = await response.json();
    const playlistData = Data;
    if (playlistData._id) id = playlistData._id;
    if (playlistData.name) {
      document.getElementById("name").value = playlistData.name;
      originalName = playlistData.name;
    }
    if (playlistData.description) {
      document.getElementById("description").value = playlistData.description;
    }
    if (playlistData.faq && Array.isArray(playlistData.faq)) {
      playlistData.faq.forEach((item) => {
        const faqItem = document.createElement("div");
        faqItem.classList.add("faq-item", "mb-3");
        faqItem.innerHTML = `
          <div class="row">
            <div class="col-md-5">
              <textarea class="form-control" name="question[]" placeholder="Question" rows="2" required maxlength="100">${item.question}</textarea>
            </div>
            <div class="col-md-5">
              <textarea class="form-control" name="answer[]" placeholder="Answer" rows="2" required>${item.answer}</textarea>
            </div>
            <div class="col-md-2 text-right">
              <button type="button" class="btn btn-danger remove-faq">Remove</button>
            </div>
          </div>`;
        faqContainer.appendChild(faqItem);

        faqItem.querySelector(".remove-faq").addEventListener("click", () => {
          faqItem.remove();
        });
      });
    }

    if (playlistData.images && Array.isArray(playlistData.images)) {
      let mediaHTML = "";
      playlistData.images.forEach((file) => {
        lijst.push(file);
        
        // Verkrijg de bestandsextensie (lowercase)
        const extension = file.split('.').pop().toLowerCase();
        
        // Controleer of het een afbeelding of video is op basis van de extensie
        if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg'].includes(extension)) {
          // Behandel het bestand als een afbeelding
          mediaHTML += `
            <div class="image-container media-item">
              <img src="/mnt/signage/${originalName.replace(/%20/g, '_').replace(/\s/g, '_')}/${file}" alt="${file}" class="img-fluid">
              <small class="form-text text-muted">${file}</small>
              <div class="media-action">
                <a href="#" class="js-delete-file" data-file="${file}" title="Delete" style="height:25px;width:25px;position:absolute;top:10px;right:10px;background:#f00;color:#fff;padding:5px;border-radius:50%;display:flex;align-items:center;justify-content:center;text-decoration:none;">
                  <i class="ri-delete-bin-line"></i>
                </a>
              </div>
            </div>`;
        } else if (['mp4', 'webm', 'ogg'].includes(extension)) {
          // Behandel het bestand als een video
          mediaHTML += `
            <div class="image-container media-item">
              <video src="/mnt/signage/${originalName.replace(/%20/g, '_').replace(/\s/g, '_')}/${file}" class="img-fluid" controls></video>
              <small class="form-text text-muted">${file}</small>
              <div class="media-action">
                <a href="#" class="js-delete-file" data-file="${file}" title="Delete" style="height:25px;width:25px;position:absolute;top:10px;right:10px;background:#f00;color:#fff;padding:5px;border-radius:50%;display:flex;align-items:center;justify-content:center;text-decoration:none;">
                  <i class="ri-delete-bin-line"></i>
                </a>
              </div>
            </div>`;
        }
      });
      
      // mediaList.innerHTML = rowsHTML;
      imageView.innerHTML = mediaHTML;
      addImageClickEvents(); // Voeg de delete click events toe
    }
    
  } catch (error) {
    console.error(`Fout bij het ophalen van de playlistgegevens: ${error.message}`);
    errorMessage.style.display = "block";
    errorMessage.textContent = "Er is een fout opgetreden bij het laden van de playlistgegevens.";
  }
});
