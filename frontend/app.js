const storageKeys = {
  accessToken: "booking_ui_access_token",
  refreshToken: "booking_ui_refresh_token",
  userEmail: "booking_ui_user_email",
};

const state = {
  accessToken: localStorage.getItem(storageKeys.accessToken) || "",
  refreshToken: localStorage.getItem(storageKeys.refreshToken) || "",
  userEmail: localStorage.getItem(storageKeys.userEmail) || "",
  events: [],
  bookings: [],
  serviceStatus: {
    auth: { label: "Auth Service", ok: null, detail: "ожидание" },
    events: { label: "Event Service", ok: null, detail: "ожидание" },
    bookings: { label: "Booking Service", ok: null, detail: "ожидание" },
  },
};

const elements = {
  serviceStatus: document.getElementById("service-status"),
  sessionRole: document.getElementById("session-role"),
  sessionSummary: document.getElementById("session-summary"),
  sessionTokens: document.getElementById("session-tokens"),
  accessTokenPreview: document.getElementById("access-token-preview"),
  refreshTokenPreview: document.getElementById("refresh-token-preview"),
  eventsList: document.getElementById("events-list"),
  bookingsList: document.getElementById("bookings-list"),
  eventSearch: document.getElementById("event-search"),
  eventForm: document.getElementById("event-form"),
  eventSubmitBtn: document.getElementById("event-submit-btn"),
  toastStack: document.getElementById("toast-stack"),
};

function decodeJwtPayload(token) {
  if (!token) {
    return null;
  }

  try {
    const payload = token.split(".")[1];
    if (!payload) {
      return null;
    }

    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(normalized)
        .split("")
        .map((char) => `%${char.charCodeAt(0).toString(16).padStart(2, "0")}`)
        .join(""),
    );
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function getCurrentUser() {
  const payload = decodeJwtPayload(state.accessToken);
  if (!payload) {
    return null;
  }

  return {
    id: payload.sub,
    role: payload.role || "user",
    type: payload.type,
    email: state.userEmail || "unknown",
  };
}

function saveSession({ accessToken, refreshToken, email }) {
  state.accessToken = accessToken || "";
  state.refreshToken = refreshToken || "";
  state.userEmail = email || state.userEmail || "";

  localStorage.setItem(storageKeys.accessToken, state.accessToken);
  localStorage.setItem(storageKeys.refreshToken, state.refreshToken);
  localStorage.setItem(storageKeys.userEmail, state.userEmail);

  renderSession();
}

function clearSession() {
  state.accessToken = "";
  state.refreshToken = "";
  state.userEmail = "";

  localStorage.removeItem(storageKeys.accessToken);
  localStorage.removeItem(storageKeys.refreshToken);
  localStorage.removeItem(storageKeys.userEmail);

  renderSession();
  renderBookings();
}

function formatTokenPreview(token) {
  if (!token) {
    return "empty";
  }
  if (token.length <= 48) {
    return token;
  }
  return `${token.slice(0, 24)} ... ${token.slice(-18)}`;
}

function formatDate(isoString) {
  if (!isoString) {
    return "—";
  }

  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) {
    return isoString;
  }

  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function showToast(message, type = "success") {
  const toast = document.createElement("article");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  elements.toastStack.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 4200);
}

async function apiRequest(path, options = {}) {
  const config = { method: "GET", ...options };
  const headers = new Headers(config.headers || {});

  if (config.auth && state.accessToken) {
    headers.set("Authorization", `Bearer ${state.accessToken}`);
  }

  if (config.json) {
    headers.set("Content-Type", "application/json");
    config.body = JSON.stringify(config.json);
  }

  if (config.form) {
    headers.set("Content-Type", "application/x-www-form-urlencoded");
    config.body = new URLSearchParams(config.form);
  }

  const response = await fetch(path, { ...config, headers });
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    const detail =
      typeof payload === "string"
        ? payload
        : payload?.detail || payload?.message || JSON.stringify(payload);
    throw new Error(detail || `HTTP ${response.status}`);
  }

  return payload;
}

function renderSession() {
  const user = getCurrentUser();
  elements.sessionRole.textContent = user?.role || "guest";
  elements.sessionSummary.textContent = user
    ? `${user.email} · role=${user.role} · user_id=${user.id}`
    : "Не авторизован";
  elements.sessionTokens.textContent = user
    ? "Access и refresh токены сохранены в localStorage"
    : "Access / Refresh недоступны";
  elements.accessTokenPreview.textContent = formatTokenPreview(state.accessToken);
  elements.refreshTokenPreview.textContent = formatTokenPreview(state.refreshToken);
  elements.eventSubmitBtn.disabled = !user || user.role !== "admin";
}

