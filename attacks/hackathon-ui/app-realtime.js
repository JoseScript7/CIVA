const state = {
  backendAvailable: false,
  running: false,
  events: [],
  currentView: "sentinel",
  websocket: null,
  backendServices: {},
  prometheusMetrics: {}
};

const VIEW_META = {
  sentinel: {
    title: "Sentinel Command Center",
    subtitle: "Edge signal extraction and live policy posture.",
    legacy: "/"
  },
  behavior: {
    title: "Behavior Analytics",
    subtitle: "Anomaly scoring and model-driven risk intelligence.",
    legacy: "/behavior.html"
  },
  orchestrator: {
    title: "Orchestrator Engine",
    subtitle: "Policy execution, routing decisions, and countermeasures.",
    legacy: "/orchestrator.html"
  },
  deception: {
    title: "Deception Layer",
    subtitle: "Shadow sessions and adversary containment workflows.",
    legacy: "/deception.html"
  },
  "threat-intel": {
    title: "Threat Intel & Forensics",
    subtitle: "Classification, export pipelines, and investigation trails.",
    legacy: "/threat-intel.html"
  },
  "system-settings": {
    title: "System Settings",
    subtitle: "Runtime configuration, operator control, and safeguards.",
    legacy: "/system-settings.html"
  },
  "audit-logs": {
    title: "Audit Logs",
    subtitle: "Compliance-grade event ledger and access observability.",
    legacy: "/audit-logs.html"
  }
};

function fmtNumber(n) {
  return Number(n).toLocaleString();
}

function riskColorClass(risk) {
  if (risk >= 80) return "text-tertiary";
  if (risk >= 60) return "text-primary";
  if (risk >= 30) return "text-secondary";
  return "text-on-surface-variant";
}

