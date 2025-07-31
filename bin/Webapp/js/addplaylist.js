const fileInput = document.getElementById('files');
const mediaList = document.querySelector('.js-media-list');
const errorMessage = document.getElementById('error-message');
const uploadForm = document.getElementById('uploadForm'); // Correcte verwijzing naar het form-element
const submitButton = document.getElementById('submitbutton');
const url = process.env.URL || 'http://127.0.0.1:5000';  // Basis-URL
const faqContainer = document.getElementById('faq-container');
const addFaqButton = document.getElementById('add-faq');


// Set the file input to accept only images and videos
fileInput.setAttribute('accept', 'image/*,video/*');

// FAQ Dynamisch Beheer


// Voeg een nieuwe FAQ-vraag toe
addFaqButton.addEventListener('click', () => {
   const faqItem = document.createElement('div');
   faqItem.classList.add('faq-item', 'mb-3');
   faqItem.innerHTML = `
      <div class="row">
         <div class="col-md-5">
            <textarea class="form-control" name="question[]" placeholder="Question" rows="2" required></textarea>
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

   // Verwijder een specifieke FAQ-vraag
   faqItem.querySelector('.remove-faq').addEventListener('click', () => {
      faqItem.remove();
   });
});

// Handle file input change
fileInput.addEventListener('change', function (event) {
   const files = Array.from(event.target.files);
   let rowsHTML = "";
   let invalidFile = false;

   // Loop through selected files
   files.forEach(file => {
      // Check if the file type is valid
      if (file.type.startsWith('image/') || file.type.startsWith('video/')) {
         rowsHTML += `
            <tr>
               <td>${file.name}</td>
               <td>
                  <div class="d-flex align-items-center list-user-action">
                     <a class="iq-bg-primary js-delete-file" data-toggle="tooltip" data-placement="top" title="Delete" href="#">
                        <i class="ri-delete-bin-line"></i>
                     </a>
                  </div>
               </td>
            </tr>`;
      } else {
         invalidFile = true;
      }
   });

   // If there's an invalid file, show error message
   if (invalidFile) {
      errorMessage.style.display = 'block';
      errorMessage.textContent = "Error: Only image and video files are allowed!";
   } else {
      // Clear the error message and add the valid files to the table
      errorMessage.style.display = 'none';
      mediaList.innerHTML += rowsHTML;
   }

   // Add event listeners to the delete buttons
   const deleteButtons = document.querySelectorAll('.js-delete-file');
   deleteButtons.forEach(button => {
      button.addEventListener('click', function (e) {
         e.preventDefault();
         const row = this.closest('tr');
         row.remove(); // Remove the row
      });
   });
});

// Handle form submit (AJAX)
submitButton.addEventListener("click", async (event) => {
   event.preventDefault(); // Voorkomt standaardformulierverzending

   if (!uploadForm) {
      console.error("Form element with ID 'uploadForm' not found.");
      return;
   }

   const formData = new FormData(uploadForm); // Create a FormData object

   // Check if there are files to upload
   const files = fileInput.files;
   if (files.length === 0) {
      alert('Please select at least one file to upload!');
      return;
   }

   // Add files to FormData object
   for (let i = 0; i < files.length; i++) {
      formData.append('files[]', files[i]);
   }

   // Send the form data via AJAX
   const xhr = new XMLHttpRequest();
   xhr.open('POST', `${url}/api/v1/playlist`, true); // Correcte URL

   xhr.onload = function () {
      if (xhr.status === 200) {
          alert('Files successfully uploaded!');
          // Je kunt hier een succesbericht tonen
      } else {
          // Toon de foutmelding die door de server is gestuurd
          const errorMessage = xhr.responseText || 'An error occurred while uploading the files.';
          alert(`Error: ${errorMessage}`);
      }
  };
   xhr.send(formData); // Send the FormData object
});
