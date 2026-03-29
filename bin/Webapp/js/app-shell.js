(() => {
  const shell = {
    role: (localStorage.getItem("role") || "").toLowerCase(),
    username: localStorage.getItem("username") || "",
    token: localStorage.getItem("access_token") || "",
  };

  function clearSession() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
  }

  function ensureNoticeRegion() {
    let region = document.getElementById("app-notice-region");
    if (region) return region;

    region = document.createElement("div");
    region.id = "app-notice-region";
    region.className = "tt-notice-region";
    document.body.appendChild(region);
    return region;
  }

  function showNotice(message, type = "info", timeout = 3600) {
    const region = ensureNoticeRegion();
    const notice = document.createElement("div");
    notice.className = `tt-notice tt-notice-${type}`;
    notice.innerHTML = `
      <div class="tt-notice__body">${escapeHtml(String(message))}</div>
      <button type="button" class="tt-notice__close" aria-label="Sluiten">&times;</button>
    `;

    notice.querySelector(".tt-notice__close")?.addEventListener("click", () => {
      notice.remove();
    });

    region.appendChild(notice);

    if (timeout > 0) {
      setTimeout(() => {
        notice.remove();
      }, timeout);
    }
  }

  function escapeHtml(value) {
    return value
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function updateText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function applyRoleVisibility() {
    document.querySelectorAll("[data-admin-only]").forEach((element) => {
      if (shell.role === "admin") return;
      element.classList.add("d-none");
    });

    document.querySelectorAll("[data-user-only]").forEach((element) => {
      if (shell.role !== "admin") return;
      element.classList.add("d-none");
    });

    document.querySelectorAll("[data-user-copy]").forEach((element) => {
      const copyType = element.getAttribute("data-user-copy");
      if (shell.role === "admin") return;

      if (copyType === "timesheet-nav") {
        element.textContent = "Mijn Timesheet";
        const parentLink = element.closest("a");
        if (parentLink && shell.username) {
          parentLink.setAttribute("href", `timesheet.html?username=${encodeURIComponent(shell.username)}`);
        }
      } else if (copyType === "account-nav") {
        element.textContent = "Mijn account";
        const parentLink = element.closest("a");
        if (parentLink && shell.username) {
          parentLink.setAttribute("href", `edit-user.html?username=${encodeURIComponent(shell.username)}`);
        }
      }
    });
  }

  function applyProfileBox() {
    updateText("js-nametag", shell.username ? `Hallo ${shell.username}` : "Welkom");

    if (shell.role !== "admin" && shell.username) {
      document.querySelectorAll(".tt-shell-brand").forEach((brandLink) => {
        brandLink.setAttribute("href", `timesheet.html?username=${encodeURIComponent(shell.username)}`);
      });
    }

    const editUserLink = document.getElementById("editUserLink");
    if (editUserLink && shell.username) {
      editUserLink.setAttribute("href", `edit-user.html?username=${encodeURIComponent(shell.username)}`);
    }

    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", (event) => {
        event.preventDefault();
        clearSession();
        window.location.href = "/index.html";
      });
    }
  }

  function redirectAdminPageIfNeeded() {
    const adminPage = document.body.getAttribute("data-admin-page") === "true";
    if (!adminPage || shell.role === "admin") return;

    if (shell.username) {
      window.location.replace(`timesheet.html?username=${encodeURIComponent(shell.username)}`);
      return;
    }

    clearSession();
    window.location.href = "/index.html";
  }

  function init() {
    redirectAdminPageIfNeeded();
    applyRoleVisibility();
    applyProfileBox();
  }

  window.appShell = {
    ...shell,
    clearSession,
    showNotice,
    init,
  };

  document.addEventListener("DOMContentLoaded", init);
})();
