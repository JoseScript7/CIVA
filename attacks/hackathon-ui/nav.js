(function () {
  const INACTIVE_CLASSES = ["bg-[#adc6ff]/10", "text-[#adc6ff]", "border-r-2", "border-[#adc6ff]"];
  const ACTIVE_CLASSES = ["bg-[#adc6ff]/10", "text-[#adc6ff]", "border-r-2", "border-[#adc6ff]"];

  // Keep navigation on the existing multi-page hackathon dashboard.
  const routes = {
    Sentinel: "/",
    Behavior: "/behavior.html",
    Orchestrator: "/orchestrator.html",
    Deception: "/deception.html",
    "Threat Intel": "/threat-intel.html",
    "System Settings": "/system-settings.html",
    "Audit Logs": "/audit-logs.html"
  };

  function textOf(el) {
    const clone = el.cloneNode(true);
    clone.querySelectorAll(".material-symbols-outlined").forEach((n) => n.remove());
    return (clone.textContent || "").replace(/\s+/g, " ").trim();
  }

  function applyNavLinks() {
    document.querySelectorAll("a").forEach((a) => {
      const label = textOf(a);
      if (routes[label]) {
        a.setAttribute("href", routes[label]);
        INACTIVE_CLASSES.forEach((c) => a.classList.remove(c));
        if (!a.classList.contains("hover:bg-[#1c1f2a]")) {
          a.classList.add("hover:bg-[#1c1f2a]");
        }
        if (!a.classList.contains("hover:text-[#adc6ff]")) {
          a.classList.add("hover:text-[#adc6ff]");
        }
        if (!a.classList.contains("text-[#c2c6d6]")) {
          a.classList.add("text-[#c2c6d6]");
        }

        // Use normal navigation so each existing dashboard page loads unchanged.
      }
    });

    if (!document.getElementById("scenarioBtn")) {
      const deployBtn = Array.from(document.querySelectorAll("button")).find((b) => {
        return textOf(b).toLowerCase() === "deploy policy";
      });
      if (deployBtn) {
        deployBtn.id = "scenarioBtn";
      }
    }

    if (!document.getElementById("scenarioState")) {
      const btn = document.getElementById("scenarioBtn");
      if (btn && btn.parentElement) {
        const state = document.createElement("span");
        state.id = "scenarioState";
        state.className = "font-label text-[10px] uppercase tracking-widest text-tertiary";
        state.textContent = "Stopped";
        btn.parentElement.appendChild(state);
      }
    }
  }

  function markActive() {
    const path = (window.location.pathname || "/").toLowerCase();
    const active =
      path.endsWith("/behavior.html") ? "Behavior" :
      path.endsWith("/orchestrator.html") ? "Orchestrator" :
      path.endsWith("/deception.html") ? "Deception" :
      path.endsWith("/threat-intel.html") ? "Threat Intel" :
      path.endsWith("/system-settings.html") ? "System Settings" :
      path.endsWith("/audit-logs.html") ? "Audit Logs" :
      "Sentinel";

    document.querySelectorAll("a").forEach((a) => {
      const label = textOf(a);
      if (!routes[label]) return;
      INACTIVE_CLASSES.forEach((c) => a.classList.remove(c));
      if (label === active) {
        a.classList.remove("text-[#c2c6d6]");
        ACTIVE_CLASSES.forEach((c) => a.classList.add(c));
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    applyNavLinks();
    markActive();
  });

  window.addEventListener("popstate", () => {
    markActive();
  });
})();
