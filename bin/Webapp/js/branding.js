(() => {
  const DEFAULT_BRANDING = {
    brand_name: "Q-Home",
    logo_url: "images/logo.png",
    accent_color: "#4caf57",
  };

  const currentHost = window.location.hostname;
  const apiUrl = `http://${currentHost}:5000/api/v1`;

  function shadeColor(hex, percent) {
    const normalized = String(hex || DEFAULT_BRANDING.accent_color).replace("#", "");
    const value = parseInt(normalized, 16);
    const amount = Math.round(2.55 * percent);
    const r = Math.max(0, Math.min(255, (value >> 16) + amount));
    const g = Math.max(0, Math.min(255, ((value >> 8) & 0xff) + amount));
    const b = Math.max(0, Math.min(255, (value & 0xff) + amount));
    return `#${(0x1000000 + r * 0x10000 + g * 0x100 + b).toString(16).slice(1)}`;
  }

  function hexToRgb(hex) {
    const normalized = String(hex || DEFAULT_BRANDING.accent_color).replace("#", "");
    const value = parseInt(normalized, 16);
    return `${value >> 16}, ${(value >> 8) & 0xff}, ${value & 0xff}`;
  }

  function applyBranding(settings) {
    const branding = { ...DEFAULT_BRANDING, ...(settings || {}) };
    const root = document.documentElement;
    const accent = branding.accent_color || DEFAULT_BRANDING.accent_color;
    const accentDark = shadeColor(accent, -14);
    const accentSoft = `${accent}17`;
    const accentBorder = `${accent}66`;

    root.style.setProperty("--tt-accent", accent);
    root.style.setProperty("--tt-accent-dark", accentDark);
    root.style.setProperty("--tt-accent-soft", accentSoft);
    root.style.setProperty("--tt-accent-border", accentBorder);
    root.style.setProperty("--tt-accent-rgb", hexToRgb(accent));

    document.querySelectorAll(".tt-shell-brand__title, [data-brand-name]").forEach((element) => {
      element.textContent = branding.brand_name;
    });

    document.querySelectorAll(".tt-shell-brand img, [data-brand-logo]").forEach((image) => {
      image.setAttribute("src", branding.logo_url || DEFAULT_BRANDING.logo_url);
      image.setAttribute("alt", branding.brand_name);
    });

    const title = document.title || "";
    if (title.includes("Q-Home") || title.includes("TimeTracking") || title.includes("Time Tracking")) {
      document.title = title
        .replaceAll("Q-Home", branding.brand_name)
        .replaceAll("TimeTracking", branding.brand_name)
        .replaceAll("Time Tracking", branding.brand_name);
    }

    window.appBranding = branding;
    window.dispatchEvent(new CustomEvent("branding:loaded", { detail: branding }));
  }

  async function loadBranding() {
    try {
      const response = await fetch(`${apiUrl}/settings/branding`, { method: "GET" });
      const result = await response.json();
      const branding = result?.data || DEFAULT_BRANDING;
      applyBranding(branding);
      return branding;
    } catch (error) {
      applyBranding(DEFAULT_BRANDING);
      return DEFAULT_BRANDING;
    }
  }

  window.branding = {
    defaults: DEFAULT_BRANDING,
    load: loadBranding,
    apply: applyBranding,
  };

  document.addEventListener("DOMContentLoaded", loadBranding);
})();
