const apiBase = window.location.hostname === "localhost" ? "http://localhost:8000" : `${window.location.protocol}//${window.location.hostname}:8000`;

const views = [
  { id: "overview", label: "Overview" },
  { id: "episodes", label: "Episode Testing" },
  { id: "requests", label: "Request / Response" },
  { id: "performance", label: "Performance" },
  { id: "agents", label: "AI Agents" },
  { id: "workflows", label: "Workflows" },
];

const state = {
  summary: null,
  catalog: null,
  metrics: null,
  requests: null,
  activeView: "overview",
};

document.getElementById("api-base-label").textContent = apiBase;

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function setActiveView(viewId) {
  state.activeView = viewId;
  document.getElementById("view-title").textContent =
    views.find((view) => view.id === viewId)?.label || "Overview";

  views.forEach((view) => {
    document.getElementById(`view-${view.id}`).classList.toggle("active", view.id === viewId);
  });

  [...document.querySelectorAll(".menu-button")].forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewId);
  });
}

function renderMenu() {
  const menu = document.getElementById("menu");
  menu.innerHTML = views
    .map(
      (view) => `
        <button class="menu-button ${view.id === state.activeView ? "active" : ""}" data-view="${view.id}">
          ${view.label}
        </button>
      `
    )
    .join("");

  menu.querySelectorAll(".menu-button").forEach((button) => {
    button.addEventListener("click", () => setActiveView(button.dataset.view));
  });
}

async function fetchJson(path, options = {}) {
  const response = await fetch(`${apiBase}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with ${response.status}`);
  }
  return response.json();
}

function renderOverview() {
  const summary = state.summary || {};
  const episodes = state.catalog?.episodes || [];
  const metrics = state.metrics?.http_metrics || [];

  document.getElementById("view-overview").innerHTML = `
    <div class="grid cols-3">
      <article class="panel">
        <p class="eyebrow">Episodes</p>
        <span class="metric-value">${summary.episodes || 0}</span>
        <p>Scenario-based backend testing modules available in the console.</p>
      </article>
      <article class="panel">
        <p class="eyebrow">Agents</p>
        <span class="metric-value">${summary.agents || 0}</span>
        <p>Registered AI agents and operational roles exposed by the project.</p>
      </article>
      <article class="panel">
        <p class="eyebrow">Workflows</p>
        <span class="metric-value">${summary.workflows || 0}</span>
        <p>Composable flows covering ingestion, extraction, NLP, review, and runtime.</p>
      </article>
    </div>
    <div class="grid cols-2" style="margin-top: 18px;">
      <article class="panel">
        <h3>Platform Snapshot</h3>
        <div class="list">
          <div class="list-item"><strong>Service</strong><span class="subtle">${summary.service || "-"}</span></div>
          <div class="list-item"><strong>Mock Mode</strong><span class="subtle">${summary.mock_mode ? "Enabled" : "Disabled"}</span></div>
          <div class="list-item"><strong>Recent Requests</strong><span class="subtle">${summary.recent_requests || 0}</span></div>
          <div class="list-item"><strong>Scenario Runs</strong><span class="subtle">${summary.recent_scenarios || 0}</span></div>
        </div>
      </article>
      <article class="panel">
        <h3>Most Active Endpoints</h3>
        ${
          metrics.length
            ? `<table class="table">
                <thead><tr><th>Path</th><th>Count</th><th>Average</th></tr></thead>
                <tbody>
                  ${metrics
                    .slice(0, 5)
                    .map(
                      (row) => `
                        <tr>
                          <td class="mono">${row.path}</td>
                          <td>${row.count}</td>
                          <td>${row.average_ms} ms</td>
                        </tr>
                      `
                    )
                    .join("")}
                </tbody>
              </table>`
            : `<div class="empty">Run an episode to start generating performance data.</div>`
        }
      </article>
    </div>
    <article class="panel" style="margin-top: 18px;">
      <h3>Episode Coverage</h3>
      <div class="grid cols-2">
        ${episodes
          .map(
            (episode) => `
              <div class="list-item">
                <strong>${episode.title}</strong>
                <span class="subtle">${episode.description}</span>
              </div>
            `
          )
          .join("")}
      </div>
    </article>
  `;
}

function renderEpisodes() {
  const episodes = state.catalog?.episodes || [];
  document.getElementById("view-episodes").innerHTML = `
    <div class="grid">
      ${episodes
        .map(
          (episode) => `
            <article class="panel episode-card">
              <div>
                <p class="eyebrow">${episode.id}</p>
                <h3>${episode.title}</h3>
                <p>${episode.description}</p>
              </div>
              <div class="episode-actions">
                <div>
                  <span class="tag">Workflow: ${episode.workflow}</span>
                  <span class="tag">Agent: ${episode.agent}</span>
                </div>
                <button class="button primary" data-episode="${episode.id}">Run Test</button>
              </div>
              <div class="split">
                <div>
                  <h4>Sample Request</h4>
                  <pre>${pretty(episode.sample_input)}</pre>
                </div>
                <div>
                  <h4>Latest Response</h4>
                  <pre id="response-${episode.id}">Run this episode to capture a response.</pre>
                </div>
              </div>
            </article>
          `
        )
        .join("")}
    </div>
  `;

  document.querySelectorAll("[data-episode]").forEach((button) => {
    button.addEventListener("click", async () => {
      const episodeId = button.dataset.episode;
      button.disabled = true;
      button.textContent = "Running...";
      try {
        const episode = episodes.find((entry) => entry.id === episodeId);
        const result = await fetchJson(`/api/dashboard/run/${episodeId}`, {
          method: "POST",
          body: JSON.stringify(episode.sample_input),
        });
        document.getElementById(`response-${episodeId}`).textContent = pretty(result);
        await refreshData();
      } catch (error) {
        document.getElementById(`response-${episodeId}`).textContent = String(error);
      } finally {
        button.disabled = false;
        button.textContent = "Run Test";
      }
    });
  });
}

