const currentHost = window.location.hostname;
const apiUrl = `http://${currentHost}:5000/api/v1`;

document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("access_token");
  const role = (localStorage.getItem("role") || "").toLowerCase();

  if (!token) {
    window.location.href = "/index.html";
    return;
  }

  if (role !== "admin") {
    window.location.href = "/timesheet.html";
    return;
  }

  bindSettingsForm();
  loadSettings();
});

function authHeaders() {
  return {
    Authorization: `Bearer ${localStorage.getItem("access_token")}`,
    "Content-Type": "application/json",
  };
}

function bindSettingsForm() {
  document.getElementById("brandingForm")?.addEventListener("submit", saveSettings);
  document.getElementById("logoUpload")?.addEventListener("change", handleLogoUpload);
  document.getElementById("accentColor")?.addEventListener("input", updatePreview);
  document.getElementById("brandName")?.addEventListener("input", updatePreview);
  document.getElementById("logoUrl")?.addEventListener("input", updatePreview);
}

async function loadSettings() {
  try {
    const response = await fetch(`${apiUrl}/settings/branding`);
    const result = await response.json();
    const settings = result?.data || window.branding?.defaults || {};

    document.getElementById("brandName").value = settings.brand_name || "Q-Home";
    document.getElementById("logoUrl").value = settings.logo_url || "images/logo.png";
    document.getElementById("accentColor").value = settings.accent_color || "#4caf57";
    updatePreview();
  } catch (error) {
    showMessage("Instellingen konden niet geladen worden.", "danger");
  }
}

function handleLogoUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  if (!file.type.startsWith("image/")) {
    showMessage("Kies een geldig afbeeldingsbestand.", "warning");
    return;
  }

  if (file.size > 500000) {
    showMessage("Logo is te groot. Gebruik maximaal 500 KB.", "warning");
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    document.getElementById("logoUrl").value = reader.result;
    updatePreview();
  };
  reader.readAsDataURL(file);
}

function updatePreview() {
  const brandName = document.getElementById("brandName")?.value || "Q-Home";
  const logoUrl = document.getElementById("logoUrl")?.value || "images/logo.png";
  const accentColor = document.getElementById("accentColor")?.value || "#4caf57";

  document.getElementById("brandPreviewName").textContent = brandName;
  document.getElementById("brandPreviewLogo").src = logoUrl;
  document.getElementById("brandPreviewButton").style.backgroundColor = accentColor;
  document.getElementById("brandPreviewButton").style.borderColor = accentColor;
}

async function saveSettings(event) {
  event.preventDefault();

  const payload = {
    brand_name: document.getElementById("brandName").value.trim(),
    logo_url: document.getElementById("logoUrl").value.trim(),
    accent_color: document.getElementById("accentColor").value,
  };

  try {
    const response = await fetch(`${apiUrl}/settings/branding`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Instellingen opslaan mislukt.");
    }

    window.branding?.apply(result.data);
    showMessage("White-label instellingen opgeslagen.", "success");
  } catch (error) {
    showMessage(error.message, "danger");
  }
}

function showMessage(message, type) {
  const container = document.getElementById("settingsMessage");
  if (!container) return;

  container.innerHTML = `
    <div class="alert alert-${type}" role="alert">
      ${escapeHtml(message)}
    </div>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
