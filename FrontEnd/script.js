const API_BASE = "http://localhost:8080";

function saveTokens(access, refresh) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}
function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}
function getAccess() { return localStorage.getItem("access_token"); }
function getRefresh() { return localStorage.getItem("refresh_token"); }


async function apiFetch(path, opts = {}, retry = true) {
  const access = getAccess();
  opts.headers = opts.headers || {};

  if (opts.body && !opts.headers["Content-Type"]) {
    opts.headers["Content-Type"] = "application/json";
  }

  if (access) {
    opts.headers["Authorization"] = "Bearer " + access;
  }

  const res = await fetch(API_BASE + path, opts);

  if (res.status === 401 && retry) {
    const refresh = getRefresh();
    if (!refresh) {
      clearTokens();
      throw { code: 401 };
    }
    try {
      const rr = await fetch(API_BASE + "/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshtoken: refresh })
      });
      if (!rr.ok) throw new Error("refresh failed");
      const jr = await rr.json();
      const newAccess = jr.access_token || jr.result?.access_token;
      const newRefresh = jr.refresh_token || jr.result?.refresh_token;
      saveTokens(newAccess, newRefresh || refresh);
      return apiFetch(path, opts, false);
    } catch (e) {
      clearTokens();
      throw { code: 401 };
    }
  }

  return res;
}

const qs = (x) => document.querySelector(x);
const qsa = (x) => Array.from(document.querySelectorAll(x));

function showLoginPanel() {
  qs("#login-panel").classList.remove("hidden");
  qs("#main-app").classList.add("hidden");
}
function showMainApp() {
  qs("#login-panel").classList.add("hidden");
  qs("#main-app").classList.remove("hidden");
}

function renderUserArea() {
  const ua = qs("#user-area");
  ua.innerHTML = "";
  if (!getAccess()) return;

  const logoutBtn = document.createElement("button");
  logoutBtn.textContent = "Wyloguj";

  logoutBtn.onclick = async () => {
    const ref = getRefresh();
    if (ref) {
      await fetch(API_BASE + "/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshtoken: ref })
      });
    }

    clearTokens();

    currentConvId = null;
    qs("#chat-window").innerHTML = "";
    qs("#conversations-list").innerHTML = "";
    qs("#chat-header").textContent = "Wybierz rozmowę";

    showLoginPanel();
    renderUserArea();
  };

  ua.appendChild(logoutBtn);
}


let currentConvId = null;

async function loadConversations() {
  try {
    const res = await apiFetch("/conversations", { method: "GET" });
    if (!res.ok) return showLoginPanel();
    const j = await res.json();
    renderConversations(j.conversations || []);
  } catch (e) {
    console.error("loadConversations error:", e);
  }
}

function renderConversations(convs) {
  const list = qs("#conversations-list");
  list.innerHTML = "";
  if (!convs.length) {
    list.innerHTML = "<div class='muted small'>Brak konwersacji</div>";
    return;
  }

  convs.forEach(c => {
    const id = c.id;
    const el = document.createElement("div");
    el.className = "conv-item";
    el.dataset.id = id;

    el.innerHTML = `
      <div><strong>Rozmowa z dnia ${new Date(c.created).toLocaleString("pl-PL")}</strong></div>
    `;

    el.onclick = () => {
      qsa(".conv-item").forEach(x => x.classList.remove("active"));
      el.classList.add("active");
      openConversation(id);

      const input = qs("#chat-input");
      if (input) {
        input.value = "";
        input.focus();
      }
    };

    list.appendChild(el);
  });
}


async function openConversation(id) {
  currentConvId = id;
  qs("#chat-header").textContent = `Rozmowa:`;
  qs("#chat-window").innerHTML = "";

  try {
    const res = await apiFetch(`/history/${id}`, { method: "GET" });
    if (!res.ok) return;

    const j = await res.json();
    const history = j.history || [];

    history.forEach(row => {
      if (row.usermessage)
        appendMsg("user", row.usermessage, row.id, row.rating);

      const botText = row.llmmessage ?? row.assistant ?? row.response;
      if (botText)
        appendMsg("bot", botText, row.id, row.rating);
    });

    scrollChatToBottom();
  } catch (e) {
    console.error("openConversation error:", e);
  }
}

async function sendRate(historyId, rateValue) {
  try {
    const res = await apiFetch(`/chat/rate/${historyId}`, {
      method: "POST",
      body: JSON.stringify({ rate: rateValue })
    });

    if (!res.ok) {
      console.error("Błąd podczas oceniania odpowiedzi");
      return;
    }

    const j = await res.json();
    console.log("Ocena zapisana:", j);
  } catch (e) {
    console.error("sendRate error:", e);
  }
}

