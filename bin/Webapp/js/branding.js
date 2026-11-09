(() => {
  const defaults = {
    brand_name: "Q-Home",
    logo_url: "images/logo.png",
    accent_color: "#4caf57",
  };
  const cacheKey = "tt-installation-branding";
  const root = document.documentElement;
  const originalTitle = document.title;
  let revision = 0;

  function normalize(settings) {
    const color = settings?.accent_color;
    const logo = settings?.logo_url;
    return {
      brand_name: typeof settings?.brand_name === "string" && settings.brand_name.trim()
        ? settings.brand_name.trim() : defaults.brand_name,
      logo_url: typeof logo === "string" && /^(images\/|https?:\/\/|data:image\/)/i.test(logo)
        ? logo : defaults.logo_url,
      accent_color: typeof color === "string" && /^#[0-9a-f]{6}$/i.test(color)
        ? color : defaults.accent_color,
    };
  }

  function rgb(hex) {
    return hex.slice(1).match(/../g).map((part) => parseInt(part, 16));
  }

  function readableAccent(hex) {
    let channels = rgb(hex);
    const luminance = () => channels.reduce((sum, value, index) => {
      const srgb = value / 255;
      const linear = srgb <= 0.04045 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4;
      return sum + linear * [0.2126, 0.7152, 0.0722][index];
    }, 0);
    while (luminance() > 0.18) {
      channels = channels.map((value) => Math.floor(value * 0.9));
    }
    return `#${channels.map((value) => value.toString(16).padStart(2, "0")).join("")}`;
  }

  function readCache() {
    try {
      return normalize(JSON.parse(sessionStorage.getItem(cacheKey)));
    } catch {
      return defaults;
    }
  }

  let current = readCache();

  function render(branding) {
    const { brand_name: name, logo_url: logo, accent_color: accent } = branding;
    root.style.setProperty("--tt-accent", accent);
    root.style.setProperty("--tt-accent-dark", readableAccent(accent));
    root.style.setProperty("--tt-accent-soft", `${accent}17`);
    root.style.setProperty("--tt-accent-border", `${accent}66`);
    root.style.setProperty("--tt-accent-rgb", rgb(accent).join(", "));
    root.style.setProperty("--tt-company-logo", `url(${JSON.stringify(new URL(logo, location.href).href)})`);
    root.dataset.ttBrand = logo === defaults.logo_url ? "default" : "company";

    document.querySelectorAll(".tt-shell-brand__eyebrow, [data-brand-name]").forEach((element) => {
      element.textContent = name;
    });
    document.querySelectorAll("[data-brand-logo]").forEach((image) => {
      image.src = logo;
      image.alt = name;
    });
    document.title = originalTitle.replace(/Q-Home|TimeTracking|Time Tracking/g, () => name);
    window.appBranding = branding;
    if (document.readyState !== "loading") {
      root.dataset.ttBrandReady = "";
      window.dispatchEvent(new CustomEvent("branding:loaded", { detail: branding }));
    }
  }

  async function loadImage(url) {
    const image = new Image();
    let timer;
    try {
      image.src = url;
      return await Promise.race([
        image.decode().then(() => url),
        new Promise((resolve) => { timer = setTimeout(() => resolve(defaults.logo_url), 1800); }),
      ]);
    } catch {
      return defaults.logo_url;
    } finally {
      clearTimeout(timer);
    }
  }

  async function apply(settings) {
    const change = ++revision;
    const next = normalize(settings);
    if (next.logo_url !== current.logo_url && next.logo_url !== defaults.logo_url) {
      next.logo_url = await loadImage(next.logo_url);
    }
    if (change !== revision) return current;

    current = next;
    render(current);
    try {
      sessionStorage.setItem(cacheKey, JSON.stringify(current));
    } catch {
      // The rendered branding still works if browser storage is unavailable.
    }
    return current;
  }

  async function load() {
    const pendingRevision = revision;
    try {
      const response = await fetch("/api/v1/settings/branding", { cache: "no-cache" });
      if (!response.ok) return current;
      const { data } = await response.json();
      return data && pendingRevision === revision ? await apply(data) : current;
    } catch {
      return current;
    }
  }

  window.branding = { defaults, load, apply };

  // Reuse a decoded logo before the first paint after navigation.
  render(current);
  document.addEventListener("DOMContentLoaded", () => {
    render(current);
    load();
  });
})();