function renderServiceStatus() {
  elements.serviceStatus.innerHTML = "";

  Object.values(state.serviceStatus).forEach((service) => {
    const item = document.createElement("div");
    item.className = "status-pill";

    const chipClass =
      service.ok === null ? "status-pending" : service.ok ? "status-ok" : "status-error";
    const chipLabel =
      service.ok === null ? "checking" : service.ok ? "online" : "offline";

    item.innerHTML = `
      <div>
        <strong>${service.label}</strong>
        <div class="booking-meta">${service.detail}</div>
      </div>
      <span class="status-chip ${chipClass}">${chipLabel}</span>
    `;
    elements.serviceStatus.appendChild(item);
  });
}

function createEmptyState(message) {
  const item = document.createElement("div");
  item.className = "empty-state";
  item.textContent = message;
  return item;
}

function renderEvents() {
  const query = elements.eventSearch.value.trim().toLowerCase();
  const user = getCurrentUser();
  const filtered = state.events.filter((event) =>
    event.title.toLowerCase().includes(query),
  );

  elements.eventsList.innerHTML = "";
  if (filtered.length === 0) {
    elements.eventsList.appendChild(createEmptyState("События пока не найдены."));
    return;
  }

  filtered.forEach((event) => {
    const article = document.createElement("article");
    article.className = "event-card";
    article.innerHTML = `
      <div class="event-header">
        <div>
          <div class="event-title">${event.title}</div>
          <div class="event-meta">
            ${event.description || "Без описания"}<br />
            ${formatDate(event.date_start)} - ${formatDate(event.date_end)}
          </div>
        </div>
        <span class="mini-tag">${Number(event.price).toFixed(2)} RUB</span>
      </div>
      <div class="event-meta">
        id=${event.id} · билетов=${event.total_tickets}
      </div>
      <div class="card-actions">
        <button type="button" data-book-event="${event.id}">Забронировать</button>
        ${
          user?.role === "admin"
            ? `
              <button type="button" class="mini-button" data-edit-event="${event.id}">Редактировать</button>
              <button type="button" class="mini-button danger" data-delete-event="${event.id}">Удалить</button>
            `
            : ""
        }
      </div>
    `;
    elements.eventsList.appendChild(article);
  });
}

function renderBookings() {
  elements.bookingsList.innerHTML = "";

  if (!state.accessToken) {
    elements.bookingsList.appendChild(
      createEmptyState("Авторизуйся, чтобы увидеть свои бронирования."),
    );
    return;
  }

  if (state.bookings.length === 0) {
    elements.bookingsList.appendChild(
      createEmptyState("Пока нет бронирований. Можно оформить первую бронь из списка событий."),
    );
    return;
  }

  state.bookings.forEach((booking) => {
    const badgeClass =
      booking.status === "cancelled"
        ? "cancelled"
        : booking.status === "confirmed"
          ? "confirmed"
          : "pending";

    const article = document.createElement("article");
    article.className = "booking-card";
    article.innerHTML = `
      <div class="booking-header">
        <div>
          <div class="booking-title">Бронь #${booking.id}</div>
          <div class="booking-meta">
            event_id=${booking.event_id} · user_id=${booking.user_id}<br />
            создано: ${formatDate(booking.created_at)}
          </div>
        </div>
        <span class="mini-tag ${badgeClass}">${booking.status}</span>
      </div>
      <div class="booking-meta">Стоимость на момент брони: ${Number(booking.price_at_booking).toFixed(2)} RUB</div>
      <div class="card-actions">
        <button type="button" class="mini-button" data-open-booking="${booking.id}">Открыть</button>
        ${
          booking.status !== "cancelled"
            ? `<button type="button" class="mini-button danger" data-cancel-booking="${booking.id}">Отменить</button>`
            : ""
        }
      </div>
    `;
    elements.bookingsList.appendChild(article);
  });
}

async function loadHealth() {
  const services = [
    ["auth", "/health/auth"],
    ["events", "/health/events"],
    ["bookings", "/health/bookings"],
  ];

  await Promise.all(
    services.map(async ([key, url]) => {
      try {
        const result = await apiRequest(url);
        state.serviceStatus[key] = {
          label: state.serviceStatus[key].label,
          ok: true,
          detail: `${result.service || key} · ${result.database || "ok"}`,
        };
      } catch (error) {
        state.serviceStatus[key] = {
          label: state.serviceStatus[key].label,
          ok: false,
          detail: error.message,
        };
      }
    }),
  );

  renderServiceStatus();
}