function appendMsg(kind, text, historyId = null, rate) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${kind}`;

  const row = document.createElement("div");
  row.className = "msg-row";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = `
    <div class="meta">${kind === "user" ? "Ty" : "Asystent"}</div>
    <div class="txt">${text}</div>
  `;

  row.appendChild(bubble);
  wrap.appendChild(row);

if (kind === "bot") {

    const rateContainer = document.createElement("div");
    rateContainer.className = "rate-container";

    const question = document.createElement("div");
    question.className = "rate-question";
    question.textContent = "Czy ta odpowiedź była pomocna?";

    const rateBox = document.createElement("div");
    rateBox.className = "rate-box";

    const up = document.createElement("button");
    up.className = "rate-up";
    up.textContent = "Tak";

    const down = document.createElement("button");
    down.className = "rate-down";
    down.textContent = "Nie";

    rateBox.appendChild(up);
    rateBox.appendChild(down);

    rateContainer.appendChild(question);
    rateContainer.appendChild(rateBox);
    wrap.appendChild(rateContainer);

    console.log("appendMsg historyId =", historyId);

    if (historyId !== null && historyId !== undefined) {

        up.onclick = () => {
          rateBox.style.display = "none";
            up.classList.add("active");
            down.classList.remove("active");
            question.textContent = "Odpowiedź oceniona pozytywnie";
            sendRate(historyId, true);
        };

        down.onclick = () => {
          rateBox.style.display = "none";
            down.classList.add("active");
            up.classList.remove("active");
            question.textContent = "Odpowiedź oceniona negatywnie";
            sendRate(historyId, false);
        };
    if (rate !== null){
        rateBox.style.display = "none";
        if (rate == true){
            up.classList.add("active");
            down.classList.remove("active");
            question.textContent = "Odpowiedź oceniona pozytywnie";
        }else if (rate === false){
            down.classList.add("active");
            up.classList.remove("active");
            question.textContent = "Odpowiedź oceniona negatywnie";
        }
    }
    } else {
        console.warn("Brak historyId — rating nie zostanie wysłany.");
    }
}


  qs("#chat-window").appendChild(wrap);
}

function scrollChatToBottom() {
  const w = qs("#chat-window");
  w.scrollTop = w.scrollHeight;
}

async function sendChatMessage() {
  const txt = qs("#chat-input").value.trim();
  if (!txt || !currentConvId) return;

  appendMsg("user", txt);
  qs("#chat-input").value = "";

  const placeholder = document.createElement("div");
  placeholder.className = "msg bot";
  placeholder.innerHTML = "<div class='txt'>Asystent pisze...</div>";
  qs("#chat-window").appendChild(placeholder);

  scrollChatToBottom();

  try {
    const res = await apiFetch(`/chat/${currentConvId}`, {
      method: "POST",
      body: JSON.stringify({ usermessage: txt })
    });

    const j = await res.json();
    placeholder.remove();

    appendMsg(
      "bot",
      j.response ?? j.llmmessage ?? j.assistant ?? "Brak odpowiedzi",
      j.historyid
    );

    scrollChatToBottom();
  } catch (e) {
    placeholder.textContent = "Błąd podczas wysyłania wiadomości";
  }
}

async function createNewConversation() {
  try {
    const res = await apiFetch("/conversations/new", { method: "POST" });
    const j = await res.json();
    await loadConversations();
    openConversation(j.conversation_id);
  } catch (e) {
    alert("Nie można stworzyć konwersacji");
  }
}

async function doLogin() {
  const login = qs("#login-login").value.trim();
  const password = qs("#login-password").value.trim();
  if (!login || !password) {
    qs("#login-msg").textContent = "Podaj login i hasło";
    return;
  }

  qs("#login-msg").textContent = "Logowanie...";

  try {
    const res = await fetch(API_BASE + "/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login, password })
    });

    const j = await res.json();
    if (!j.result) throw new Error("Brak result");

    saveTokens(j.result.access_token, j.result.refresh_token);
    qs("#login-msg").textContent = "Zalogowano";

    renderUserArea();
    showMainApp();
    await loadConversations();
  } catch (e) {
    console.error("login error", e);
    qs("#login-msg").textContent = "Błąd logowania";
  }
}

function bindUi() {
  qs("#btn-login").addEventListener("click", doLogin);
  qs("#btn-new-conv").addEventListener("click", createNewConversation);
  qs("#btn-send").addEventListener("click", sendChatMessage);
  qs("#chat-input").addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendChatMessage();
  });
}

window.addEventListener("load", () => {
  bindUi();
  if (getAccess()) {
    renderUserArea();
    showMainApp();
    loadConversations();
  } else {
    showLoginPanel();
  }
});
