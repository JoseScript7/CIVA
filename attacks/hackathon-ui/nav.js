(function () {
  const INACTIVE_CLASSES = [
    "bg-[#adc6ff]/10",
    "text-[#adc6ff]",
    "border-r-2",
    "border-[#adc6ff]"
  ];

  const ACTIVE_CLASSES = [
    "bg-[#adc6ff]/10",
    "text-[#adc6ff]",
    "border-r-2",
    "border-[#adc6ff]"
  ];

  const routes = {
    Sentinel: "/?view=sentinel",
    Behavior: "/?view=behavior",
    Orchestrator: "/?view=orchestrator",
    Deception: "/?view=deception",
    "Threat Intel": "/?view=threat-intel",
    "System Settings": "/?view=system-settings",
    "Audit Logs": "/?view=audit-logs"
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

        a.addEventListener("click", (e) => {
          const href = a.getAttribute("href") || "";
          if (!href.startsWith("/?view=")) return;
          e.preventDefault();
          window.history.pushState({}, "", href);
          markActive();
          window.dispatchEvent(new CustomEvent("civa:view-change"));
        });
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
    const params = new URLSearchParams(window.location.search);
    const view = (params.get("view") || "sentinel").toLowerCase();
    const activeMap = {
      "sentinel": "Sentinel",
      "behavior": "Behavior",
      "orchestrator": "Orchestrator",
      "deception": "Deception",
      "threat-intel": "Threat Intel",
      "system-settings": "System Settings",
      "audit-logs": "Audit Logs"
    };
    const active = activeMap[view] || "Sentinel";

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
    window.dispatchEvent(new CustomEvent("civa:view-change"));
  });
})();
