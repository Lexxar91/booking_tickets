// Регрессионные проверки XSS, хранения сессии и редактирования вместимости.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../app.js"), "utf8")
  .replace(/\nbootstrap\(\);\s*$/, "\n");

function createNode() {
  const selectors = new Map();
  return {
    innerHTML: "",
    textContent: "",
    value: "",
    children: [],
    appendChild(child) { this.children.push(child); },
    querySelector(selector) {
      if (!selectors.has(selector)) selectors.set(selector, createNode());
      return selectors.get(selector);
    },
  };
}

function createApp(storage = new Map()) {
  const nodes = new Map();
  const fields = Object.fromEntries([
    "eventId", "title", "description", "price", "total_tickets",
    "date_start", "date_end",
  ].map((name) => [name, { value: "" }]));
  const context = vm.createContext({
    localStorage: {
      getItem(key) { return storage.get(key) ?? null; },
      setItem(key, value) { storage.set(key, value); },
      removeItem(key) { storage.delete(key); },
    },
    document: {
      getElementById(id) {
        if (!nodes.has(id)) nodes.set(id, createNode());
        return nodes.get(id);
      },
      createElement: createNode,
    },
    window: { scrollTo() {} },
    atob: (value) => Buffer.from(value, "base64").toString("binary"),
    Headers,
    Intl,
  });
  vm.runInContext(source, context);
  nodes.get("event-form").elements = fields;
  nodes.get("event-form").reset = () => {};
  return { context, nodes, fields, storage };
}

test("содержимое события выводится текстом, включая HTML и неверные даты", () => {
  const app = createApp();
  const payload = '<img src=x onerror="alert(1)">';
  app.context.event = {
    id: 1, title: payload, description: payload,
    date_start: payload, date_end: payload, price: "10.00", total_tickets: 2,
  };
  vm.runInContext("state.events = [event]; renderEvents();", app.context);

  const card = app.nodes.get("events-list").children[0];
  assert.equal(card.querySelector(".event-title").textContent, payload);
  assert.equal(card.querySelector(".event-description").textContent, payload);
  assert.equal(card.querySelector(".event-dates").textContent,
    `${payload} - ${payload}`);
  assert.ok(!card.innerHTML.includes(payload));
});

test("ошибка health-check отображается текстом", () => {
  const app = createApp();
  app.context.payload = '<svg onload="alert(1)">';
  vm.runInContext(
    "state.serviceStatus.auth.detail = payload; renderServiceStatus();",
    app.context,
  );
  const status = app.nodes.get("service-status").children[0];
  assert.equal(status.querySelector(".booking-meta").textContent,
    app.context.payload);
  assert.ok(!status.innerHTML.includes(app.context.payload));
});

test("JWT отсутствуют в состоянии и хранилище frontend", () => {
  const storage = new Map([
    ["booking_ui_access_token", "old-access"],
    ["booking_ui_refresh_token", "old-refresh"],
  ]);
  const app = createApp(storage);
  assert.equal(vm.runInContext("'accessToken' in state", app.context), false);
  assert.equal(vm.runInContext("'refreshToken' in state", app.context), false);
  vm.runInContext(`saveSession({
    user: {id: 1, role: "user", email: "a@test.com"}, csrf_token: "csrf"
  });`, app.context);

  assert.equal(storage.has("booking_ui_access_token"), false);
  assert.equal(storage.has("booking_ui_refresh_token"), false);
  assert.equal(vm.runInContext("state.user.id", app.context), 1);
  assert.equal(vm.runInContext("state.csrfToken", app.context), "csrf");

  const reloaded = createApp(storage);
  assert.equal(vm.runInContext("state.user", reloaded.context), null);

  vm.runInContext("clearSession();", app.context);
  assert.equal(vm.runInContext("state.user", app.context), null);
  assert.equal(vm.runInContext("state.csrfToken", app.context), "");
});

test("после перезагрузки вход восстанавливается cookie-запросом к BFF", async () => {
  const app = createApp();
  const requests = [];
  app.context.fetch = async (url, options) => {
    requests.push({ url, options });
    return {
      ok: true, headers: new Headers({"content-type": "application/json"}),
      json: async () => ({user: {id: 7, role: "user", email: "a@test.com"},
        csrf_token: "server-csrf"}),
    };
  };
  await vm.runInContext("restoreSession();", app.context);
  assert.equal(vm.runInContext("state.user.id", app.context), 7);
  assert.equal(requests[0].url, "/api/auth/session");
  assert.equal(requests[0].options.credentials, "same-origin");
  assert.equal(requests[0].options.headers.has("Authorization"), false);
  await vm.runInContext(`apiRequest("/api/bookings/", {
    method: "POST", auth: true, json: {event_id: 1}
  });`, app.context);
  assert.equal(requests[1].options.headers.get("X-CSRF-Token"), "server-csrf");
  assert.equal(requests[1].options.headers.has("Authorization"), false);
});

test("форма запрещает менять вместимость при редактировании события", () => {
  const app = createApp();
  app.context.event = {
    id: 1, title: "Concert", description: "", price: "10.00", total_tickets: 2,
    date_start: "2026-10-20T10:00:00Z", date_end: "2026-10-20T11:00:00Z",
  };
  vm.runInContext("fillEventForm(event);", app.context);
  assert.equal(app.fields.total_tickets.readOnly, true);
  assert.equal(app.fields.total_tickets.value, 2);
  vm.runInContext("resetEventForm();", app.context);
  assert.equal(app.fields.total_tickets.readOnly, false);
});
