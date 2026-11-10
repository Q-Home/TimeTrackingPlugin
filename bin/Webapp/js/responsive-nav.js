(() => {
  const sidebar = document.querySelector(".iq-sidebar, .rail");
  const brand = sidebar?.querySelector(".iq-sidebar-logo, .brand");
  const menu = sidebar?.querySelector("#sidebar-scrollbar, nav");
  if (!brand || !menu) return;

  const account = sidebar.querySelector(".rail-bottom");
  const panels = account ? [menu, account] : [menu];
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "tt-nav-toggle";
  toggle.textContent = "Menu";
  toggle.setAttribute("aria-controls", panels.map((panel, index) => {
    panel.id ||= `tt-menu-panel-${index}`;
    return panel.id;
  }).join(" "));

  function setExpanded(expanded) {
    sidebar.toggleAttribute("data-menu-collapsed", !expanded);
    toggle.setAttribute("aria-expanded", String(expanded));
  }

  setExpanded(false);
  if (brand.matches("a")) brand.after(toggle);
  else brand.append(toggle);

  toggle.addEventListener("click", () => {
    setExpanded(toggle.getAttribute("aria-expanded") === "false");
  });
  sidebar.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !toggle.getClientRects().length ||
        toggle.getAttribute("aria-expanded") !== "true") return;
    setExpanded(false);
    toggle.focus();
  });
})();
