const telegram = window.Telegram?.WebApp;
if (telegram) {
  telegram.ready();
  telegram.expand();
  telegram.disableVerticalSwipes?.();
}

const state = {
  initData: telegram?.initData || "",
  favorites: [],
  theme: localStorage.getItem("nettool-theme") || "neon",
};

const els = {
  target: document.getElementById("targetInput"),
  label: document.getElementById("labelInput"),
  port: document.getElementById("portInput"),
  output: document.getElementById("resultOutput"),
  status: document.getElementById("statusPill"),
  favoritesList: document.getElementById("favoritesList"),
  userBadge: document.getElementById("userBadge"),
  portCheckButton: document.getElementById("portCheckButton"),
  refreshFavorites: document.getElementById("refreshFavorites"),
  themeSelect: document.getElementById("themeSelect"),
};

const actionButtons = Array.from(document.querySelectorAll("[data-action]"));

function applyTheme(theme) {
  state.theme = ["neon", "chrome", "void"].includes(theme) ? theme : "neon";
  document.body.dataset.theme = state.theme;
  els.themeSelect.value = state.theme;
  localStorage.setItem("nettool-theme", state.theme);
}

function setStatus(text, isError = false) {
  els.status.textContent = text;
  els.status.classList.toggle("is-error", isError);
}

function setOutput(value) {
  els.output.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function getTarget() {
  return els.target.value.trim();
}

function getLabel() {
  return els.label.value.trim() || getTarget();
}

async function request(path, payload, options = {}) {
  const response = await fetch(path, {
    method: options.method || "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({ detail: "Server returned invalid JSON." }));
  if (!response.ok) {
    throw new Error(data.detail || "Request failed.");
  }
  return data;
}

async function runAction(action) {
  const target = getTarget();
  if (!target) {
    setStatus("Target required", true);
    setOutput("Enter a hostname or IP first.");
    return;
  }

  setStatus(`Running ${action}...`);
  setOutput("Please wait...");

  try {
    if (action === "save-favorite") {
      if (!state.initData) {
        throw new Error("Favorites are available only inside Telegram Web App.");
      }
      await request("/api/favorites", {
        label: getLabel(),
        host: target,
        init_data: state.initData,
      }, { method: "PUT" });
      setStatus("Favorite saved");
      setOutput(`Saved ${target} as favorite.`);
      await loadFavorites();
      return;
    }

    if (action === "geo") {
      const data = await request("/api/geo", { target });
      setStatus("Geo completed");
      setOutput(data);
      return;
    }

    const path = action === "ping" ? "/api/ping" : "/api/traceroute";
    const data = await request(path, { target });
    setStatus(`${action} completed`);
    setOutput(data.output.join("\n"));
  } catch (error) {
    setStatus("Action failed", true);
    setOutput(error.message);
  }
}

async function checkPort() {
  const target = getTarget();
  const port = Number(els.port.value || 0);
  if (!target) {
    setStatus("Target required", true);
    setOutput("Enter a hostname or IP first.");
    return;
  }

  setStatus("Checking port...");
  setOutput("Please wait...");

  try {
    const data = await request("/api/port-check", { target, port, timeout_seconds: 3 });
    setStatus("Port check completed");
    setOutput(data);
  } catch (error) {
    setStatus("Action failed", true);
    setOutput(error.message);
  }
}

function renderFavorites() {
  if (!state.favorites.length) {
    els.favoritesList.innerHTML = '<div class="favorite-item"><div><strong>No favorites yet</strong><div class="favorite-meta">Saved hosts will appear here.</div></div></div>';
    return;
  }

  els.favoritesList.innerHTML = state.favorites.map((item) => `
    <article class="favorite-item">
      <div>
        <strong>${escapeHtml(item.label)}</strong>
        <div class="favorite-meta">${escapeHtml(item.host)}</div>
      </div>
      <div class="favorite-actions">
        <button class="secondary compact" data-fill="${escapeHtml(item.host)}">Use</button>
        <button class="compact" data-delete="${escapeHtml(item.host)}">Delete</button>
      </div>
    </article>
  `).join("");

  document.querySelectorAll("[data-fill]").forEach((button) => {
    button.addEventListener("click", () => {
      els.target.value = button.dataset.fill || "";
      els.label.value = "";
    });
  });

  document.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await request("/api/favorites", {
          host: button.dataset.delete,
          init_data: state.initData,
        }, { method: "DELETE" });
        await loadFavorites();
      } catch (error) {
        setStatus("Delete failed", true);
        setOutput(error.message);
      }
    });
  });
}

async function loadFavorites() {
  if (!state.initData) {
    renderFavorites();
    return;
  }

  try {
    const data = await request("/api/favorites", { init_data: state.initData });
    state.favorites = data.items || [];
    renderFavorites();
  } catch (error) {
    setStatus("Favorites unavailable", true);
    setOutput(error.message);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

actionButtons.forEach((button) => {
  button.addEventListener("click", () => runAction(button.dataset.action));
});

els.portCheckButton.addEventListener("click", checkPort);
els.refreshFavorites.addEventListener("click", loadFavorites);
els.themeSelect.addEventListener("change", () => applyTheme(els.themeSelect.value));

const telegramUser = telegram?.initDataUnsafe?.user;
if (telegramUser) {
  els.userBadge.textContent = `${telegramUser.first_name || "User"} #${telegramUser.id}`;
} else {
  els.userBadge.textContent = "Browser preview";
}

applyTheme(state.theme);
renderFavorites();
loadFavorites();