function renderRequests() {
  const requestRows = state.requests?.http_requests || [];
  const scenarioRows = state.requests?.scenario_requests || [];

  document.getElementById("view-requests").innerHTML = `
    <div class="split">
      <article class="panel">
        <h3>HTTP Request Monitor</h3>
        ${
          requestRows.length
            ? `<div class="list">
                ${requestRows
                  .map(
                    (row) => `
                      <div class="list-item">
                        <strong>${row.method} <span class="mono">${row.path}</span></strong>
                        <span class="subtle">${row.status_code} • ${row.duration_ms} ms • ${row.timestamp}</span>
                      </div>
                    `
                  )
                  .join("")}
              </div>`
            : `<div class="empty">No HTTP traffic captured yet.</div>`
        }
      </article>
      <article class="panel">
        <h3>Scenario Request / Response</h3>
        ${
          scenarioRows.length
            ? `<div class="list">
                ${scenarioRows
                  .map(
                    (row) => `
                      <div class="list-item">
                        <strong>${row.episode_id}</strong>
                        <span class="subtle">${row.duration_ms} ms • ${row.timestamp}</span>
                        <pre style="margin-top: 12px;">${pretty({
                          request: row.request,
                          response: row.response,
                        })}</pre>
                      </div>
                    `
                  )
                  .join("")}
              </div>`
            : `<div class="empty">Run an episode to inspect the full request and response payloads.</div>`
        }
      </article>
    </div>
  `;
}

function renderPerformance() {
  const rows = state.metrics?.http_metrics || [];
  const scenarioRows = state.metrics?.scenario_runs || [];

  document.getElementById("view-performance").innerHTML = `
    <div class="split">
      <article class="panel">
        <h3>Endpoint Performance</h3>
        ${
          rows.length
            ? `<table class="table">
                <thead>
                  <tr>
                    <th>Path</th>
                    <th>Calls</th>
                    <th>Average</th>
                    <th>Max</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  ${rows
                    .map(
                      (row) => `
                        <tr>
                          <td class="mono">${row.path}</td>
                          <td>${row.count}</td>
                          <td>${row.average_ms} ms</td>
                          <td>${row.max_ms} ms</td>
                          <td>${row.last_status}</td>
                        </tr>
                      `
                    )
                    .join("")}
                </tbody>
              </table>`
            : `<div class="empty">Performance data appears here after the first API calls.</div>`
        }
      </article>
      <article class="panel">
        <h3>Episode Run Latency</h3>
        ${
          scenarioRows.length
            ? `<div class="list">
                ${scenarioRows
                  .map(
                    (row) => `
                      <div class="list-item">
                        <strong>${row.episode_id}</strong>
                        <span class="subtle">${row.duration_ms} ms at ${row.timestamp}</span>
                      </div>
                    `
                  )
                  .join("")}
              </div>`
            : `<div class="empty">Scenario latency will appear after tests run.</div>`
        }
      </article>
    </div>
  `;
}

function renderAgents() {
  const agents = state.catalog?.agents || [];
  document.getElementById("view-agents").innerHTML = `
    <div class="grid cols-2">
      ${agents
        .map(
          (agent) => `
            <article class="panel">
              <p class="eyebrow">${agent.type}</p>
              <h3>${agent.name}</h3>
              <p>${agent.workflows.join(", ")}</p>
              <div class="list" style="margin-top: 14px;">
                ${agent.capabilities
                  .map((capability) => `<div class="list-item"><span class="subtle">${capability}</span></div>`)
                  .join("")}
              </div>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function renderWorkflows() {
  const workflows = state.catalog?.workflows || [];
  document.getElementById("view-workflows").innerHTML = `
    <div class="grid">
      ${workflows
        .map(
          (workflow) => `
            <article class="panel">
              <p class="eyebrow">${workflow.id}</p>
              <h3>${workflow.name}</h3>
              <div class="split" style="margin-top: 14px;">
                <div>
                  <h4>Steps</h4>
                  <div class="list">
                    ${workflow.steps.map((step) => `<div class="list-item"><span class="subtle">${step}</span></div>`).join("")}
                  </div>
                </div>
                <div>
                  <h4>Modules</h4>
                  <div class="list">
                    ${workflow.modules.map((module) => `<div class="list-item mono">${module}</div>`).join("")}
                  </div>
                </div>
              </div>
            </article>
          `
        )
        .join("")}
    </div>
  `;
}

function renderAll() {
  renderOverview();
  renderEpisodes();
  renderRequests();
  renderPerformance();
  renderAgents();
  renderWorkflows();
}

async function refreshData() {
  const [summary, catalog, metrics, requests] = await Promise.all([
    fetchJson("/api/dashboard/summary"),
    fetchJson("/api/dashboard/catalog"),
    fetchJson("/api/dashboard/metrics"),
    fetchJson("/api/dashboard/requests"),
  ]);

  state.summary = summary;
  state.catalog = catalog;
  state.metrics = metrics;
  state.requests = requests;
  renderAll();
}

async function boot() {
  renderMenu();
  setActiveView("overview");
  document.getElementById("refresh-button").addEventListener("click", refreshData);

  try {
    await refreshData();
  } catch (error) {
    document.getElementById("view-overview").innerHTML = `
      <article class="panel">
        <h3>Unable to load dashboard</h3>
        <p>${String(error)}</p>
      </article>
    `;
  }
}

boot();
