(function () {
  const liveState = {
    settings: {
      theme: "dark",
      density: "compact",
      autonomous_mitigation: true,
      shadow_autoscaling: true,
      siem_frequency: "REAL-TIME (STREAM)",
    },
    selectedTheme: "dark",
    selectedDensity: "compact",
    operators: [],
    running: false,
    eventsSeen: 0,
    ws: null,
    audit: {
      page: 1,
      pageSize: 5,
      filtersOpen: false,
      minImpact: 0,
      actor: "",
      action: "",
    },
  };

  function currentPath() {
    return (window.location.pathname || "/").toLowerCase();
  }

  function isAuditPage() {
    return currentPath().endsWith("/audit-logs.html");
  }

  function isSystemSettingsPage() {
    return currentPath().endsWith("/system-settings.html");
  }

  function csvEscape(value) {
    const s = String(value == null ? "" : value);
    if (s.includes(",") || s.includes("\"") || s.includes("\n")) {
      return '"' + s.replace(/\"/g, '""') + '"';
    }
    return s;
  }

  function toast(message, kind) {
    const id = "civa-live-toast";
    let root = document.getElementById(id);
    if (!root) {
      root = document.createElement("div");
      root.id = id;
      root.style.position = "fixed";
      root.style.top = "16px";
      root.style.right = "16px";
      root.style.zIndex = "9999";
      document.body.appendChild(root);
    }

    const node = document.createElement("div");
    const bg = kind === "error" ? "#7f1d1d" : kind === "warn" ? "#78350f" : "#0f172a";
    const border = kind === "error" ? "#ef4444" : kind === "warn" ? "#f59e0b" : "#60a5fa";
    node.style.background = bg;
    node.style.border = "1px solid " + border;
    node.style.color = "#e2e8f0";
    node.style.padding = "10px 12px";
    node.style.marginBottom = "8px";
    node.style.borderRadius = "6px";
    node.style.fontSize = "12px";
    node.style.fontFamily = "JetBrains Mono, monospace";
    node.textContent = message;
    root.appendChild(node);

    window.setTimeout(function () {
      node.remove();
    }, 2200);
  }

  async function api(path, opts) {
    const config = opts || {};
    const res = await fetch(path, {
      method: config.method || "GET",
      headers: { "Content-Type": "application/json" },
      body: config.body ? JSON.stringify(config.body) : undefined,
    });
    if (!res.ok) {
      throw new Error(path + " failed with status " + res.status);
    }
    return res.json();
  }

  function ensureLiveChip() {
    if (document.getElementById("civa-live-chip")) {
      return;
    }
    const chip = document.createElement("div");
    chip.id = "civa-live-chip";
    chip.style.position = "fixed";
    chip.style.left = "16px";
    chip.style.bottom = "16px";
    chip.style.zIndex = "9998";
    chip.style.background = "rgba(15, 23, 42, 0.9)";
    chip.style.border = "1px solid rgba(96,165,250,0.6)";
    chip.style.color = "#bfdbfe";
    chip.style.padding = "8px 10px";
    chip.style.borderRadius = "6px";
    chip.style.fontSize = "11px";
    chip.style.fontFamily = "JetBrains Mono, monospace";
    chip.textContent = "LIVE: connecting...";
    document.body.appendChild(chip);
  }

  function updateLiveChip(message) {
    const chip = document.getElementById("civa-live-chip");
    if (chip) {
      chip.textContent = message;
    }
  }

  function applyTheme(theme) {
    const html = document.documentElement;
    html.classList.remove("dark", "light", "emerald");
    if (theme === "light") {
      html.classList.add("light");
      document.body.style.filter = "saturate(0.85) brightness(1.04)";
    } else if (theme === "emerald") {
      html.classList.add("dark");
      document.body.style.filter = "hue-rotate(18deg) saturate(1.1)";
    } else {
      html.classList.add("dark");
      document.body.style.filter = "";
    }
  }

  function applyDensity(density) {
    const compact = density !== "relaxed";
    const root = document.documentElement;
    root.style.setProperty("--civa-density-scale", compact ? "1" : "1.12");
    document.body.style.lineHeight = compact ? "1.3" : "1.55";

    document.querySelectorAll("button, input, select, td, th, p, span").forEach(function (el) {
      if (compact) {
        el.style.letterSpacing = "";
      } else {
        el.style.letterSpacing = "0.01em";
      }
    });
  }

  function setThemeSelectionVisual(theme) {
    const swatches = Array.from(document.querySelectorAll("button.w-6.h-6.rounded-full"));
    if (swatches.length < 3) {
      return;
    }
    swatches.forEach(function (btn) {
      btn.classList.remove("border-primary");
      btn.classList.add("border-transparent");
    });
    const idx = theme === "dark" ? 0 : theme === "light" ? 1 : 2;
    swatches[idx].classList.add("border-primary");
    swatches[idx].classList.remove("border-transparent");
  }

  function setDensitySelectionVisual(density) {
    const compactBtn = Array.from(document.querySelectorAll("button")).find(function (b) {
      return (b.textContent || "").trim().toUpperCase() === "COMPACT";
    });
    const relaxedBtn = Array.from(document.querySelectorAll("button")).find(function (b) {
      return (b.textContent || "").trim().toUpperCase() === "RELAXED";
    });

    if (!compactBtn || !relaxedBtn) {
      return;
    }

    if (density === "compact") {
      compactBtn.classList.add("bg-primary", "text-on-primary");
      relaxedBtn.classList.remove("bg-primary", "text-on-primary");
      relaxedBtn.classList.add("text-slate-500");
    } else {
      relaxedBtn.classList.add("bg-primary", "text-on-primary");
      compactBtn.classList.remove("bg-primary", "text-on-primary");
      compactBtn.classList.add("text-slate-500");
    }
  }

  function getAuditRows() {
    return Array.from(document.querySelectorAll("table tbody tr"));
  }

  function parseImpactFromRow(row) {
    const cells = row.querySelectorAll("td");
    if (cells.length < 4) return 0;
    const txt = (cells[3].textContent || "").replace(/[^0-9]/g, "");
    return Number(txt || 0);
  }

  function actorFromRow(row) {
    const cells = row.querySelectorAll("td");
    if (cells.length < 2) return "";
    return (cells[1].textContent || "").trim().toLowerCase();
  }

  function actionFromRow(row) {
    const cells = row.querySelectorAll("td");
    if (cells.length < 3) return "";
    return (cells[2].textContent || "").trim().toLowerCase();
  }

  function applyAuditFiltersAndPagination() {
    if (!isAuditPage()) return;
    const rows = getAuditRows();

    const filtered = rows.filter(function (row) {
      const impact = parseImpactFromRow(row);
      const actor = actorFromRow(row);
      const action = actionFromRow(row);
      if (impact < liveState.audit.minImpact) return false;
      if (liveState.audit.actor && !actor.includes(liveState.audit.actor)) return false;
      if (liveState.audit.action && !action.includes(liveState.audit.action)) return false;
      return true;
    });

    const totalPages = Math.max(1, Math.ceil(filtered.length / liveState.audit.pageSize));
    if (liveState.audit.page > totalPages) liveState.audit.page = totalPages;
    const start = (liveState.audit.page - 1) * liveState.audit.pageSize;
    const end = start + liveState.audit.pageSize;
    const visibleSet = new Set(filtered.slice(start, end));

    rows.forEach(function (row) {
      row.style.display = visibleSet.has(row) ? "" : "none";
    });

    const summary = Array.from(document.querySelectorAll("span.text-xs.text-slate-500.font-label")).find(function (el) {
      return (el.textContent || "").includes("Showing");
    });
    if (summary) {
      const from = filtered.length ? start + 1 : 0;
      const to = Math.min(end, filtered.length);
      summary.innerHTML = 'Showing <span class="text-on-surface font-mono">' + from + "-" + to + '</span> of <span class="text-on-surface font-mono">' + filtered.length + "</span>";
    }

    const pagerButtons = Array.from(document.querySelectorAll("button"));
    const numberButtons = pagerButtons.filter(function (b) {
      const t = (b.textContent || "").trim();
      return /^\d+$/.test(t);
    });
    numberButtons.forEach(function (btn) {
      const n = Number((btn.textContent || "").trim());
      const active = n === liveState.audit.page;
      if (active) {
        btn.classList.add("bg-primary/20", "text-primary", "border", "border-primary/30");
      } else {
        btn.classList.remove("bg-primary/20", "text-primary", "border", "border-primary/30");
      }
      btn.style.display = n <= totalPages ? "" : "none";
    });
  }

  function downloadAuditTableCSV() {
    const rows = getAuditRows().filter(function (r) { return r.style.display !== "none"; });
    if (!rows.length) {
      toast("No rows available to export", "warn");
      return;
    }

    const header = ["Timestamp", "Actor", "Action", "Impact Score", "Metadata", "State"];
    const lines = [header.join(",")];
    rows.forEach(function (row) {
      const cols = Array.from(row.querySelectorAll("td")).map(function (td) {
        return csvEscape((td.textContent || "").replace(/\s+/g, " ").trim());
      });
      lines.push(cols.join(","));
    });

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "audit-logs-export.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast("Audit CSV exported", "ok");
  }

  function wireAuditLogsControls() {
    if (!isAuditPage()) return;

    const buttons = Array.from(document.querySelectorAll("button"));
    const advBtn = buttons.find(function (b) {
      return ((b.textContent || "").replace(/\s+/g, " ").trim() === "Advanced Filters");
    });
    const exportBtn = buttons.find(function (b) {
      return ((b.textContent || "").replace(/\s+/g, " ").trim() === "Export CSV");
    });

    if (advBtn && !document.getElementById("auditAdvancedFilters")) {
      const panel = document.createElement("div");
      panel.id = "auditAdvancedFilters";
      panel.style.display = "none";
      panel.className = "mb-4 p-4 bg-surface-container border border-outline-variant/20 rounded";
      panel.innerHTML =
        '<div class="grid grid-cols-1 md:grid-cols-3 gap-3">' +
        '<input id="auditFilterActor" class="bg-surface-container-lowest border border-outline-variant/20 text-xs p-2 rounded" placeholder="Actor contains..." />' +
        '<input id="auditFilterAction" class="bg-surface-container-lowest border border-outline-variant/20 text-xs p-2 rounded" placeholder="Action contains..." />' +
        '<input id="auditFilterImpact" type="number" min="0" max="100" value="0" class="bg-surface-container-lowest border border-outline-variant/20 text-xs p-2 rounded" placeholder="Min impact" />' +
        "</div>";

      const tableWrap = document.querySelector("table")?.closest(".bg-surface-container");
      if (tableWrap && tableWrap.parentElement) {
        tableWrap.parentElement.insertBefore(panel, tableWrap);
      }

      advBtn.addEventListener("click", function () {
        liveState.audit.filtersOpen = !liveState.audit.filtersOpen;
        panel.style.display = liveState.audit.filtersOpen ? "block" : "none";
        toast(liveState.audit.filtersOpen ? "Advanced filters opened" : "Advanced filters closed", "ok");
      });

      const actorInput = panel.querySelector("#auditFilterActor");
      const actionInput = panel.querySelector("#auditFilterAction");
      const impactInput = panel.querySelector("#auditFilterImpact");

      [actorInput, actionInput, impactInput].forEach(function (el) {
        el.addEventListener("input", function () {
          liveState.audit.actor = (actorInput.value || "").trim().toLowerCase();
          liveState.audit.action = (actionInput.value || "").trim().toLowerCase();
          liveState.audit.minImpact = Number(impactInput.value || 0);
          liveState.audit.page = 1;
          applyAuditFiltersAndPagination();
        });
      });
    }

    if (exportBtn) {
      exportBtn.addEventListener("click", function (e) {
        e.preventDefault();
        downloadAuditTableCSV();
      });
    }

    const pagerButtons = Array.from(document.querySelectorAll("button"));
    const leftBtn = pagerButtons.find(function (b) {
      return !!b.querySelector('[data-icon="chevron_left"]');
    });
    const rightBtn = pagerButtons.find(function (b) {
      return !!b.querySelector('[data-icon="chevron_right"]');
    });
    const numberButtons = pagerButtons.filter(function (b) {
      return /^\d+$/.test((b.textContent || "").trim());
    });

    if (leftBtn) {
      leftBtn.addEventListener("click", function () {
        liveState.audit.page = Math.max(1, liveState.audit.page - 1);
        applyAuditFiltersAndPagination();
      });
    }
    if (rightBtn) {
      rightBtn.addEventListener("click", function () {
        liveState.audit.page = liveState.audit.page + 1;
        applyAuditFiltersAndPagination();
      });
    }
    numberButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        liveState.audit.page = Number((btn.textContent || "").trim()) || 1;
        applyAuditFiltersAndPagination();
      });
    });

    applyAuditFiltersAndPagination();
  }

  function wireSystemSettingsControls() {
    if (!isSystemSettingsPage()) return;

    const labels = Array.from(document.querySelectorAll("label"));
    const autoLabel = labels.find(function (l) {
      return (l.textContent || "").includes("Autonomous Mitigation");
    });
    const shadowLabel = labels.find(function (l) {
      return (l.textContent || "").includes("Shadow Layer Auto-Scaling");
    });

    const autoInput = autoLabel ? autoLabel.querySelector('input[type="checkbox"]') : null;
    const shadowInput = shadowLabel ? shadowLabel.querySelector('input[type="checkbox"]') : null;
    const siemSelect = document.querySelector("select");

    if (autoInput) {
      autoInput.checked = !!liveState.settings.autonomous_mitigation;
      autoInput.addEventListener("change", function () {
        liveState.settings.autonomous_mitigation = !!autoInput.checked;
        toast("Autonomous mitigation set to " + (autoInput.checked ? "ON" : "STANDBY"), "ok");
      });
    }

    if (shadowInput) {
      shadowInput.checked = !!liveState.settings.shadow_autoscaling;
      shadowInput.addEventListener("change", function () {
        liveState.settings.shadow_autoscaling = !!shadowInput.checked;
        toast("Shadow auto-scaling set to " + (shadowInput.checked ? "ON" : "OFF"), "ok");
      });
    }

    if (siemSelect) {
      siemSelect.value = liveState.settings.siem_frequency || siemSelect.value;
      siemSelect.addEventListener("change", function () {
        liveState.settings.siem_frequency = siemSelect.value;
        toast("SIEM frequency updated", "ok");
      });
    }

    const copyBtn = Array.from(document.querySelectorAll("button")).find(function (b) {
      return !!b.querySelector("span") && (b.textContent || "").includes("content_copy");
    });
    if (copyBtn) {
      copyBtn.addEventListener("click", async function () {
        try {
          await navigator.clipboard.writeText("npm-token-masked");
          toast("Token copied", "ok");
        } catch (e) {
          toast("Clipboard unavailable", "warn");
        }
      });
    }

    const refreshBtn = Array.from(document.querySelectorAll("button")).find(function (b) {
      return !!b.querySelector("span") && (b.textContent || "").includes("refresh");
    });
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        const tokenInput = Array.from(document.querySelectorAll("input")).find(function (i) {
          return (i.placeholder || "").includes("ENTER NEW ACCESS TOKEN");
        });
        if (tokenInput && tokenInput.value.trim()) {
          toast("PYPI token refreshed", "ok");
          tokenInput.value = "";
        } else {
          toast("Enter token before refresh", "warn");
        }
      });
    }

    const editBtns = Array.from(document.querySelectorAll("button")).filter(function (b) {
      return (b.textContent || "").includes("edit_note");
    });
    editBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        const row = btn.closest("tr");
        if (!row) return;
        const roleCell = row.querySelectorAll("td")[1];
        const clearanceTag = row.querySelectorAll("td")[2]?.querySelector("span");
        const newRole = window.prompt("Update role:", roleCell ? roleCell.textContent.trim() : "OPERATOR");
        if (newRole && roleCell) {
          roleCell.textContent = newRole.toUpperCase();
        }
        const newClr = window.prompt("Update clearance:", clearanceTag ? clearanceTag.textContent.trim() : "LVL-2");
        if (newClr && clearanceTag) {
          clearanceTag.textContent = newClr.toUpperCase();
        }
        toast("Operator updated", "ok");
      });
    });
  }

  function formatAttackName(name) {
    const s = String(name || "").replace(/_/g, " ").trim();
    return s ? s.replace(/\b\w/g, function (c) { return c.toUpperCase(); }) : "Unknown";
  }

  function classifyBuckets(events) {
    const out = {
      credential: 0,
      lateral: 0,
      exfil: 0,
    };
    events.forEach(function (e) {
      const a = String(e.attack || "").toLowerCase();
      if (a.includes("credential") || a.includes("spray") || a.includes("brute")) {
        out.credential += 1;
      } else if (a.includes("lateral") || a.includes("hijack") || a.includes("session")) {
        out.lateral += 1;
      } else if (a.includes("exfil") || a.includes("phish") || a.includes("mfa_bypass")) {
        out.exfil += 1;
      }
    });
    return out;
  }

  function renderThreatIntelFromEvents(events) {
    const reqEl = document.getElementById("tiReqRate");
    const riskEl = document.getElementById("tiRiskScore");
    const driftEl = document.getElementById("tiModelDrift");
    const c1 = document.getElementById("tiClsCountCredential");
    const c2 = document.getElementById("tiClsCountLateral");
    const c3 = document.getElementById("tiClsCountExfil");
    const q = document.getElementById("tiQueuedSignatures");
    const epoch = document.getElementById("tiNextEpoch");
    const acc = document.getElementById("tiAccuracy");
    const loss = document.getElementById("tiLossRate");
    const siemList = document.getElementById("tiSiemStatusList");
    const archiveBody = document.getElementById("tiArchiveBody");
    const archiveSummary = document.getElementById("tiArchiveSummary");

    const recent = events.slice(0, 200);
    const avgRisk = recent.length
      ? recent.reduce(function (s, e) { return s + Number(e.risk || 0); }, 0) / recent.length
      : 0;
    const perSec = Math.max(0, Math.round(recent.length / 5));
    const buckets = classifyBuckets(recent);
    const queued = recent.filter(function (e) { return Number(e.risk || 0) >= 60; }).length * 4;
    const drift = recent.length ? Math.min(9.99, avgRisk / 18) : 0;
    const accuracy = Math.max(0, 100 - Math.min(35, avgRisk / 3.2));
    const lossRate = Math.max(0.0001, Math.min(0.9, (100 - accuracy) / 1000));

    if (reqEl) reqEl.textContent = perSec + " req/sec";
    if (riskEl) riskEl.textContent = "Risk Score: " + avgRisk.toFixed(1);
    if (driftEl) driftEl.textContent = drift.toFixed(2) + "%";
    if (c1) c1.textContent = String(buckets.credential);
    if (c2) c2.textContent = String(buckets.lateral);
    if (c3) c3.textContent = String(buckets.exfil);
    if (q) q.textContent = String(queued) + " New Signatures Queued";
    if (epoch) {
      const d = new Date(Date.now() + 5 * 60 * 1000);
      epoch.textContent = "Next Epoch: " + d.toTimeString().slice(0, 8);
    }
    if (acc) acc.textContent = accuracy.toFixed(1) + "%";
    if (loss) loss.textContent = lossRate.toFixed(4);

    if (siemList) {
      const siemEvents = recent.slice(0, 3);
      const targets = ["Splunk_Cloud_Prod", "Elastic_SIEM_Dev", "Crowdstrike_Humio"];
      const fmts = ["JSON-STIX", "SYSLOG", "CSV"];
      siemList.innerHTML = siemEvents.map(function (e, i) {
        const size = Math.max(2, Math.round((Number(e.pipeline_latency_ms || 10) + Number(e.ml_latency_ms || 5)) * 0.9));
        return '<div class="p-3 bg-surface-container-low rounded border border-outline-variant/5">' +
          '<div class="flex justify-between items-start mb-2">' +
          '<span class="text-[10px] mono-font text-primary">' + targets[i] + '</span>' +
          '<span class="text-[10px] text-on-surface-variant">' + (i * 4 + 1) + 'm ago</span>' +
          '</div>' +
          '<p class="text-xs font-medium">Exported: ' + e.id + '</p>' +
          '<div class="mt-2 flex items-center gap-2">' +
          '<span class="text-[10px] px-1.5 py-0.5 bg-secondary/10 text-secondary rounded">' + fmts[i] + '</span>' +
          '<span class="text-[10px] text-on-surface-variant">' + size + ' KB</span>' +
          '</div></div>';
      }).join("");
    }

    if (archiveBody) {
      const rows = recent.slice(0, 12);
      archiveBody.innerHTML = rows.map(function (e) {
        const stateDot = Number(e.risk || 0) >= 80 ? "bg-tertiary" : "bg-secondary";
        const terminal = Number(e.risk || 0) >= 80 ? "Data Leaked (Simulated)" : "Containment Successful";
        return '<tr class="hover:bg-surface-container transition-colors group">' +
          '<td class="py-4 px-2"><div class="flex items-center gap-2"><span class="material-symbols-outlined text-sm text-on-surface-variant" data-icon="description">description</span><span class="mono-font">' + e.id + '</span></div></td>' +
          '<td class="py-4 px-2 text-on-surface-variant">' + Math.max(1, Math.round(Number(e.risk || 0) / 7)) + 'h ' + (Math.round(Number(e.ml_latency_ms || 3)) % 60) + 'm</td>' +
          '<td class="py-4 px-2"><span class="px-2 py-0.5 bg-surface-container-high rounded text-[10px] border border-outline-variant/20">' + formatAttackName(e.attack) + '</span></td>' +
          '<td class="py-4 px-2"><div class="flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full ' + stateDot + '"></span><span>' + terminal + '</span></div></td>' +
          '<td class="py-4 px-2 text-right"><button class="text-primary hover:underline font-bold">REPLAY</button><span class="mx-2 text-outline-variant opacity-30">|</span><button class="text-on-surface-variant hover:text-on-surface"><span class="material-symbols-outlined text-sm align-middle" data-icon="download">download</span></button></td>' +
          '</tr>';
      }).join("");

      if (archiveSummary) {
        archiveSummary.textContent = "Showing " + Math.min(rows.length, 12) + " of " + recent.length + " archived sessions";
      }
    }
  }

  async function wireThreatIntelRealtime() {
    if (!currentPath().endsWith("/threat-intel.html")) return;
    try {
      const data = await api("/api/events?limit=250");
      const events = (data && data.events) ? data.events : [];
      renderThreatIntelFromEvents(events);
    } catch (e) {
      toast("Threat Intel live feed unavailable", "warn");
    }
  }

  function appendOperatorRow(operator) {
    const tbody = document.querySelector("table tbody");
    if (!tbody) {
      return;
    }

    const initials = operator.name
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map(function (s) { return s[0].toUpperCase(); })
      .join("");

    const tr = document.createElement("tr");
    tr.innerHTML =
      '<td class="py-3 text-sm flex items-center gap-2">' +
      '<div class="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-300">' + initials + "</div>" +
      '<span class="font-medium">' + operator.name + "</span>" +
      "</td>" +
      '<td class="py-3 text-xs font-mono text-slate-300">' + operator.role + "</td>" +
      '<td class="py-3"><span class="px-2 py-0.5 bg-primary/10 text-primary text-[10px] border border-primary/20 rounded-sm">' + operator.clearance + "</span></td>" +
      '<td class="py-3"><button class="text-slate-500 hover:text-white transition-colors"><span class="material-symbols-outlined text-lg">edit_note</span></button></td>';
    tbody.appendChild(tr);
  }

  async function saveSettings() {
    const payload = {
      theme: liveState.selectedTheme,
      density: liveState.selectedDensity,
      autonomous_mitigation: liveState.settings.autonomous_mitigation,
      shadow_autoscaling: liveState.settings.shadow_autoscaling,
      siem_frequency: liveState.settings.siem_frequency,
    };
    const data = await api("/api/settings", { method: "POST", body: payload });
    liveState.settings = data.settings;
    applyTheme(liveState.settings.theme);
    applyDensity(liveState.settings.density);
    toast("Environment specs applied", "ok");
  }

  async function toggleScenario() {
    if (liveState.running) {
      await api("/api/attack/stop", { method: "POST" });
      liveState.running = false;
      toast("Live attack scenario stopped", "warn");
    } else {
      await api("/api/attack/start", { method: "POST" });
      liveState.running = true;
      toast("Live attack scenario started", "ok");
    }
  }

  async function doAttack(type) {
    await api("/api/attack/execute?attack_type=" + encodeURIComponent(type), { method: "POST" });
    toast("Attack launched: " + type, "ok");
  }

  function wireTextButtons() {
    const buttons = Array.from(document.querySelectorAll("button"));

    buttons.forEach(function (btn) {
      const text = (btn.textContent || "").trim().replace(/\s+/g, " ");

      if (text === "COMPACT") {
        btn.addEventListener("click", function () {
          liveState.selectedDensity = "compact";
          setDensitySelectionVisual("compact");
          applyDensity("compact");
        });
      }

      if (text === "RELAXED") {
        btn.addEventListener("click", function () {
          liveState.selectedDensity = "relaxed";
          setDensitySelectionVisual("relaxed");
          applyDensity("relaxed");
        });
      }

      if (text === "Apply Environment Specs" || text === "Commit Changes") {
        btn.addEventListener("click", async function () {
          try {
            await saveSettings();
          } catch (e) {
            toast("Failed to apply settings", "error");
          }
        });
      }

      if (text === "+ Add New Operator") {
        btn.addEventListener("click", async function () {
          const name = window.prompt("Operator name:", "N. Carter");
          if (!name) return;
          const role = window.prompt("Role:", "OPERATOR") || "OPERATOR";
          const clearance = window.prompt("Clearance:", "LVL-2") || "LVL-2";
          try {
            const data = await api("/api/operators", {
              method: "POST",
              body: { name: name, role: role, clearance: clearance },
            });
            appendOperatorRow(data.operator);
            toast("Operator added", "ok");
          } catch (e) {
            toast("Failed to add operator", "error");
          }
        });
      }

      if (text === "Deploy Policy") {
        btn.addEventListener("click", async function () {
          try {
            await api("/api/orchestrator/policy", {
              method: "POST",
              body: {
                rule_name: "ui-policy-" + Date.now(),
                source: "hackathon-ui",
                mode: "active",
              },
            });
            toast("Policy deployed", "ok");
          } catch (e) {
            toast("Policy endpoint unavailable", "warn");
          }
        });
      }

      if (text === "SIEM Export" || text === "Export CSV") {
        btn.addEventListener("click", function () {
          if (isAuditPage()) {
            downloadAuditTableCSV();
          } else {
            window.open("/api/export/events.csv?limit=400", "_blank");
            toast("Export started", "ok");
          }
        });
      }

      if (text === "Start Live Attack Scenario" || text === "Stop Live Attack Scenario" || text === "Toggle Scenario") {
        btn.addEventListener("click", async function () {
          try {
            await toggleScenario();
          } catch (e) {
            toast("Unable to toggle scenario", "error");
          }
        });
      }

      if (text === "INITIATE BLACKOUT") {
        btn.addEventListener("click", async function () {
          try {
            await doAttack("session_hijacking");
          } catch (e) {
            toast("Blackout action failed", "error");
          }
        });
      }

      if (text === "FORGE RESPONSE") {
        btn.addEventListener("click", async function () {
          try {
            await doAttack("phishing_mfa");
          } catch (e) {
            toast("Forge response failed", "error");
          }
        });
      }

      if (text === "REPLAY") {
        btn.addEventListener("click", async function () {
          try {
            await api("/api/events/ingest", {
              method: "POST",
              body: {
                attack: "forensics_replay",
                ip: "127.0.0.1",
                user_id: "replay-operator",
                risk: 72,
                action: "DECEPTION",
              },
            });
            toast("Replay injected into live stream", "ok");
          } catch (e) {
            toast("Replay failed", "error");
          }
        });
      }

      if (text === "View All Logs") {
        btn.addEventListener("click", function () {
          window.location.href = "/audit-logs.html";
        });
      }
    });

    const swatches = Array.from(document.querySelectorAll("button.w-6.h-6.rounded-full"));
    if (swatches.length >= 3) {
      swatches[0].addEventListener("click", function () {
        liveState.selectedTheme = "dark";
        setThemeSelectionVisual("dark");
        applyTheme("dark");
      });
      swatches[1].addEventListener("click", function () {
        liveState.selectedTheme = "light";
        setThemeSelectionVisual("light");
        applyTheme("light");
      });
      swatches[2].addEventListener("click", function () {
        liveState.selectedTheme = "emerald";
        setThemeSelectionVisual("emerald");
        applyTheme("emerald");
      });
    }
  }

  async function syncSettings() {
    try {
      const data = await api("/api/settings");
      liveState.settings = data.settings || liveState.settings;
      liveState.operators = data.operators || [];
      liveState.selectedTheme = liveState.settings.theme || "dark";
      liveState.selectedDensity = liveState.settings.density || "compact";
      applyTheme(liveState.selectedTheme);
      applyDensity(liveState.selectedDensity);
      setThemeSelectionVisual(liveState.selectedTheme);
      setDensitySelectionVisual(liveState.selectedDensity);
    } catch (e) {
      toast("Settings API offline, using local behavior", "warn");
    }
  }

  async function syncScenarioStatus() {
    try {
      const data = await api("/api/status");
      liveState.running = !!(data && data.running);
      const label = document.getElementById("scenarioState");
      const btn = document.getElementById("scenarioBtn");
      if (label) {
        label.textContent = liveState.running ? "Running" : "Stopped";
      }
      if (btn) {
        btn.textContent = liveState.running ? "Stop Live Attack Scenario" : "Start Live Attack Scenario";
      }
    } catch (e) {
      // no-op
    }
  }

  function connectLiveStream() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = protocol + "//" + window.location.host + "/ws/events";
    const ws = new WebSocket(url);
    liveState.ws = ws;

    ws.onopen = function () {
      updateLiveChip("LIVE: connected | events " + liveState.eventsSeen);
    };

    ws.onmessage = function (evt) {
      try {
        const payload = JSON.parse(evt.data);
        if (payload && payload.type === "event") {
          liveState.eventsSeen += 1;
          const e = payload.data || {};
          updateLiveChip("LIVE: " + liveState.eventsSeen + " | " + (e.attack || "event") + " | risk " + (e.risk || "-") );
        }
      } catch (e) {
        // no-op
      }
    };

    ws.onclose = function () {
      updateLiveChip("LIVE: reconnecting...");
      window.setTimeout(connectLiveStream, 2500);
    };

    ws.onerror = function () {
      updateLiveChip("LIVE: stream error");
    };
  }

  async function bootstrap() {
    ensureLiveChip();
    await syncSettings();
    wireTextButtons();
    wireSystemSettingsControls();
    wireAuditLogsControls();
    await wireThreatIntelRealtime();
    await syncScenarioStatus();
    connectLiveStream();
    window.setInterval(syncScenarioStatus, 3000);
    window.setInterval(wireThreatIntelRealtime, 3000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();
