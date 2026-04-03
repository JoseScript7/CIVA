const state = {
  backendAvailable: false,
  running: false,
  events: [],
  currentView: "sentinel"
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
  const res = await fetch(path, {
    method: opts.method || "GET",
    headers: { "Content-Type": "application/json" },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json();
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

  if (!events.length) return;

  const avgRisk = events.slice(0, 10).reduce((sum, e) => sum + Number(e.risk), 0) / Math.min(events.length, 10);
  const highRisk = events.filter((e) => Number(e.risk) > 60).length;

  const req = 68000 + Math.floor(Math.random() * 12000) + highRisk * 10;
  const lat = (10 + Math.random() * 8 + highRisk * 0.03).toFixed(1);
  const neu = Math.max(97.7, 100 - highRisk * 0.02).toFixed(2);
  const shadowCount = 1100 + highRisk * 3 + Math.floor(Math.random() * 80);

  if (traffic) traffic.textContent = fmtNumber(req);
  if (topTraffic) topTraffic.textContent = `${Math.round(req / 1000)}k req/sec`;
  if (topRisk) topRisk.textContent = `Risk Score: ${avgRisk.toFixed(1)}`;
  if (aggRisk) aggRisk.textContent = avgRisk.toFixed(1);
  if (latency) latency.textContent = lat;
  if (neutral) neutral.textContent = neu;
  if (shadow) shadow.textContent = fmtNumber(shadowCount);
  if (node) node.textContent = `NODE_ALPHA: ACTIVE [${lat}ms]`;
}

function renderScenarioState() {
  const stateLabel = document.getElementById("scenarioState");
  const btn = document.getElementById("scenarioBtn");
  if (!stateLabel || !btn) return;

  if (!state.backendAvailable) {
    stateLabel.textContent = "Backend offline";
    stateLabel.className = "font-label text-[10px] uppercase tracking-widest text-tertiary";
    btn.textContent = "Backend Offline";
    btn.disabled = true;
    return;
  }

  btn.disabled = false;
  if (state.running) {
    stateLabel.textContent = "Running";
    stateLabel.className = "font-label text-[10px] uppercase tracking-widest text-secondary";
    btn.textContent = "Stop Live Attack Scenario";
  } else {
    stateLabel.textContent = "Stopped";
    stateLabel.className = "font-label text-[10px] uppercase tracking-widest text-tertiary";
    btn.textContent = "Start Live Attack Scenario";
  }
}

function renderModuleView(events) {
  const stream = document.getElementById("moduleStream");
  const risk = document.getElementById("moduleRisk");
  const total = document.getElementById("moduleEvents");
  const scenario = document.getElementById("moduleScenario");
  const action = document.getElementById("moduleAction");
  if (!stream) return;

  const recent = events.slice(0, 24);
  const threatCounts = {};
  events.forEach((e) => {
    threatCounts[e.attack] = (threatCounts[e.attack] || 0) + 1;
  });

  let html = "";
  if (state.currentView === "behavior") {
    const avgRisk = recent.length ? recent.reduce((s, e) => s + Number(e.risk), 0) / recent.length : 0;
    const anomalyCount = recent.filter((e) => Number(e.risk) > 75).length;
    const sagemakerLatency = (8 + avgRisk / 6).toFixed(1);
    const leftLogs = recent.slice(0, 12);
    html = `<div class="grid grid-cols-1 xl:grid-cols-2 gap-6 min-h-[720px]">
      <section class="border border-outline-variant/10 bg-surface-container-lowest rounded-lg overflow-hidden flex flex-col">
        <div class="p-4 border-b border-outline-variant/10 flex justify-between items-center bg-surface">
          <div class="flex items-center gap-3"><span class="material-symbols-outlined text-primary">security</span><h2 class="font-headline text-sm font-bold uppercase tracking-wider">Real-time Sentinel Feed</h2></div>
          <div class="flex gap-2"><span class="px-2 py-0.5 bg-primary/10 text-primary font-label text-[10px] rounded">KAFKA_STREAMING</span><span class="px-2 py-0.5 bg-surface-variant text-on-surface-variant font-label text-[10px] rounded">SEC_OPS_01</span></div>
        </div>
        <div class="flex-1 overflow-y-auto p-4 font-label text-xs space-y-2">
          ${leftLogs.map((e) => `<div class="p-3 border-l-2 ${Number(e.risk) > 75 ? "border-tertiary/40 bg-tertiary/5" : "border-primary/40 bg-surface-container-low/30"} hover:bg-surface-container-low transition-colors group"><div class="flex justify-between text-on-surface-variant mb-1"><span class="${Number(e.risk) > 75 ? "text-tertiary" : "text-primary-fixed-dim"}">${e.time}</span><span class="${Number(e.risk) > 75 ? "text-tertiary font-bold" : "text-secondary"}">${Number(e.risk) > 75 ? "ANOMALY_DETECTED" : "REQ_PROCESSED"}</span></div><div class="grid grid-cols-2 gap-x-4 gap-y-1"><div><span class="text-outline">IP:</span> <span class="text-on-surface">${e.ip}</span></div><div><span class="text-outline">JWT_SUB:</span> <span class="text-on-surface">${e.user_id}</span></div><div><span class="text-outline">ATTACK:</span> <span class="text-on-surface">${e.attack}</span></div><div><span class="text-outline">SCORE:</span> <span class="${riskColorClass(Number(e.risk))}">${Number(e.risk).toFixed(1)}</span></div></div></div>`).join("")}
        </div>
        <div class="p-3 bg-surface-container-low border-t border-outline-variant/20 flex items-center gap-3 font-label text-xs"><span class="text-secondary">$</span><input class="bg-transparent border-none focus:ring-0 text-on-surface flex-1 placeholder:text-outline/40" placeholder="Filter signals (e.g. geo:'US' score>50)..." type="text"/><span class="text-outline/40">CTRL + K</span></div>
      </section>
      <section class="overflow-y-auto p-2 bg-surface grid grid-cols-6 grid-rows-12 gap-4">
        <div class="col-span-6 row-span-5 glass-panel rounded-lg p-5 flex flex-col">
          <div class="flex justify-between items-start mb-6"><div><h3 class="font-headline text-lg font-bold">Behavior ML Anomaly Graph</h3><p class="text-xs text-on-surface-variant">Baseline (TimescaleDB) vs Current Request Pattern</p></div><div class="flex gap-4 font-label text-[10px]"><div class="flex items-center gap-2"><span class="w-3 h-0.5 bg-outline-variant"></span> BASELINE</div><div class="flex items-center gap-2"><span class="w-3 h-0.5 bg-primary"></span> CURRENT</div></div></div>
          <div class="flex-1 relative mt-2"><svg class="w-full h-full" viewBox="0 0 800 200"><path class="text-outline-variant/30" d="M0,150 Q100,140 200,160 T400,140 T600,155 T800,145" fill="none" stroke="currentColor" stroke-width="2"></path><path class="text-primary" d="M0,150 Q100,130 200,180 T400,110 T600,170 T800,100" fill="none" stroke="currentColor" stroke-width="2"></path><circle class="fill-tertiary" cx="400" cy="110" r="4"></circle><text class="fill-tertiary font-label text-[10px]" x="410" y="100">ANOMALY DETECTED (Δ ${(avgRisk / 100).toFixed(2)})</text></svg></div>
        </div>
        <div class="col-span-3 row-span-4 glass-panel rounded-lg p-5"><h3 class="font-headline text-sm font-bold uppercase tracking-wider mb-4">Risk Distribution</h3><div class="flex items-end gap-1 h-32"><div class="w-full bg-secondary/20 h-[80%] rounded-t-sm"></div><div class="w-full bg-secondary/20 h-[95%] rounded-t-sm"></div><div class="w-full bg-secondary/40 h-[60%] rounded-t-sm"></div><div class="w-full bg-primary/40 h-[30%] rounded-t-sm"></div><div class="w-full bg-tertiary/40 h-[10%] rounded-t-sm"></div><div class="w-full bg-tertiary h-[15%] rounded-t-sm"></div><div class="w-full bg-tertiary/20 h-[5%] rounded-t-sm"></div></div><div class="flex justify-between mt-2 font-label text-[10px] text-outline"><span>LOW</span><span>MED</span><span>HIGH</span></div><div class="mt-4 pt-4 border-t border-outline-variant/10"><div class="flex justify-between text-xs"><span class="text-on-surface-variant">Active Sessions:</span><span class="font-label text-primary">${fmtNumber(events.length * 160 + anomalyCount)}</span></div></div></div>
        <div class="col-span-3 row-span-4 glass-panel rounded-lg p-5 flex flex-col"><div class="flex justify-between items-center mb-4"><h3 class="font-headline text-sm font-bold uppercase tracking-wider">SageMaker Status</h3><div class="w-2 h-2 rounded-full bg-secondary status-pulse"></div></div><div class="space-y-4 flex-1 flex flex-col justify-center"><div class="flex justify-between items-baseline"><span class="text-[10px] text-on-surface-variant font-label uppercase">Avg Latency</span><span class="text-2xl font-headline font-bold text-primary">${sagemakerLatency}ms</span></div><div class="w-full bg-surface-container-lowest h-1.5 rounded-full overflow-hidden"><div class="bg-primary h-full w-[85%]"></div></div><div class="grid grid-cols-2 gap-2 text-[10px] font-label"><div class="p-2 bg-surface-container-lowest rounded"><div class="text-outline">UPTIME</div><div class="text-on-surface">99.998%</div></div><div class="p-2 bg-surface-container-lowest rounded"><div class="text-outline">MODEL</div><div class="text-on-surface">XG-SENT-V4</div></div></div></div></div>
        <div class="col-span-4 row-span-3 bg-surface-container rounded-lg overflow-hidden relative group"><img class="w-full h-full object-cover opacity-40 grayscale group-hover:grayscale-0 transition-all duration-700" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDuixsxOCSprCC0XpDBq_WMbI1Xg5aDYaVi596X5wR-rE5EVhD-aMYyDLgu7Xsn5Unxjb3MynN0ZqlJS40cnMCnuplkZJIM2AxUam8BzAzFa1F-2gpxijMWIV-SX6XxVFo5YbLaiWWPe1jLgEoHxdkXfb7eR8k1-dav5rVnaJk8IHWXP8_Xzd6tebpoCBb925By9rYYMaxbLICTJdooBxjRWV-Re9LcnIhS9h1Gvll6h2pJmYXMLuz1JHmupGTehysVeH07Ro_AS1aU" alt="Global Security Map"/><div class="absolute inset-0 bg-gradient-to-t from-surface to-transparent p-4 flex flex-col justify-end"><span class="font-label text-[10px] text-primary">LIVE GEOLOCATION TRAFFIC</span><h4 class="font-headline text-lg font-bold">Signal Extraction Origin</h4></div></div>
        <div class="col-span-2 row-span-3 glass-panel rounded-lg p-4 flex flex-col justify-between"><div class="flex items-center gap-2"><span class="material-symbols-outlined text-tertiary text-sm">warning</span><span class="font-headline text-xs font-bold uppercase tracking-widest text-tertiary">Alert Queue</span></div><div><div class="text-3xl font-headline font-bold">${anomalyCount}</div><div class="text-[10px] font-label text-outline uppercase tracking-wider">Unresolved Events</div></div><button class="w-full py-2 bg-surface-container-highest hover:bg-surface-variant text-[10px] font-bold font-label uppercase tracking-widest transition-colors rounded">Review All</button></div>
      </section>
    </div>`;
  } else if (state.currentView === "orchestrator") {
    const decision = { ALLOW: 0, MFA: 0, DECEPTION: 0, KILL: 0 };
    events.forEach((e) => {
      decision[e.action] = (decision[e.action] || 0) + 1;
    });
    const topIp = recent[0]?.ip || "-";
    html = `<div class="space-y-8">
      <div class="mb-2 flex justify-between items-end"><div><h2 class="text-3xl font-bold font-headline tracking-tight text-on-surface">Orchestration <span class="text-primary">&amp;</span> Deception</h2><p class="text-on-surface-variant font-body">Policy enforcement layer and active counter-intelligence monitoring.</p></div><div class="glass-panel px-4 py-2 rounded-lg flex flex-col items-end"><span class="text-[10px] font-label text-on-surface-variant uppercase tracking-tighter">Active Deceptive Nodes</span><span class="text-xl font-headline font-bold text-secondary">${decision.DECEPTION + decision.KILL} / 500</span></div></div>
      <div class="grid grid-cols-12 gap-6">
        <div class="col-span-12 lg:col-span-8 space-y-6">
          <div class="grid grid-cols-3 gap-6">
            <div class="bg-surface-container rounded-lg p-6 relative overflow-hidden group"><div class="relative z-10"><span class="font-label text-xs text-on-surface-variant uppercase mb-2 block">Attacker Dwell Time</span><div class="text-3xl font-headline font-bold text-on-surface">${Math.max(3, Math.round((decision.DECEPTION + decision.KILL) * 0.7))}m ${String(Math.floor(Math.random() * 59)).padStart(2, "0")}s</div><div class="flex items-center gap-2 mt-2"><span class="material-symbols-outlined text-secondary text-sm">trending_up</span><span class="text-xs text-secondary font-label">+12% vs last 24h</span></div></div></div>
            <div class="bg-surface-container rounded-lg p-6 relative overflow-hidden group"><div class="relative z-10"><span class="font-label text-xs text-on-surface-variant uppercase mb-2 block">Honeypot Hit Rate</span><div class="text-3xl font-headline font-bold text-on-surface">${(84 + Math.min(15, decision.DECEPTION / 10)).toFixed(1)}%</div><div class="flex items-center gap-2 mt-2"><span class="material-symbols-outlined text-secondary text-sm">check_circle</span><span class="text-xs text-secondary font-label">Optimal Efficiency</span></div></div></div>
            <div class="bg-surface-container rounded-lg p-6 relative overflow-hidden group"><div class="relative z-10"><span class="font-label text-xs text-on-surface-variant uppercase mb-2 block">Shadow Pivot Success</span><div class="text-3xl font-headline font-bold text-on-surface">${fmtNumber(decision.DECEPTION * 11 + decision.KILL * 7 + 50)}</div><div class="flex items-center gap-2 mt-2"><span class="material-symbols-outlined text-tertiary text-sm">priority_high</span><span class="text-xs text-tertiary font-label">Requires Review</span></div></div></div>
          </div>
          <section class="bg-surface-container rounded-lg overflow-hidden">
            <div class="px-6 py-4 border-b border-outline-variant/15 flex justify-between items-center bg-surface-container-high/50"><h3 class="font-headline font-bold text-lg">Orchestrator Policy Ruleset</h3><button class="text-xs font-label text-primary hover:underline">New Rule +</button></div>
            <div class="p-6 space-y-4">
              <div class="flex items-center justify-between p-4 bg-surface-container-low border border-outline-variant/10 rounded-sm"><div class="flex items-center gap-4"><div class="w-10 h-10 rounded flex items-center justify-center bg-primary/10 text-primary"><span class="material-symbols-outlined">rule</span></div><div><div class="font-headline font-medium text-on-surface">Critical Escalation</div><div class="font-label text-xs text-on-surface-variant">IF Risk Score &gt; 85 THEN Isolator.Strict()</div></div></div><div class="flex items-center gap-8"><div class="text-right"><span class="text-[10px] font-label text-on-surface-variant uppercase block">Hits (24h)</span><span class="font-label text-sm text-on-surface">${decision.KILL}</span></div><div class="bg-secondary/20 text-secondary px-3 py-1 text-[10px] font-bold rounded-full uppercase tracking-widest">Active</div></div></div>
              <div class="flex items-center justify-between p-4 bg-surface-container-low border border-outline-variant/10 rounded-sm"><div class="flex items-center gap-4"><div class="w-10 h-10 rounded flex items-center justify-center bg-tertiary/10 text-tertiary"><span class="material-symbols-outlined">psychology</span></div><div><div class="font-headline font-medium text-on-surface">Deceptive Pivot</div><div class="font-label text-xs text-on-surface-variant">IF Anomalous_SQL_Pattern THEN Deception.Mirror()</div></div></div><div class="flex items-center gap-8"><div class="text-right"><span class="text-[10px] font-label text-on-surface-variant uppercase block">Hits (24h)</span><span class="font-label text-sm text-on-surface">${decision.DECEPTION}</span></div><div class="bg-secondary/20 text-secondary px-3 py-1 text-[10px] font-bold rounded-full uppercase tracking-widest">Active</div></div></div>
              <div class="flex items-center justify-between p-4 bg-surface-container-low border border-outline-variant/10 rounded-sm border-l-4 border-l-tertiary"><div class="flex items-center gap-4"><div class="w-10 h-10 rounded flex items-center justify-center bg-tertiary/10 text-tertiary"><span class="material-symbols-outlined">security_update_warning</span></div><div><div class="font-headline font-medium text-on-surface">Persistent Surveillance</div><div class="font-label text-xs text-on-surface-variant">Score &gt; 60 -&gt; Activate Deception</div></div></div><div class="flex items-center gap-8"><div class="text-right"><span class="text-[10px] font-label text-on-surface-variant uppercase block">Hits (24h)</span><span class="font-label text-sm text-on-surface">${decision.DECEPTION + decision.MFA}</span></div><div class="bg-secondary/20 text-secondary px-3 py-1 text-[10px] font-bold rounded-full uppercase tracking-widest">Active</div></div></div>
            </div>
          </section>
        </div>
        <div class="col-span-12 lg:col-span-4 space-y-6">
          <section class="bg-surface-container rounded-lg overflow-hidden border border-tertiary/20"><div class="px-6 py-4 border-b border-tertiary/15 flex items-center gap-2 bg-tertiary/5"><span class="w-2 h-2 rounded-full bg-tertiary animate-pulse"></span><h3 class="font-headline font-bold text-lg text-tertiary">Active Shadow Sessions</h3></div><div class="p-4 space-y-2 max-h-[400px] overflow-y-auto">${recent.slice(0, 6).map((e, i) => `<div class="${i === 0 ? "bg-surface-container-high border-l-2 border-tertiary" : "bg-surface-container-low border-l-2 border-outline-variant"} p-4 rounded-sm cursor-pointer hover:bg-surface-container-high transition-all group"><div class="flex justify-between items-start mb-2"><span class="font-label text-xs ${i === 0 ? "text-primary" : "text-on-surface-variant"}">${e.id}</span><span class="text-[10px] font-label ${i === 0 ? "text-tertiary bg-tertiary/10 px-2 py-0.5 rounded" : "text-on-surface-variant/50"}">${i === 0 ? "LIVE FEED" : "IDLE"}</span></div><div class="text-[10px] font-label text-on-surface-variant/70 mb-3 uppercase tracking-tighter">Attacker IP: ${e.ip}</div><div class="text-[10px] font-label ${i === 0 ? "text-tertiary/70" : "italic text-on-surface-variant/40"}">${i === 0 ? `${e.time} ${e.attack} ${e.action}` : "Waiting for next tactical interaction..."}</div></div>`).join("")}</div><div class="p-4 bg-tertiary-container/5 border-t border-tertiary/10"><button class="w-full text-center font-label text-[10px] text-tertiary uppercase tracking-widest hover:brightness-125 transition-all">View All Active Intercepts</button></div></section>
          <section class="bg-surface-container rounded-lg overflow-hidden border border-outline-variant/20 shadow-lg"><div class="px-6 py-4 border-b border-outline-variant/15 flex items-center justify-between bg-surface-container-highest/20"><div class="flex items-center gap-2"><span class="material-symbols-outlined text-tertiary text-sm">database</span><h3 class="font-label font-bold text-xs uppercase tracking-widest">Redis Key-State Lookup</h3></div><span class="font-label text-[10px] text-secondary">0.4ms latency</span></div><div class="p-4"><div class="relative mb-4"><input class="w-full bg-surface-container-lowest border-none focus:ring-1 focus:ring-primary rounded-sm text-xs font-label text-on-surface py-2 pl-8" placeholder="HGET session:risk_score..." type="text"/><span class="material-symbols-outlined absolute left-2 top-2 text-sm text-on-surface-variant/50">search</span></div><div class="space-y-3"><div class="flex justify-between items-center text-[10px] font-label"><span class="text-on-surface-variant">node_cluster:primary</span><span class="text-secondary font-bold">STABLE</span></div><div class="bg-surface-container-lowest p-3 rounded font-label text-[11px] space-y-1"><div class="flex justify-between"><span class="text-primary/70">curr_connections</span><span class="text-on-surface">${fmtNumber(events.length * 53 + 1200)}</span></div><div class="flex justify-between"><span class="text-primary/70">keys_evicted_24h</span><span class="text-on-surface">${decision.KILL + 20}</span></div><div class="flex justify-between"><span class="text-primary/70">mem_usage</span><span class="text-on-surface">${(3 + decision.DECEPTION / 200).toFixed(2)}GB</span></div></div><button class="w-full bg-surface-container-high py-2 text-[10px] font-label uppercase tracking-widest text-on-surface-variant hover:text-on-surface border border-outline-variant/20 transition-all">Flush Non-Active Buffer</button></div></div></section>
        </div>
      </div>
      <section class="mt-2 bg-surface-container rounded-lg overflow-hidden"><div class="px-6 py-3 border-b border-outline-variant/15 flex items-center justify-between bg-surface-container-low"><span class="font-label text-xs font-bold uppercase tracking-widest">System Log Stream</span><span class="font-label text-[10px] text-on-surface-variant/60">Filtered: Deception_Layer</span></div><div class="p-4 bg-surface-container-lowest font-label text-[11px] h-40 overflow-y-auto space-y-1 leading-relaxed">${recent.slice(0, 8).map((e) => `<div class="${Number(e.risk) > 80 ? "text-tertiary" : "text-on-surface-variant"}"><span class="text-secondary">[${e.time}]</span> ORCH_CORE: ${e.id} routed for ${e.action} (${e.attack}) from ${e.ip}.</div>`).join("")}</div></section>
    </div>`;
  } else if (state.currentView === "deception") {
    const decoys = recent.filter((e) => e.action === "DECEPTION" || e.action === "KILL");
    const active = decoys.length ? decoys : recent.slice(0, 8);
    const avgRisk = active.length
      ? active.reduce((s, e) => s + Number(e.risk), 0) / active.length
      : 0;
    const dwell = `${Math.max(2, Math.round(avgRisk / 4))}m ${String(Math.floor(Math.random() * 59)).padStart(2, "0")}s`;
    html = `<div class="space-y-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="bg-surface-container p-5 rounded-md border-l-2 border-primary shadow-lg">
          <p class="text-xs font-label text-slate-500 uppercase mb-2">Total Shadow Sessions</p>
          <div class="flex items-end gap-3"><span class="text-3xl font-bold font-headline text-on-surface">${active.length}</span><span class="text-[10px] text-secondary font-label pb-1.5">LIVE</span></div>
        </div>
        <div class="bg-surface-container p-5 rounded-md border-l-2 border-secondary shadow-lg">
          <p class="text-xs font-label text-slate-500 uppercase mb-2">Honeypot Hits</p>
          <div class="flex items-end gap-3"><span class="text-3xl font-bold font-headline text-on-surface">${fmtNumber(events.length * 23 + active.length * 7)}</span><span class="text-[10px] text-slate-400 font-label pb-1.5">LAST 24H</span></div>
        </div>
        <div class="bg-surface-container p-5 rounded-md border-l-2 border-primary shadow-lg">
          <p class="text-xs font-label text-slate-500 uppercase mb-2">Attacker Dwell Time</p>
          <div class="flex items-end gap-3"><span class="text-3xl font-bold font-headline text-on-surface">${dwell}</span><span class="text-[10px] text-primary font-label pb-1.5">AVG PEAK</span></div>
        </div>
        <div class="bg-surface-container p-5 rounded-md border-l-2 border-secondary shadow-lg">
          <p class="text-xs font-label text-slate-500 uppercase mb-2">Data Consistency</p>
          <div class="flex items-end gap-3"><span class="text-3xl font-bold font-headline text-secondary">${(99 - Math.min(1.8, avgRisk / 140)).toFixed(1)}%</span><span class="text-[10px] text-slate-400 font-label pb-1.5">SYNCED</span></div>
        </div>
      </div>
      <div class="grid grid-cols-12 gap-6">
        <div class="col-span-12 lg:col-span-7 space-y-6">
          <div class="flex items-center justify-between mb-1">
            <h3 class="font-headline text-xl text-on-surface flex items-center gap-2"><span class="material-symbols-outlined text-primary">grid_view</span>Active Shadow Sessions</h3>
            <div class="flex gap-2"><span class="px-3 py-1 bg-surface-container-high rounded text-[10px] font-label text-primary uppercase">Filter: High Risk</span><span class="px-3 py-1 bg-surface-container-high rounded text-[10px] font-label text-slate-400 uppercase">Sort: Dwell Time</span></div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            ${active.slice(0, 4).map((e, i) => `<div class="bg-surface-container p-4 rounded-lg relative overflow-hidden group hover:bg-surface-container-high transition-all ${Number(e.risk) >= 80 ? "ring-1 ring-tertiary/50" : ""}">
              ${Number(e.risk) >= 80 ? '<div class="absolute inset-0 bg-tertiary/5 pointer-events-none"></div>' : ""}
              <div class="flex flex-col gap-3">
                <div class="flex items-center gap-3"><div class="w-10 h-10 bg-slate-800 rounded flex items-center justify-center font-label text-primary">#${String(i + 1).padStart(2, "0")}</div><div><h4 class="font-headline font-bold text-sm">Target: ${e.attack.replace(/_/g, "-")}</h4><p class="text-[10px] font-label text-slate-500">IP: ${e.ip}</p></div></div>
                <div class="flex justify-between items-center py-2 border-y border-white/5"><span class="text-[10px] font-label text-slate-400">Activity: ${e.action}</span><span class="text-[10px] font-label text-secondary">${Math.max(1, Math.round(Number(e.risk) / 8))}:${String(Math.floor(Math.random() * 59)).padStart(2, "0")} Dwell</span></div>
                <div class="flex gap-2 mt-1"><div class="h-1 flex-1 bg-surface-container-lowest rounded-full overflow-hidden"><div class="h-full ${Number(e.risk) >= 80 ? "bg-tertiary" : Number(e.risk) >= 60 ? "bg-primary" : "bg-secondary"}" style="width:${Math.min(100, Math.round(Number(e.risk)))}%"></div></div><span class="text-[10px] font-label ${riskColorClass(Number(e.risk))}">${Number(e.risk) >= 80 ? "Awareness: High" : Number(e.risk) >= 60 ? "Awareness: Med" : "Awareness: Low"}</span></div>
              </div>
            </div>`).join("")}
          </div>
          <div class="bg-surface-container rounded-lg overflow-hidden h-52 relative border border-white/5">
            <div class="absolute inset-0 opacity-40 mix-blend-screen grayscale contrast-150"><img class="w-full h-full object-cover" data-location="Global" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDVIgg57rdcaVL_HfcGM-YPWLIDrfrLyxzNylSEAT2UG7hddxRUdhKGIaJUPk5vmWPUbj1HL-yvmoQnFpqyl5CM8hEUkKtfR_1lU8LLOMEoi-meNZV2msB6zEuwWBVGHbmeOZ5jq_K4lqMkVVqom8vbTFzrIIaoIkJejqpgXERoE1HZidzqcLX2VO_rVL2O-83lKgV2tU5GEC2BkLtne6ZVeQ5eY_4FH2WtZ-QgbGQRq4gNqVrIDUOcdJgQQWUwS1CPlPLfoHYMC0Lk"/></div>
            <div class="absolute inset-0 bg-gradient-to-t from-surface to-transparent"></div>
            <div class="absolute bottom-4 left-4 flex flex-col"><span class="text-[10px] font-label text-primary uppercase">Geospatial Distribution</span><span class="text-xs text-slate-300 font-headline">${active.length} Incoming Connections Under Deception</span></div>
          </div>
        </div>
        <div class="col-span-12 lg:col-span-5 flex flex-col">
          <div class="bg-slate-950 rounded-xl overflow-hidden flex flex-col h-full border border-white/10 shadow-2xl">
            <div class="bg-slate-900 px-4 py-3 flex items-center justify-between border-b border-white/5"><div class="flex items-center gap-3"><div class="flex gap-1.5"><div class="w-2.5 h-2.5 rounded-full bg-error/20 border border-error/40"></div><div class="w-2.5 h-2.5 rounded-full bg-primary/20 border border-primary/40"></div><div class="w-2.5 h-2.5 rounded-full bg-secondary/20 border border-secondary/40"></div></div><span class="text-xs font-label text-slate-400">SESSION_INTERCEPT [LIVE]</span></div><span class="text-[10px] font-label text-primary px-2 py-0.5 bg-primary/10 rounded">LIVE_CAPTURE</span></div>
            <div class="flex-1 p-4 font-label text-sm leading-relaxed overflow-y-auto terminal-scroll bg-black/40">
              ${recent.slice(0, 10).map((e, i) => `<div class="mb-3"><span class="text-slate-600">[${e.time}]</span> <span class="text-primary">system@decoy:~$</span> <span class="text-on-surface">${i % 2 ? "cat /opt/secure/vault/master_keys.enc" : "ls -la /opt/secure/vault"}</span><br/><span class="${riskColorClass(Number(e.risk))}">${e.id} | ${e.attack} | ${e.action}</span></div>`).join("")}
            </div>
            <div class="p-4 bg-slate-900/50 border-t border-white/5 flex items-center gap-3"><span class="material-symbols-outlined text-slate-500 text-sm">emergency_home</span><div class="flex-1 bg-slate-950 px-3 py-2 rounded border border-white/10 text-xs text-slate-500 font-label">Monitoring stream... Manual intercept disabled by Agent 4 policy.</div><button data-action="start-stop-scenario" class="px-4 py-2 bg-primary text-on-primary text-xs font-bold rounded shadow-lg glow-on-hover">FORGE RESPONSE</button></div>
          </div>
        </div>
      </div>
    </div>`;
  } else if (state.currentView === "threat-intel") {
    const topAttacks = Object.entries(threatCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3);
    const modelDrift = (0.01 + Math.min(0.09, (recent.filter((e) => e.action === "MFA").length / Math.max(1, recent.length)) / 10)).toFixed(2);
    const retrainCount = recent.filter((e) => e.action === "MFA" || Number(e.risk) > 70).length * 4 + 12;
    html = `<div class="space-y-6">
      <div class="grid grid-cols-12 gap-6">
        <div class="col-span-8"><h2 class="text-3xl font-bold font-headline tracking-tight text-on-surface mb-2">Threat Intel &amp; Forensics</h2><p class="text-on-surface-variant max-w-2xl">Real-time NLP attack classification and long-term forensic auditing. Data synchronized with SIEM endpoints and neural feedback loops.</p></div>
        <div class="col-span-4 flex items-end justify-end gap-4"><div class="p-4 bg-surface-container rounded-lg border-l-2 border-secondary flex flex-col"><span class="text-[10px] font-label text-on-surface-variant uppercase tracking-widest">Model Drift</span><span class="text-2xl font-bold font-headline text-secondary">${modelDrift}%</span></div><div class="p-4 bg-surface-container rounded-lg border-l-2 border-primary flex flex-col"><span class="text-[10px] font-label text-on-surface-variant uppercase tracking-widest">SIEM Sync</span><span class="text-2xl font-bold font-headline text-primary">Active</span></div></div>
      </div>
      <div class="grid grid-cols-12 gap-6">
        <div class="col-span-12 lg:col-span-7 p-6 bg-surface-container-low rounded-xl relative overflow-hidden group">
          <div class="absolute top-0 right-0 p-8 opacity-5"><span class="material-symbols-outlined text-[120px]">psychology</span></div>
          <div class="flex items-center justify-between mb-6"><h3 class="text-lg font-bold font-headline flex items-center gap-2"><span class="material-symbols-outlined text-primary">neurology</span>NLP Classification Engine</h3><span class="px-2 py-1 bg-primary/10 text-primary text-[10px] font-label rounded">HuggingFace Optimized</span></div>
          <div class="space-y-4">
            ${topAttacks.map(([attack, n], i) => {
              const confidence = (96.1 - i * 1.7).toFixed(1);
              const width = Math.min(92, 24 + n * 8);
              const tone = i === 0 ? "tertiary" : i === 1 ? "primary" : "secondary";
              return `<div class="flex items-center gap-4 p-3 bg-surface-container hover:bg-surface-container-high transition-colors rounded border border-outline-variant/10"><div class="w-1.5 h-8 bg-${tone} rounded-full"></div><div class="flex-1"><div class="flex justify-between items-center mb-1"><span class="text-sm font-semibold">${attack}</span><span class="text-xs font-label text-on-surface-variant">${confidence}% Confidence</span></div><div class="w-full h-1 bg-surface-container-lowest rounded-full"><div class="h-full bg-${tone} rounded-full" style="width:${width}%"></div></div></div><div class="text-right"><span class="text-lg font-bold">${n}</span><p class="text-[10px] text-on-surface-variant">Last Window</p></div></div>`;
            }).join("") || '<div class="text-xs text-on-surface-variant">No classification data yet</div>'}
          </div>
        </div>
        <div class="col-span-12 lg:col-span-5 p-6 bg-surface-container-low rounded-xl border border-outline-variant/5">
          <h3 class="text-lg font-bold font-headline mb-6 flex items-center gap-2"><span class="material-symbols-outlined text-secondary">sync_alt</span>Agent 2 Retraining Queue</h3>
          <div class="flex flex-col items-center justify-center py-8 bg-surface-container-lowest rounded-lg border border-outline-variant/10 relative">
            <div class="w-32 h-32 rounded-full border-4 border-dashed border-primary/20 flex items-center justify-center"><div class="w-24 h-24 rounded-full bg-primary/5 flex items-center justify-center"><span class="material-symbols-outlined text-4xl text-primary">neurology</span></div></div>
            <div class="mt-6 text-center"><p class="text-sm font-bold">${retrainCount} New Signatures Queued</p><p class="text-xs text-on-surface-variant font-label">Next Epoch: ${String(new Date().getHours()).padStart(2, "0")}:${String(new Date().getMinutes()).padStart(2, "0")}:00</p></div>
          </div>
        </div>
        <div class="col-span-12 lg:col-span-4 p-6 bg-surface-container rounded-xl">
          <h3 class="text-sm font-bold font-headline mb-4 flex items-center justify-between">SIEM Export Status<span class="w-2 h-2 rounded-full bg-secondary"></span></h3>
          <div class="space-y-3">
            ${recent.slice(0, 3).map((e, i) => `<div class="p-3 bg-surface-container-low rounded border border-outline-variant/5"><div class="flex justify-between items-start mb-2"><span class="text-[10px] font-label text-primary">${i === 0 ? "Splunk_Cloud_Prod" : i === 1 ? "Elastic_SIEM_Dev" : "Crowdstrike_Humio"}</span><span class="text-[10px] text-on-surface-variant">${i * 9 + 2}m ago</span></div><p class="text-xs font-medium">Exported: ${e.id}</p><div class="mt-2 flex items-center gap-2"><span class="text-[10px] px-1.5 py-0.5 bg-secondary/10 text-secondary rounded">${i === 2 ? "CSV" : i === 1 ? "SYSLOG" : "JSON-STIX"}</span><span class="text-[10px] text-on-surface-variant">${(Math.random() * 2 + 0.2).toFixed(1)} MB</span></div></div>`).join("")}
          </div>
        </div>
        <div class="col-span-12 lg:col-span-8 p-6 bg-surface-container-low rounded-xl border border-outline-variant/5">
          <div class="flex items-center justify-between mb-6"><h3 class="text-lg font-bold font-headline flex items-center gap-2"><span class="material-symbols-outlined text-primary">folder_zip</span>Forensics Archive (S3)</h3><div class="flex items-center gap-4"><div class="relative"><span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">search</span><input class="bg-surface-container-lowest border-none text-xs rounded-sm pl-9 pr-4 py-2 w-64 focus:ring-1 focus:ring-primary" placeholder="Search logs (IP, ID, Hash)..." type="text"/></div><button class="material-symbols-outlined text-on-surface-variant hover:text-on-surface">filter_list</button></div></div>
          <div class="overflow-x-auto"><table class="w-full text-left text-xs"><thead><tr class="border-b border-outline-variant/10 text-on-surface-variant uppercase tracking-widest font-bold"><th class="pb-3 px-2">Session ID</th><th class="pb-3 px-2">Duration</th><th class="pb-3 px-2">Classification</th><th class="pb-3 px-2">Terminal State</th><th class="pb-3 px-2 text-right">Actions</th></tr></thead><tbody class="divide-y divide-outline-variant/5">${recent.slice(0, 6).map((e) => `<tr class="hover:bg-surface-container transition-colors group"><td class="py-4 px-2"><div class="flex items-center gap-2"><span class="material-symbols-outlined text-sm text-on-surface-variant">description</span><span class="font-label">${e.id}</span></div></td><td class="py-4 px-2 text-on-surface-variant">${Math.max(1, Math.round(Number(e.risk) / 7))}h ${Math.floor(Math.random() * 59)}m</td><td class="py-4 px-2"><span class="px-2 py-0.5 bg-surface-container-high rounded text-[10px] border border-outline-variant/20">${e.attack}</span></td><td class="py-4 px-2"><div class="flex items-center gap-2"><span class="w-1.5 h-1.5 rounded-full ${Number(e.risk) > 80 ? "bg-tertiary" : "bg-secondary"}"></span><span>${Number(e.risk) > 80 ? "Data Leaked (Simulated)" : "Containment Successful"}</span></div></td><td class="py-4 px-2 text-right"><button class="text-primary hover:underline font-bold">REPLAY</button></td></tr>`).join("")}</tbody></table></div>
        </div>
      </div>
    </div>`;
  } else if (state.currentView === "system-settings") {
    const agentCards = [
      { name: "Vanguard-Alpha", id: "AGNT-77-01", metric: "HEURISTIC DEPTH", val: 88, tone: "primary" },
      { name: "Crawler-Sigma", id: "AGNT-22-09", metric: "PACKET BUFFER", val: 42, tone: "secondary" },
      { name: "Logic-Gate-9", id: "AGNT-55-41", metric: "DECRYPTION PWR", val: 95, tone: "primary" },
      { name: "Sentinel-Prime", id: "AGNT-11-04", metric: "STRESS INDEX", val: 78, tone: "tertiary" },
      { name: "Apex-Stalker", id: "AGNT-99-05", metric: "RESPONSE TIME", val: 12, tone: "primary", suffix: "ms" },
    ];
    html = `<div class="space-y-8">
      <section class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="glass-panel p-6 rounded-md col-span-2">
          <div class="flex justify-between items-start mb-6"><div><h2 class="font-headline text-2xl font-bold text-primary tracking-tight">System Core Configuration</h2><p class="text-on-surface-variant text-sm mt-1">Global logic parameters for the CIVA intelligence swarm.</p></div><span class="font-label text-[10px] bg-primary/10 text-primary border border-primary/20 px-2 py-1 rounded">REV: 09-042</span></div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-6 text-xs">
            <div class="space-y-2"><span class="text-xs font-semibold uppercase tracking-widest text-slate-400">Autonomous Mitigation</span><div class="text-[11px] font-label ${state.running ? "text-secondary" : "text-tertiary"}">${state.running ? "ENABLED" : "STANDBY"}</div><p class="text-[10px] text-slate-500">Enables AI-driven countermeasures without manual sign-off.</p></div>
            <div class="space-y-2"><span class="text-xs font-semibold uppercase tracking-widest text-slate-400">Shadow Layer Auto-Scaling</span><div class="text-[11px] font-label text-secondary">ON</div><p class="text-[10px] text-slate-500">Dynamic virtualization scaling based on threat density.</p></div>
            <div class="space-y-2"><span class="text-xs font-semibold uppercase tracking-widest text-slate-400">SIEM Export Frequency</span><div class="text-[11px] font-label text-primary">REAL-TIME (STREAM)</div><p class="text-[10px] text-slate-500">Export pipeline tuned for low-latency forensics.</p></div>
          </div>
        </div>
        <div class="glass-panel p-6 rounded-md flex flex-col justify-between"><div><h3 class="font-headline text-lg font-bold text-on-surface mb-4">UI Environment</h3><div class="space-y-4"><div class="flex items-center justify-between"><span class="text-sm text-on-surface-variant">Active Theme</span><div class="flex gap-2"><button class="w-6 h-6 rounded-full bg-slate-900 border-2 border-primary"></button><button class="w-6 h-6 rounded-full bg-slate-200 border-2 border-transparent"></button><button class="w-6 h-6 rounded-full bg-emerald-950 border-2 border-transparent"></button></div></div><div class="flex items-center justify-between"><span class="text-sm text-on-surface-variant">Data Density</span><div class="flex bg-surface-container-lowest p-0.5 rounded"><button class="px-3 py-1 text-[10px] bg-primary text-on-primary rounded-sm font-bold">COMPACT</button><button class="px-3 py-1 text-[10px] text-slate-500 rounded-sm font-bold">RELAXED</button></div></div></div></div><button data-action="start-stop-scenario" class="w-full py-2 bg-primary/10 border border-primary/20 text-primary font-bold text-xs rounded-sm hover:bg-primary/20 transition-all uppercase tracking-widest mt-6">Apply Environment Specs</button></div>
      </section>
      <section>
        <div class="flex items-end justify-between mb-6"><h2 class="font-headline text-xl font-bold text-on-surface border-l-4 border-primary pl-4 uppercase tracking-tighter">Neural Agent Parameters</h2><span class="text-[10px] font-label text-slate-500 uppercase tracking-widest">Active Units: 05 / Capacity: 12</span></div>
        <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">${agentCards.map((a, i) => `<div class="bg-surface-container p-4 rounded-md border-b-2 border-${a.tone}/50 relative overflow-hidden group"><div class="flex justify-between items-start mb-4"><div class="w-10 h-10 bg-slate-900 flex items-center justify-center rounded-sm border border-white/5"><span class="material-symbols-outlined text-${a.tone}">${i === 0 ? "smart_toy" : i === 1 ? "memory" : i === 2 ? "data_object" : i === 3 ? "warning" : "rocket_launch"}</span></div><span class="text-[10px] font-label ${a.tone === "tertiary" ? "text-tertiary" : "text-emerald-400"}">${String(i + 1).padStart(2, "0")}_${a.tone === "tertiary" ? "WARNING" : "ACTIVE"}</span></div><h4 class="font-headline font-bold text-sm mb-1 uppercase tracking-tight">${a.name}</h4><p class="text-[10px] text-on-surface-variant mb-4 font-label">ID: ${a.id}</p><div class="space-y-3"><div class="space-y-1"><div class="flex justify-between text-[10px] font-label"><span class="text-slate-500">${a.metric}</span><span class="text-${a.tone}">${a.val}${a.suffix || "%"}</span></div><div class="h-1 bg-surface-container-highest rounded-full overflow-hidden"><div class="h-full bg-${a.tone}" style="width:${a.suffix ? Math.min(100, a.val * 2) : a.val}%"></div></div></div><div class="flex items-center justify-between"><span class="text-[10px] font-label text-slate-400">VERBOSE LOGS</span><input ${i % 2 === 0 ? "checked" : ""} class="h-3 w-3 bg-surface border-none rounded-sm text-${a.tone} focus:ring-0" type="checkbox"/></div></div></div>`).join("")}</div>
      </section>
      <section class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="glass-panel p-6 rounded-md"><div class="flex items-center gap-3 mb-6"><span class="material-symbols-outlined text-primary">key</span><h3 class="font-headline text-lg font-bold">API &amp; Integrations</h3></div><div class="space-y-4"><div class="p-4 bg-surface-container-lowest rounded border border-white/5"><div class="flex justify-between items-center mb-2"><span class="text-xs font-bold font-label">NPM PACKAGE REGISTRY</span><span class="text-[10px] text-emerald-400 font-label">CONNECTED</span></div><div class="flex gap-2"><input class="flex-1 bg-surface border-none text-on-surface text-xs font-label px-3 py-2 rounded-sm" readonly type="password" value="••••••••••••••••••••••••••••"/><button class="px-3 bg-primary/10 text-primary border border-primary/20 rounded-sm"><span class="material-symbols-outlined text-sm">content_copy</span></button></div></div><div class="p-4 bg-surface-container-lowest rounded border border-white/5"><div class="flex justify-between items-center mb-2"><span class="text-xs font-bold font-label">PYPI / PIP INTEGRATION</span><span class="text-[10px] text-tertiary font-label">EXPIRED</span></div><div class="flex gap-2"><input class="flex-1 bg-surface border-none text-on-surface text-xs font-label px-3 py-2 rounded-sm" placeholder="ENTER NEW ACCESS TOKEN" type="text"/><button class="px-3 bg-tertiary/10 text-tertiary border border-tertiary/20 rounded-sm"><span class="material-symbols-outlined text-sm">refresh</span></button></div></div></div></div>
        <div class="glass-panel p-6 rounded-md"><div class="flex items-center gap-3 mb-6"><span class="material-symbols-outlined text-secondary">verified_user</span><h3 class="font-headline text-lg font-bold">Access Control (RBAC)</h3></div><div class="overflow-x-auto"><table class="w-full text-left"><thead class="border-b border-white/10"><tr><th class="py-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Operator</th><th class="py-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Role</th><th class="py-2 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Clearance</th></tr></thead><tbody class="divide-y divide-white/5"><tr><td class="py-3 text-sm">K. Johns</td><td class="py-3 text-xs font-label text-slate-300">ADMINISTRATOR</td><td class="py-3"><span class="px-2 py-0.5 bg-secondary/10 text-secondary text-[10px] border border-secondary/20 rounded-sm">LVL-4</span></td></tr><tr><td class="py-3 text-sm">M. Rossi</td><td class="py-3 text-xs font-label text-slate-300">OPERATOR</td><td class="py-3"><span class="px-2 py-0.5 bg-primary/10 text-primary text-[10px] border border-primary/20 rounded-sm">LVL-2</span></td></tr><tr><td class="py-3 text-sm">A. Lopez</td><td class="py-3 text-xs font-label text-slate-300">AUDITOR</td><td class="py-3"><span class="px-2 py-0.5 bg-slate-800 text-slate-400 text-[10px] border border-white/5 rounded-sm">LVL-1</span></td></tr></tbody></table></div></div>
      </section>
    </div>`;
  } else if (state.currentView === "audit-logs") {
    const highImpact = recent.filter((e) => Number(e.risk) >= 80).length;
    html = `<div class="space-y-6">
      <section class="flex justify-between items-end">
        <div><h2 class="text-3xl font-bold font-headline tracking-tight text-on-surface mb-2">Audit Logs</h2><div class="flex items-center gap-3"><span class="flex items-center gap-1.5 text-xs text-secondary font-label"><span class="w-1.5 h-1.5 bg-secondary rounded-full shadow-[0_0_8px_#4edea3]"></span>SYSTEM LIVE</span><span class="text-slate-500 text-xs font-label">Showing ${fmtNumber(recent.length)} total events in current epoch</span></div></div>
        <div class="flex gap-2"><button class="flex items-center gap-2 px-4 py-2 bg-surface-container border border-outline-variant/20 text-xs font-label text-on-surface hover:bg-surface-container-high transition-colors"><span class="material-symbols-outlined text-sm">filter_list</span>Advanced Filters</button><button class="flex items-center gap-2 px-4 py-2 bg-primary text-on-primary text-xs font-label font-bold hover:brightness-110 transition-all rounded-sm shadow-[0_0_15px_rgba(173,198,255,0.2)]"><span class="material-symbols-outlined text-sm">download</span>Export CSV</button></div>
      </section>
      <section class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="p-4 bg-surface-container-low rounded border border-white/5"><p class="text-[10px] font-label text-slate-500 uppercase tracking-widest mb-1">Total Actions</p><p class="text-2xl font-bold font-headline text-primary">${fmtNumber(recent.length)}</p></div>
        <div class="p-4 bg-surface-container-low rounded border border-white/5"><p class="text-[10px] font-label text-slate-500 uppercase tracking-widest mb-1">High Impact Events</p><p class="text-2xl font-bold font-headline text-tertiary">${highImpact}</p></div>
        <div class="p-4 bg-surface-container-low rounded border border-white/5"><p class="text-[10px] font-label text-slate-500 uppercase tracking-widest mb-1">Agent Retrains</p><p class="text-2xl font-bold font-headline text-secondary">${recent.filter((e) => e.attack.toLowerCase().includes("model") || e.action === "MFA").length}</p></div>
        <div class="p-4 bg-surface-container-low rounded border border-white/5"><p class="text-[10px] font-label text-slate-500 uppercase tracking-widest mb-1">System Overrides</p><p class="text-2xl font-bold font-headline text-on-surface">${recent.filter((e) => e.action === "KILL").length}</p></div>
      </section>
      <section class="bg-surface-container border border-white/5 rounded overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-[11px]">
            <thead class="bg-surface-container-high/50 border-b border-outline-variant/20">
              <tr>
                <th class="px-4 py-3 font-label uppercase tracking-widest text-on-surface-variant">Timestamp</th>
                <th class="px-4 py-3 font-label uppercase tracking-widest text-on-surface-variant">Actor</th>
                <th class="px-4 py-3 font-label uppercase tracking-widest text-on-surface-variant">Action</th>
                <th class="px-4 py-3 font-label uppercase tracking-widest text-on-surface-variant">Impact</th>
                <th class="px-4 py-3 font-label uppercase tracking-widest text-on-surface-variant">Metadata</th>
                <th class="px-4 py-3 font-label uppercase tracking-widest text-on-surface-variant">State</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/5">
              ${recent.slice(0, 18).map((e) => `<tr class="hover:bg-white/[0.02] transition-colors">
                <td class="px-4 py-3 font-label text-primary-fixed-dim">${e.time}</td>
                <td class="px-4 py-3 text-on-surface">${e.user_id}</td>
                <td class="px-4 py-3"><span class="px-2 py-1 bg-surface-container-highest text-on-surface text-[10px] font-headline border-l-2 border-primary">${e.attack}</span></td>
                <td class="px-4 py-3 ${riskColorClass(Number(e.risk))} font-bold">${Number(e.risk).toFixed(1)}</td>
                <td class="px-4 py-3 text-[10px] text-slate-500 font-label">{"ip":"${e.ip}","event":"${e.id}"}</td>
                <td class="px-4 py-3 font-label text-on-surface-variant">${e.action}</td>
              </tr>`).join("")}
            </tbody>
          </table>
        </div>
        <div class="px-6 py-4 bg-surface-container-high/30 border-t border-outline-variant/20 flex justify-between items-center"><span class="text-xs text-slate-500 font-label">Showing <span class="text-on-surface font-label">1-${Math.min(18, recent.length)}</span> of <span class="text-on-surface font-label">${fmtNumber(recent.length)}</span></span><div class="flex gap-1"><button class="p-1 text-slate-500 hover:text-on-surface transition-colors"><span class="material-symbols-outlined text-lg">chevron_left</span></button><button class="px-3 py-1 bg-primary/20 text-primary text-xs font-label rounded-sm border border-primary/30">1</button><button class="px-3 py-1 hover:bg-white/5 text-slate-400 text-xs font-label rounded-sm transition-colors">2</button><button class="p-1 text-slate-500 hover:text-on-surface transition-colors"><span class="material-symbols-outlined text-lg">chevron_right</span></button></div></div>
      </section>
    </div>`;
  } else {
    html = recent.slice(0, 24).map((e) => {
      const c = riskColorClass(Number(e.risk));
      return `<div class="p-3 border border-outline-variant/15 rounded bg-surface-container-low/50">
        <div class="flex justify-between text-[10px] uppercase text-on-surface-variant font-label">
          <span>${e.time}</span><span class="${c}">${e.attack}</span>
        </div>
        <div class="mt-1 text-xs">${e.ip} | user=${e.user_id} | risk=<span class="${c} font-bold">${Number(e.risk).toFixed(1)}</span> | action=${e.action}</div>
      </div>`;
    }).join("");
  }

  stream.innerHTML = html;

  if (state.currentView === "sentinel") {
    stream.innerHTML = recent.slice(0, 24).map((e) => {
    const c = riskColorClass(Number(e.risk));
    return `<div class="p-3 border border-outline-variant/15 rounded bg-surface-container-low/50">
      <div class="flex justify-between text-[10px] uppercase text-on-surface-variant font-label">
        <span>${e.time}</span><span class="${c}">${e.attack}</span>
      </div>
      <div class="mt-1 text-xs">${e.ip} | user=${e.user_id} | risk=<span class="${c} font-bold">${Number(e.risk).toFixed(1)}</span> | action=${e.action}</div>
    </div>`;
    }).join("");
  }

  if (events.length) {
    const avg = events.slice(0, 10).reduce((s, e) => s + Number(e.risk), 0) / Math.min(10, events.length);
    if (risk) risk.textContent = avg.toFixed(1);
    if (action) action.textContent = events[0].action || "-";
  }
  if (total) total.textContent = String(events.length);
  if (scenario) {
    scenario.textContent = state.running ? "Running" : "Stopped";
    scenario.className = state.running ? "font-bold text-secondary" : "font-bold text-tertiary";
  }
}

function applyView() {
  const params = new URLSearchParams(window.location.search);
  const view = (params.get("view") || "sentinel").toLowerCase();
  state.currentView = VIEW_META[view] ? view : "sentinel";

  const mainGrid = document.getElementById("mainGrid");
  const moduleView = document.getElementById("moduleView");
  const moduleGrid = document.getElementById("moduleGrid");
  const moduleStream = document.getElementById("moduleStream");
  const moduleStreamPane = document.getElementById("moduleStreamPane");
  const moduleKpiPane = document.getElementById("moduleKpiPane");
  const title = document.getElementById("moduleTitle");
  const subtitle = document.getElementById("moduleSubtitle");
  const legacy = document.getElementById("moduleLegacyLink");

  if (state.currentView === "sentinel") {
    if (mainGrid) mainGrid.classList.remove("hidden");
    if (moduleView) moduleView.classList.add("hidden");
    return;
  }

  if (mainGrid) mainGrid.classList.add("hidden");
  if (moduleView) moduleView.classList.remove("hidden");

  const richViews = new Set(["behavior", "orchestrator", "deception", "threat-intel", "system-settings", "audit-logs"]);
  const richMode = richViews.has(state.currentView);

  if (moduleKpiPane) {
    moduleKpiPane.classList.toggle("hidden", richMode);
  }
  if (moduleStreamPane) {
    if (richMode) {
      moduleStreamPane.classList.remove("lg:col-span-7");
      moduleStreamPane.classList.add("lg:col-span-12");
    } else {
      moduleStreamPane.classList.remove("lg:col-span-12");
      moduleStreamPane.classList.add("lg:col-span-7");
    }
  }
  if (moduleStream) {
    if (richMode) {
      moduleStream.classList.remove("max-h-[420px]", "overflow-auto", "font-label", "text-xs", "space-y-2");
      moduleStream.classList.add("w-full");
    } else {
      moduleStream.classList.add("max-h-[420px]", "overflow-auto", "font-label", "text-xs", "space-y-2");
      moduleStream.classList.remove("w-full");
    }
  }
  if (moduleGrid) {
    if (richMode) {
      moduleGrid.classList.remove("gap-6");
      moduleGrid.classList.add("gap-4");
    } else {
      moduleGrid.classList.remove("gap-4");
      moduleGrid.classList.add("gap-6");
    }
  }

  const meta = VIEW_META[state.currentView];
  if (title) title.textContent = meta.title;
  if (subtitle) subtitle.textContent = meta.subtitle;
  if (legacy) legacy.href = meta.legacy;
}

function attachGenericButtonActions() {
  document.querySelectorAll("button").forEach((btn) => {
    if (btn.dataset.wired === "1") return;
    if (btn.id === "scenarioBtn") return;

    btn.dataset.wired = "1";
    const text = (btn.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();

    btn.addEventListener("click", () => {
      if (text.includes("view all logs")) {
        window.location.href = "/?view=audit-logs";
        return;
      }
      if (text.includes("siem export")) {
        window.open("http://localhost:9200", "_blank", "noopener,noreferrer");
        return;
      }
      if (text.includes("deploy policy")) {
        toggleScenario();
        return;
      }
      // Non-critical action buttons: provide tactile feedback.
      btn.classList.add("ring-2", "ring-primary/40");
      setTimeout(() => btn.classList.remove("ring-2", "ring-primary/40"), 250);
    });
  });
}

async function refreshData() {
  try {
    const status = await api("/api/status");
    const data = await api("/api/events?limit=80");
    state.backendAvailable = true;
    state.running = Boolean(status.running);
    state.events = data.events || [];
    renderRiskTable(state.events);
    renderKpis(state.events);
    renderModuleView(state.events);
  } catch (_e) {
    state.backendAvailable = false;
  }
  renderScenarioState();
}

async function toggleScenario() {
  if (!state.backendAvailable) return;
  if (state.running) {
    await api("/api/attack/stop", { method: "POST" });
  } else {
    await api("/api/attack/start", { method: "POST" });
  }
  await refreshData();
}

document.addEventListener("DOMContentLoaded", async () => {
  applyView();
  window.addEventListener("civa:view-change", () => {
    applyView();
    renderModuleView(state.events);
  });

  const btn = document.getElementById("scenarioBtn");
  if (btn) {
    btn.addEventListener("click", toggleScenario);
  }

  document.querySelectorAll("[data-action='start-stop-scenario']").forEach((b) => {
    b.addEventListener("click", toggleScenario);
  });

  attachGenericButtonActions();

  await refreshData();
  setInterval(() => {
    applyView();
    attachGenericButtonActions();
    refreshData();
  }, 2500);
});