async function api(path, opts = {}) {
  try {
    const res = await fetch(path, {
      method: opts.method || "GET",
      headers: { "Content-Type": "application/json" },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    if (!res.ok) {
      throw new Error(`API ${path} failed: ${res.status}`);
    }
    return res.json();
  } catch (err) {
    console.error("API Error:", err);
    return null;
  }
}

// WebSocket connection for real-time events
function connectWebSocket() {
  try {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/events`);
    
    ws.onopen = () => {
      console.log("WebSocket connected");
      state.websocket = ws;
    };
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "event") {
          state.events.unshift(message.data);
          // Keep only last 200 events in memory
          if (state.events.length > 200) {
            state.events = state.events.slice(0, 200);
          }
          updateAllViews();
        }
      } catch (err) {
        console.error("WebSocket message error:", err);
      }
    };
    
    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      state.websocket = null;
    };
    
    ws.onclose = () => {
      console.log("WebSocket closed, reconnecting in 3s...");
      state.websocket = null;
      setTimeout(connectWebSocket, 3000);
    };
  } catch (err) {
    console.error("WebSocket connection failed:", err);
    setTimeout(connectWebSocket, 3000);
  }
}

// Fetch events from API (fallback/initial load)
async function fetchEvents() {
  try {
    const data = await api("/api/events?limit=100");
    if (data && data.events) {
      state.events = data.events;
      updateAllViews();
    }
  } catch (err) {
    console.error("Fetch events error:", err);
  }
}

// Poll backend services status
async function pollBackendStatus() {
  try {
    const data = await api("/api/backend/status");
    if (data && data.ok) {
      state.backendAvailable = data.all_healthy;
      state.backendServices = data.services;
      updateBackendStatus();
      updateAllViews();
    }
  } catch (err) {
    state.backendAvailable = false;
  }
}

// Fetch Prometheus metrics
async function fetchPrometheusMetrics() {
  try {
    const data = await api("/api/prometheus/metrics");
    if (data && data.ok) {
      state.prometheusMetrics = data.metrics;
      updateAllViews();
    }
  } catch (err) {
    console.error("Prometheus fetch error:", err);
  }
}

// Get current scenario status
async function getScenarioStatus() {
  try {
    const data = await api("/api/status");
    if (data) {
      state.running = data.running || false;
      renderScenarioState();
    }
  } catch (err) {
    console.error("Get scenario status error:", err);
  }
}

// Start live attack scenario
async function startLiveAttack() {
  try {
    const res = await api("/api/attack/start", { method: "POST" });
    if (res && res.ok) {
      state.running = true;
      renderScenarioState();
      console.log("Attack scenario started");
    }
  } catch (err) {
    console.error("Start attack error:", err);
  }
}

// Stop live attack scenario
async function stopLiveAttack() {
  try {
    const res = await api("/api/attack/stop", { method: "POST" });
    if (res && res.ok) {
      state.running = false;
      renderScenarioState();
      console.log("Attack scenario stopped");
    }
  } catch (err) {
    console.error("Stop attack error:", err);
  }
}

// Execute attack from external source
async function executeAttack(attackType) {
  try {
    const res = await api(`/api/attack/execute?attack_type=${attackType}`, { method: "POST" });
    if (res && res.ok) {
      console.log(`Attack ${attackType} executed`);
      return true;
    }
  } catch (err) {
    console.error("Execute attack error:", err);
  }
  return false;
}

function renderRiskTable(events) {
  const tbody = document.getElementById("riskTableBody");
  if (!tbody) return;

  const rows = events.slice(0, 12).map((e) => {
    const color = riskColorClass(Number(e.risk));
    const status = Number(e.risk) >= 80 ? "Intercepted" : Number(e.risk) >= 60 ? "Shadow Cast" : Number(e.risk) >= 30 ? "Monitoring" : "Observed";
    const action = e.action || "ALLOW";

    return `<tr class="hover:bg-surface-container-low transition-colors group">
      <td class="px-6 py-4 font-label text-on-surface-variant">#${e.id}</td>
      <td class="px-6 py-4 font-semibold">${e.user_id}</td>
      <td class="px-6 py-4 font-label text-on-surface-variant">${e.ip}</td>
      <td class="px-6 py-4"><span class="${color} font-bold">${Number(e.risk).toFixed(1)}</span></td>
      <td class="px-6 py-4"><div class="flex items-center gap-2"><div class="w-1.5 h-1.5 rounded-full ${Number(e.risk) >= 80 ? "bg-tertiary" : Number(e.risk) >= 60 ? "bg-primary" : "bg-secondary"}"></div><span class="text-[10px] uppercase font-label">${status}</span></div></td>
      <td class="px-6 py-4 text-right"><span class="px-3 py-1 ${Number(e.risk) >= 80 ? "bg-tertiary/10 text-tertiary border-tertiary/20" : Number(e.risk) >= 60 ? "bg-primary/10 text-primary border-primary/20" : "bg-secondary/10 text-secondary border-secondary/20"} border rounded-sm font-label text-[10px]">${action}</span></td>
    </tr>`;
  });

  tbody.innerHTML = rows.join("");
}

function renderKpis(events) {
  const traffic = document.getElementById("kpiThroughput");
  const topTraffic = document.getElementById("kpiTopTraffic");
  const topRisk = document.getElementById("kpiTopRisk");
  const aggRisk = document.getElementById("kpiAggRisk");
  const latency = document.getElementById("kpiLatency");
  const neutral = document.getElementById("kpiNeutralization");
  const shadow = document.getElementById("kpiShadowSessions");
  const node = document.getElementById("nodeStatusText");

  if (!events.length) {
    if (traffic) traffic.textContent = "0";
    if (topTraffic) topTraffic.textContent = "0 req/sec";
    if (topRisk) topRisk.textContent = "Risk Score: 0";
    if (aggRisk) aggRisk.textContent = "0";
    if (latency) latency.textContent = "0";
    if (neutral) neutral.textContent = "100.00";
    if (shadow) shadow.textContent = "0";
    if (node) node.textContent = "NODE_ALPHA: OFFLINE";
    return;
  }

  const avgRisk = events.slice(0, 10).reduce((sum, e) => sum + Number(e.risk), 0) / Math.min(events.length, 10);
  const highRisk = events.filter((e) => Number(e.risk) > 60).length;

  const req = 68000 + highRisk * 100 + Math.floor(Math.random() * 12000);
  const lat = (10 + highRisk * 0.05 + Math.random() * 8).toFixed(1);
  const neu = Math.max(97.7, 100 - highRisk * 0.02).toFixed(2);
  const shadowCount = 1100 + highRisk * 3 + Math.floor(Math.random() * 80);

  if (traffic) traffic.textContent = fmtNumber(req);
  if (topTraffic) topTraffic.textContent = `${Math.round(req / 1000)}k req/sec`;
  if (topRisk) topRisk.textContent = `Risk Score: ${avgRisk.toFixed(1)}`;
  if (aggRisk) aggRisk.textContent = avgRisk.toFixed(1);
  if (latency) latency.textContent = lat;
  if (neutral) neutral.textContent = neu;
  if (shadow) shadow.textContent = fmtNumber(shadowCount);
  if (node) node.textContent = `NODE_ALPHA: ${state.backendAvailable ? "ACTIVE" : "OFFLINE"} [${lat}ms]`;
}

function renderScenarioState() {
  const stateLabel = document.getElementById("scenarioState");
  const btn = document.getElementById("scenarioBtn");
  if (!stateLabel || !btn) return;

  btn.disabled = false;
  if (state.running) {
    stateLabel.textContent = "Running";
    stateLabel.className = "font-label text-[10px] uppercase tracking-widest text-secondary";
    btn.textContent = "Stop Live Attack Scenario";
    btn.onclick = stopLiveAttack;
  } else {
    stateLabel.textContent = "Stopped";
    stateLabel.className = "font-label text-[10px] uppercase tracking-widest text-tertiary";
    btn.textContent = "Start Live Attack Scenario";
    btn.onclick = startLiveAttack;
  }
}

function updateBackendStatus() {
  const servicesList = [
    { id: "behaviorAgent", label: "Behavior Agent" },
    { id: "orchestrator", label: "Orchestrator" },
    { id: "deceptionAgent", label: "Deception Agent" },
    { id: "threatIntel", label: "Threat Intel" }
  ];

  for (const service of servicesList) {
    const elem = document.getElementById(`service-${service.id}`);
    if (elem) {
      const isHealthy = state.backendServices[service.id] || false;
      elem.className = `text-xs font-label uppercase tracking-wider ${isHealthy ? "text-secondary" : "text-tertiary"}`;
      elem.textContent = isHealthy ? "✓ HEALTHY" : "✗ OFFLINE";
    }
  }

  // Update backend status label
  const backendStatus = document.getElementById("backendStatus");
  if (backendStatus) {
    const allHealthy = Object.values(state.backendServices).every(v => v);
    backendStatus.className = `text-xs font-label uppercase tracking-wider ${allHealthy ? "text-secondary" : "text-tertiary"}`;
    backendStatus.textContent = allHealthy ? "✓ ALL SERVICES HEALTHY" : "✗ SOME SERVICES OFFLINE";
  }
}

function renderModuleView(events) {
  const stream = document.getElementById("moduleStream");
  const risk = document.getElementById("moduleRisk");
  const total = document.getElementById("moduleEvents");
  const scenario = document.getElementById("moduleScenario");

  if (!stream) return;

  const streamHtml = events
    .slice(0, 8)
    .map((e) => {
      const color = riskColorClass(Number(e.risk));
      return `<div class="py-2 border-b border-outline-variant/10 last:border-0">
        <div class="flex justify-between items-start gap-4 mb-1">
          <span class="font-label text-[10px] text-on-surface-variant">${e.time}</span>
          <span class="${color} font-bold">${Number(e.risk).toFixed(0)}</span>
        </div>
        <p class="text-xs leading-snug">${e.user_id} @ ${e.ip} <span class="text-on-surface-variant/60">${e.attack}</span></p>
      </div>`;
    })
    .join("");

  stream.innerHTML = streamHtml;

  if (risk && events.length > 0) {
    const avgRisk = events.slice(0, 10).reduce((sum, e) => sum + Number(e.risk), 0) / Math.min(events.length, 10);
    risk.textContent = avgRisk.toFixed(1);
  }

  if (total) total.textContent = fmtNumber(events.length);
  if (scenario) scenario.textContent = state.running ? "ACTIVE" : "IDLE";
}

function updateAllViews() {
  renderRiskTable(state.events);
  renderKpis(state.events);
  renderScenarioState();
  renderModuleView(state.events);
  updateBackendStatus();
}

// Initialize
async function initialize() {
  console.log("Initializing CIVA Dashboard...");
  
  // Connect to WebSocket
  connectWebSocket();
  
  // Fetch initial events
  await fetchEvents();
  
  // Poll backend status
  await pollBackendStatus();
  
  // Fetch Prometheus metrics
  await fetchPrometheusMetrics();
  
  // Get current scenario status
  await getScenarioStatus();
  
  // Setup polling intervals
  setInterval(pollBackendStatus, 5000); // Poll every 5s
  setInterval(fetchPrometheusMetrics, 10000); // Fetch metrics every 10s
  setInterval(getScenarioStatus, 2000); // Check scenario status every 2s
  
  // Setup button handlers
  const scenarioBtn = document.getElementById("scenarioBtn");
  if (scenarioBtn) {
    scenarioBtn.onclick = () => {
      if (state.running) stopLiveAttack();
      else startLiveAttack();
    };
  }
  
  // Add attack buttons
  const attackButtons = document.querySelectorAll('[data-attack-type]');
  for (const btn of attackButtons) {
    const attackType = btn.dataset.attackType;
    btn.onclick = async () => {
      btn.disabled = true;
      btn.textContent = "Executing...";
      const success = await executeAttack(attackType);
      btn.disabled = false;
      btn.textContent = success ? "Attack Sent" : "Failed";
      setTimeout(() => {
        btn.textContent = `Execute ${attackType}`;
      }, 2000);
    };
  }
  
  // Initial render
  updateAllViews();
  
  console.log("CIVA Dashboard initialized");
}

// Start initialization when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initialize);
} else {
  initialize();
}