async function loadEvents() {
  try {
    state.events = await apiRequest("/api/events/");
    renderEvents();
  } catch (error) {
    showToast(`Не удалось загрузить события: ${error.message}`, "error");
  }
}

async function loadBookings() {
  if (!state.accessToken) {
    state.bookings = [];
    renderBookings();
    return;
  }

  try {
    state.bookings = await apiRequest("/api/bookings/my", { auth: true });
    renderBookings();
  } catch (error) {
    showToast(`Не удалось загрузить бронирования: ${error.message}`, "error");
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const email = formData.get("email");
  const password = formData.get("password");

  try {
    await apiRequest("/api/auth/register", {
      method: "POST",
      json: { email, password },
    });
    state.userEmail = String(email || "");
    localStorage.setItem(storageKeys.userEmail, state.userEmail);
    event.currentTarget.reset();
    showToast("Пользователь зарегистрирован. Теперь можно логиниться.");
  } catch (error) {
    showToast(`Регистрация не удалась: ${error.message}`, "error");
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const email = String(formData.get("email") || "");
  const password = String(formData.get("password") || "");

  try {
    const result = await apiRequest("/api/auth/login", {
      method: "POST",
      form: { username: email, password },
    });
    saveSession({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
      email,
    });
    event.currentTarget.reset();
    showToast("Логин успешен. Сессия обновлена.");
    await Promise.all([loadEvents(), loadBookings(), loadHealth()]);
  } catch (error) {
    showToast(`Логин не удался: ${error.message}`, "error");
  }
}

async function handleRefresh() {
  if (!state.refreshToken) {
    showToast("Нет refresh token для обновления сессии.", "error");
    return;
  }

  try {
    const result = await apiRequest("/api/auth/refresh", {
      method: "POST",
      json: { refresh_token: state.refreshToken },
    });
    saveSession({
      accessToken: result.access_token,
      refreshToken: result.refresh_token,
      email: state.userEmail,
    });
    showToast("Access token обновлен.");
    await Promise.all([loadBookings(), loadHealth()]);
  } catch (error) {
    showToast(`Refresh не удался: ${error.message}`, "error");
  }
}

async function handleLogout() {
  if (!state.refreshToken) {
    clearSession();
    showToast("Локальная сессия очищена.");
    return;
  }

  try {
    await apiRequest("/api/auth/logout", {
      method: "POST",
      json: { refresh_token: state.refreshToken },
    });
  } catch (error) {
    showToast(`Logout через API не удался: ${error.message}`, "error");
  } finally {
    clearSession();
    showToast("Сессия завершена.");
    await loadBookings();
  }
}

function resetEventForm() {
  elements.eventForm.reset();
  elements.eventForm.elements.eventId.value = "";
  elements.eventSubmitBtn.textContent = "Создать событие";
}

function fillEventForm(event) {
  elements.eventForm.elements.eventId.value = event.id;
  elements.eventForm.elements.title.value = event.title;
  elements.eventForm.elements.description.value = event.description || "";
  elements.eventForm.elements.price.value = event.price;
  elements.eventForm.elements.total_tickets.value = event.total_tickets;
  elements.eventForm.elements.date_start.value = event.date_start.slice(0, 16);
  elements.eventForm.elements.date_end.value = event.date_end.slice(0, 16);
  elements.eventSubmitBtn.textContent = "Сохранить изменения";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function handleEventSubmit(event) {
  event.preventDefault();
  const user = getCurrentUser();
  if (!user || user.role !== "admin") {
    showToast("Только admin может создавать и менять мероприятия.", "error");
    return;
  }

  const formData = new FormData(event.currentTarget);
  const eventId = formData.get("eventId");
  const payload = {
    title: String(formData.get("title") || ""),
    description: String(formData.get("description") || ""),
    price: Number(formData.get("price")).toFixed(2),
    total_tickets: Number(formData.get("total_tickets")),
    date_start: new Date(String(formData.get("date_start"))).toISOString(),
    date_end: new Date(String(formData.get("date_end"))).toISOString(),
  };

  try {
    if (eventId) {
      await apiRequest(`/api/events/${eventId}`, {
        method: "PATCH",
        auth: true,
        json: payload,
      });
      showToast(`Мероприятие #${eventId} обновлено.`);
    } else {
      await apiRequest("/api/events/", {
        method: "POST",
        auth: true,
        json: payload,
      });
      showToast("Новое мероприятие создано.");
    }

    resetEventForm();
    await loadEvents();
  } catch (error) {
    showToast(`Операция с мероприятием не удалась: ${error.message}`, "error");
  }
}

async function handleBookEvent(eventId) {
  const user = getCurrentUser();
  if (!user) {
    showToast("Сначала войди в систему, чтобы бронировать билеты.", "error");
    return;
  }

  if (!state.userEmail) {
    showToast("Не найден email пользователя в локальной сессии.", "error");
    return;
  }

  try {
    await apiRequest("/api/bookings/", {
      method: "POST",
      auth: true,
      json: {
        event_id: Number(eventId),
        user_email: state.userEmail,
      },
    });
    showToast(`Бронирование для event_id=${eventId} создано.`);
    await loadBookings();
  } catch (error) {
    showToast(`Не удалось создать бронь: ${error.message}`, "error");
  }
}

async function handleDeleteEvent(eventId) {
  const user = getCurrentUser();
  if (!user || user.role !== "admin") {
    showToast("Удаление доступно только admin.", "error");
    return;
  }

  try {
    await apiRequest(`/api/events/${eventId}`, {
      method: "DELETE",
      auth: true,
    });
    showToast(`Мероприятие #${eventId} удалено.`);
    await loadEvents();
  } catch (error) {
    showToast(`Не удалось удалить мероприятие: ${error.message}`, "error");
  }
}

async function handleCancelBooking(bookingId) {
  try {
    await apiRequest(`/api/bookings/${bookingId}/cancel`, {
      method: "POST",
      auth: true,
    });
    showToast(`Бронь #${bookingId} отменена.`);
    await loadBookings();
  } catch (error) {
    showToast(`Отмена не удалась: ${error.message}`, "error");
  }
}

async function handleOpenBooking(bookingId) {
  try {
    const booking = await apiRequest(`/api/bookings/${bookingId}`, {
      auth: true,
    });
    showToast(
      `Бронь #${booking.id}: event_id=${booking.event_id}, status=${booking.status}`,
    );
  } catch (error) {
    showToast(`Не удалось открыть бронь: ${error.message}`, "error");
  }
}

function wireActions() {
  document.getElementById("register-form").addEventListener("submit", handleRegister);
  document.getElementById("login-form").addEventListener("submit", handleLogin);
  document.getElementById("refresh-token-btn").addEventListener("click", handleRefresh);
  document.getElementById("logout-btn").addEventListener("click", handleLogout);
  document.getElementById("load-events-btn").addEventListener("click", loadEvents);
  document.getElementById("load-bookings-btn").addEventListener("click", loadBookings);
  document.getElementById("refresh-all-btn").addEventListener("click", async () => {
    await Promise.all([loadEvents(), loadBookings(), loadHealth()]);
  });
  document.getElementById("refresh-health-btn").addEventListener("click", loadHealth);
  document.getElementById("reset-event-form-btn").addEventListener("click", resetEventForm);
  elements.eventForm.addEventListener("submit", handleEventSubmit);
  elements.eventSearch.addEventListener("input", renderEvents);

  elements.eventsList.addEventListener("click", async (event) => {
    const target = event.target.closest("button");
    if (!target) {
      return;
    }

    if (target.dataset.bookEvent) {
      await handleBookEvent(target.dataset.bookEvent);
      return;
    }

    if (target.dataset.editEvent) {
      const selected = state.events.find((item) => String(item.id) === target.dataset.editEvent);
      if (selected) {
        fillEventForm(selected);
      }
      return;
    }

    if (target.dataset.deleteEvent) {
      await handleDeleteEvent(target.dataset.deleteEvent);
    }
  });

  elements.bookingsList.addEventListener("click", async (event) => {
    const target = event.target.closest("button");
    if (!target) {
      return;
    }

    if (target.dataset.cancelBooking) {
      await handleCancelBooking(target.dataset.cancelBooking);
      return;
    }

    if (target.dataset.openBooking) {
      await handleOpenBooking(target.dataset.openBooking);
    }
  });
}

async function bootstrap() {
  renderSession();
  renderServiceStatus();
  renderEvents();
  renderBookings();
  wireActions();

  await Promise.all([loadHealth(), loadEvents()]);
  if (state.accessToken) {
    await loadBookings();
  }
}

bootstrap();
