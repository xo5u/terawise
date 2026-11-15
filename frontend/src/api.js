const SESSION_KEY = "terawise.history.session";
let session;
let sessionLoaded = false;
let sessionRequest;

function validSession(value) {
  return value && typeof value.user_id === "string" &&
    typeof value.access_token === "string" && value.access_token.length > 0 &&
    typeof value.refresh_token === "string" && value.refresh_token.length > 0 &&
    Number.isFinite(value.expires_at);
}

function readSession() {
  if (!sessionLoaded) {
    sessionLoaded = true;
    try {
      const stored = JSON.parse(localStorage.getItem(SESSION_KEY));
      if (validSession(stored)) session = stored;
    } catch { /* Use memory when browser storage is unavailable or invalid. */ }
  }
  return session;
}

function saveSession(value) {
  if (!validSession(value)) throw new Error("The server returned an invalid session. Please try again.");
  session = value;
  try { localStorage.setItem(SESSION_KEY, JSON.stringify(value)); } catch { /* Session remains available in memory. */ }
  return value;
}

async function request(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error = new Error(typeof body?.detail === "string" ? body.detail : `Request failed with status ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

async function getSession(forceRefresh = false, rejectedToken) {
  const current = readSession();
  // A concurrent request may already have replaced the rejected access token.
  if (current && (!forceRefresh || (rejectedToken && current.access_token !== rejectedToken)) &&
      current.expires_at > Date.now() / 1000 + 30) return current;
  if (!sessionRequest) {
    sessionRequest = request(current ? "/api/session/refresh" : "/api/session", {
      method: "POST",
      ...(current ? {
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: current.refresh_token })
      } : {})
    }).then(saveSession).finally(() => { sessionRequest = undefined; });
  }
  return sessionRequest;
}

async function authenticatedRequest(path, options) {
  const current = await getSession();
  const send = (value) => request(path, {
    ...options,
    headers: { ...options?.headers, Authorization: `Bearer ${value.access_token}` }
  });
  try {
    return await send(current);
  } catch (error) {
    if (error.status !== 401) throw error;
    return send(await getSession(true, current.access_token));
  }
}

export function fetchCrops() {
  return request("/api/crops");
}

export function fetchHistory() {
  return authenticatedRequest("/api/history");
}

export function recordPlanting(cropId, plantingDate) {
  return authenticatedRequest("/api/history", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ crop_id: cropId, planting_date: plantingDate })
  });
}

export function fetchRecommendation({ lat, lon, farmAreaM2, tankWaterL, plantingDate }) {
  return authenticatedRequest("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      lat,
      lon,
      farm_area_m2: farmAreaM2,
      tank_water_l: tankWaterL,
      planting_date: plantingDate
    })
  });
}
