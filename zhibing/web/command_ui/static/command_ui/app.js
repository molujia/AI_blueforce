const origin = { lat: 25.044, lon: 121.523 };
const TILE_BOUNDS = [[25.000, 121.470], [25.088, 121.576]];
const map = L.map("map", {
  zoomControl: true,
  attributionControl: false,
  maxBounds: TILE_BOUNDS,
  maxBoundsViscosity: 0.8,
}).setView([origin.lat, origin.lon], 15);

// 卫星瓦片底图（本地 tile 目录）
const tileLayer = L.tileLayer("/tiles/{z}/{x}/{y}.png", {
  minZoom: 12,
  maxZoom: 18,
  maxNativeZoom: 18,
  tms: false,
  noWrap: true,
}).addTo(map);

const layers = {
  base: L.layerGroup().addTo(map),
  scenario: L.layerGroup().addTo(map),
  routes: L.layerGroup().addTo(map),
};
let currentSessionId = null;
let currentProjection = null;

init();

async function init() {
  bindEvents();
  await loadBaseMap();
  await loadDemoScene();
}

function bindEvents() {
  document.getElementById("loadDemoBtn").addEventListener("click", loadDemoScene);
  document.getElementById("deployDefaultBtn").addEventListener("click", loadDemoScene);
  document.getElementById("sendCommandBtn").addEventListener("click", submitRouteConstraint);
  document.getElementById("resetSessionBtn").addEventListener("click", resetSession);
  document.getElementById("commandInput").addEventListener("keydown", event => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) submitRouteConstraint();
  });
  document.querySelectorAll(".tool-btn").forEach(button => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tool-btn").forEach(item => item.classList.remove("active"));
      button.classList.add("active");
    });
  });
}

async function loadBaseMap() {
  // 仅加载水体覆盖层（223KB），建筑(17MB)/道路(12MB)/地块(2.4MB)过于庞大导致 SVG 渲染卡顿
  // 卫星瓦片底图已包含所有地形细节，无需重复绘制矢量图层
  const water = await fetch("/static/command_ui/map/water.geojson").then(r => r.json()).catch(() => null);
  if (water) L.geoJSON(water, { style: { color: "#155e75", weight: 1, fillColor: "#0e7490", fillOpacity: 0.28 } }).addTo(layers.base);
}

async function loadDemoScene() {
  const url = currentSessionId ? `/api/demo-scene?session_id=${encodeURIComponent(currentSessionId)}` : "/api/demo-scene";
  const response = await fetch(url);
  const data = await response.json();
  currentSessionId = data.session_id;
  renderProjection(data.projection);
  renderChatMessage("assistant", "已加载默认围剿演示场景。可以输入：不要走大路，大路有狙击风险。", false);
}

async function submitRouteConstraint() {
  const input = document.getElementById("commandInput");
  const message = input.value.trim();
  if (!message) return;
  renderChatMessage("user", message);
  input.value = "";
  const response = await fetch("/api/route-constraint", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: currentSessionId, message }),
  });
  const data = await response.json();
  currentSessionId = data.session_id;
  renderProjection(data.projection);
  renderChatMessage("assistant", data.explanation || "已重新规划路径。", false);
}

async function resetSession() {
  const response = await fetch("/api/session/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: currentSessionId }),
  });
  const data = await response.json();
  currentSessionId = data.session_id;
  document.getElementById("chat-messages").innerHTML = "";
  renderChatMessage("assistant", "会话已重置，历史约束已清空。", false);
  await loadDemoScene();
}

function renderProjection(projection) {
  currentProjection = projection;
  layers.scenario.clearLayers();
  layers.routes.clearLayers();
  document.getElementById("sessionPill").textContent = currentSessionId ? `SESSION ${currentSessionId.slice(0, 8)}` : "SESSION --";
  document.getElementById("ragPill").textContent = projection.graphrag_status?.enabled ? "RAG READY" : "RAG OFF";
  document.getElementById("taskState").textContent = projection.task_state?.state || "PLANNED";
  document.getElementById("routeCount").textContent = String((projection.route_candidates || []).length);
  document.getElementById("selectedRoute").textContent = projection.selected_route_id || "--";
  renderUnits(projection);
  renderRiskZones(projection);
  renderRoutes(projection);
  renderRouteCandidates(projection);
  renderObjectList(projection);
  renderConstraints(projection.session || {});
  document.getElementById("adapterPreview").textContent = JSON.stringify(projection.adapter_preview || {}, null, 2);
}

function renderUnits(projection) {
  if (projection.friendly) makeDraggableMarker("friendly", projection.friendly);
  for (const enemy of projection.enemies || []) makeDraggableMarker("enemy", enemy);
  if (projection.target) makeDraggableMarker("target", projection.target);
}

