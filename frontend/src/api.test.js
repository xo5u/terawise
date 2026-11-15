import assert from "node:assert/strict";
import { test } from "node:test";

const storageKey = "terawise.history.session";
const active = () => ({ user_id: "browser-user", access_token: "access-one", refresh_token: "refresh-one", expires_at: Math.floor(Date.now() / 1000) + 3600 });
const response = (body, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
let sequence = 0;

async function setup(t, { stored = null, handler = () => response({ saved: true }), blocked = false } = {}) {
  const calls = [];
  const writes = [];
  t.mock.method(globalThis, "fetch", async (path, options) => {
    calls.push({ path, options });
    return handler(path, options);
  });
  const original = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
    getItem: (key) => { assert.equal(key, storageKey); if (blocked) throw new Error("Blocked"); return stored; },
    setItem: (key, value) => { if (blocked) throw new Error("Blocked"); writes.push([key, JSON.parse(value)]); }
  } });
  t.after(() => {
    if (original) Object.defineProperty(globalThis, "localStorage", original);
    else delete globalThis.localStorage;
  });
  return { api: await import(`./api.js?test=${++sequence}`), calls, writes };
}

test("history, planting and recommendations use saved bearer session and selected crop date", async (t) => {
  const { api, calls } = await setup(t, { stored: JSON.stringify(active()) });
  await api.fetchHistory();
  await api.recordPlanting(7, "2026-11-15");
  await api.fetchRecommendation({ lat: 31.5, lon: 35.1, farmAreaM2: 400, tankWaterL: 1000, plantingDate: "2026-11-15" });
  assert.deepEqual(calls.map((call) => call.path), ["/api/history", "/api/history", "/api/recommend"]);
  for (const call of calls) assert.equal(call.options.headers.Authorization, "Bearer access-one");
  assert.equal(calls[1].options.method, "POST");
  assert.deepEqual(JSON.parse(calls[1].options.body), { crop_id: 7, planting_date: "2026-11-15" });
  assert.deepEqual(JSON.parse(calls[2].options.body), {
    lat: 31.5, lon: 35.1, farm_area_m2: 400, tank_water_l: 1000, planting_date: "2026-11-15"
  });
});

test("concurrent initial requests share one anonymous signup and persist session", async (t) => {
  const created = active();
  const { api, calls, writes } = await setup(t, { stored: "invalid json", handler: async (path) => {
    if (path === "/api/session") { await new Promise((resolve) => setTimeout(resolve, 5)); return response(created); }
    return response([]);
  } });
  await Promise.all([api.fetchHistory(), api.recordPlanting(2, "2026-12-01")]);
  assert.equal(calls.filter((call) => call.path === "/api/session").length, 1);
  assert.deepEqual(writes, [[storageKey, created]]);
});

test("blocked storage keeps the created session in memory", async (t) => {
  const { api, calls } = await setup(t, { blocked: true, handler: (path) => response(path === "/api/session" ? active() : []) });
  await api.fetchHistory();
  await api.recordPlanting(3, "2026-11-16");
  assert.equal(calls.filter((call) => call.path === "/api/session").length, 1);
});

test("expired stored session refreshes before accessing history", async (t) => {
  const expired = { ...active(), expires_at: 1 };
  const renewed = { ...active(), access_token: "renewed" };
  const { api, calls } = await setup(t, { stored: JSON.stringify(expired), handler: (path) => response(path === "/api/session/refresh" ? renewed : []) });
  await api.fetchHistory();
  assert.deepEqual(JSON.parse(calls[0].options.body), { refresh_token: "refresh-one" });
  assert.equal(calls[1].options.headers.Authorization, "Bearer renewed");
});

test("401 refreshes once and retries with the refreshed bearer", async (t) => {
  let attempts = 0;
  const { api, calls } = await setup(t, { stored: JSON.stringify(active()), handler: (path) => {
    if (path === "/api/session/refresh") return response({ ...active(), access_token: "renewed" });
    return ++attempts === 1 ? response({ detail: "Expired token" }, 401) : response([]);
  } });
  await api.fetchHistory();
  assert.deepEqual(calls.map((call) => call.path), ["/api/history", "/api/session/refresh", "/api/history"]);
  assert.equal(calls[2].options.headers.Authorization, "Bearer renewed");
});

test("repeated 401 is surfaced after one refresh", async (t) => {
  const { api, calls } = await setup(t, { stored: JSON.stringify(active()), handler: (path) => path === "/api/session/refresh" ? response(active()) : response({ detail: "Unauthorized" }, 401) });
  await assert.rejects(api.fetchHistory(), /Unauthorized/);
  assert.equal(calls.length, 3);
});

test("disabled anonymous authentication reports server detail without retrying signup", async (t) => {
  const { api, calls } = await setup(t, { handler: () => response({ detail: "Enable anonymous sign-ins in Supabase to save planting history." }, 503) });
  await assert.rejects(api.recordPlanting(1, "2026-11-15"), /Enable anonymous sign-ins/);
  assert.equal(calls.length, 1);
});

test("public crops do not create sessions and non-JSON errors retain status", async (t) => {
  const { api, calls } = await setup(t, { handler: () => ({ ok: false, status: 503, json: async () => { throw new Error("Invalid JSON"); } }) });
  await assert.rejects(api.fetchCrops(), /Request failed with status 503/);
  assert.equal(calls[0].path, "/api/crops");
  assert.equal(calls[0].options, undefined);
  assert.equal(calls.length, 1);
});