function makeDraggableMarker(kind, item) {
  const markerConfig = {
    friendly: { cls: "friendly", label: "B", coordKey: "position", tooltip: "我方班组" },
    enemy: { cls: "enemy", label: "E", coordKey: "position", tooltip: "敌方单元" },
    target: { cls: "target", label: "T", coordKey: "position", tooltip: "目标入口" },
  }[kind];
  const html = kind === "target"
    ? `<div class="target-marker">${markerConfig.label}</div>`
    : `<div class="unit-marker ${markerConfig.cls}">${markerConfig.label}</div>`;
  const icon = L.divIcon({ className: "", html, iconSize: [30, 30] });
  const marker = L.marker(vbsToLatLng(item[markerConfig.coordKey]), { icon, draggable: true })
    .bindTooltip(item.name || markerConfig.tooltip)
    .addTo(layers.scenario);
  marker.on("dragend", event => {
    item[markerConfig.coordKey] = latLngToVbs(event.target.getLatLng());
    renderObjectList(currentProjection);
  });
  return marker;
}

function renderRiskZones(projection) {
  for (const zone of projection.risk_zones || []) {
    L.circle(vbsToLatLng(zone.center), {
      radius: Number(zone.radius_m || 60),
      color: "#f97316",
      weight: 2,
      fillColor: "#f97316",
      fillOpacity: 0.16,
    }).bindTooltip(zone.name || zone.id).addTo(layers.scenario);
  }
}

function renderRoutes(projection) {
  const colors = ["#facc15", "#67e8f9", "#a78bfa", "#94a3b8"];
  const routeBounds = [];
  for (const [index, route] of (projection.route_candidates || []).entries()) {
    const latlngs = (route.waypoints || []).map(vbsToLatLng);
    if (!latlngs.length) continue;
    L.polyline(latlngs, {
      color: route.selected ? "#facc15" : colors[index % colors.length],
      weight: route.selected ? 5 : 3,
      opacity: route.selected ? 0.95 : 0.58,
      dashArray: route.selected ? null : "6 8",
    }).bindTooltip(`${route.id} score ${Number(route.total_score || 0).toFixed(0)}`).addTo(layers.routes);
    routeBounds.push(...latlngs);
  }
  if (projection.friendly) routeBounds.push(vbsToLatLng(projection.friendly.position));
  if (projection.target) routeBounds.push(vbsToLatLng(projection.target.position));
  if (routeBounds.length) map.fitBounds(L.latLngBounds(routeBounds).pad(0.25));
}

function renderRouteCandidates(projection) {
  const container = document.getElementById("routeCandidates");
  container.innerHTML = "";
  for (const route of projection.route_candidates || []) {
    const div = document.createElement("div");
    div.className = `route-candidate ${route.selected ? "selected" : ""}`;
    div.innerHTML = `<strong>${route.id}</strong><div class="metrics">distance ${Number(route.distance_m || 0).toFixed(0)}m | risk ${Number(route.risk_score || 0).toFixed(0)} | score ${Number(route.total_score || 0).toFixed(0)}</div><div>${(route.labels || []).join(" / ")}</div>`;
    container.appendChild(div);
  }
}

function renderObjectList(projection) {
  const container = document.getElementById("objectList");
  const objects = [];
  if (projection.friendly) objects.push(["我方", projection.friendly.name, projection.friendly.position]);
  for (const enemy of projection.enemies || []) objects.push(["敌方", enemy.name, enemy.position]);
  if (projection.target) objects.push(["目标", projection.target.name, projection.target.position]);
  for (const zone of projection.risk_zones || []) objects.push(["风险", zone.name, zone.center]);
  container.innerHTML = objects.map(([type, name, coord]) => `<div class="object-card"><strong>${type}</strong> ${name}<br>X ${Number(coord.x || 0).toFixed(0)} / Y ${Number(coord.y || 0).toFixed(0)}</div>`).join("");
}

function renderConstraints(session) {
  const container = document.getElementById("constraintList");
  const constraints = session.constraints || [];
  if (!constraints.length) {
    container.innerHTML = '<div class="constraint-card">暂无用户特殊约束。</div>';
    return;
  }
  container.innerHTML = constraints.map(item => `<div class="constraint-card"><strong>${item.action}</strong> ${item.target_type}:${item.target_id}<br>${item.reason || item.source_text || ""}</div>`).join("");
}

function renderChatMessage(role, content, persist = true) {
  const container = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.textContent = content;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function vbsToLatLng(coord) {
  if (!coord) return [origin.lat, origin.lon];
  if (coord.frame === "WGS84_LATLON_ALT") return [coord.lat, coord.lon];
  const lat = origin.lat + (Number(coord.y || 0) / 111320);
  const lon = origin.lon + (Number(coord.x || 0) / (111320 * Math.cos(origin.lat * Math.PI / 180)));
  return [lat, lon];
}

function latLngToVbs(latlng) {
  return {
    frame: "VBS_LOCAL_XYZ",
    x: (latlng.lng - origin.lon) * (111320 * Math.cos(origin.lat * Math.PI / 180)),
    y: (latlng.lat - origin.lat) * 111320,
    z: 0,
  };
}