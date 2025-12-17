

const API_BASE = "http://localhost:8080";
let accessToken = null;
let refreshToken = null;
let currentConvId = null;
const qs = (x) => document.querySelector(x);
const qsa = (x) => Array.from(document.querySelectorAll(x));

//save tokens in memory
function saveTokens(access, refresh) {
  accessToken = access;
  refreshToken = refresh;
}
//clear all tokens
function clearTokens() {
   accessToken = null;
   refreshToken = null;
}
//get access token
function getAccess() { return accessToken; }

//get refresh token
function getRefresh() { return refreshToken; }

//access token refresh fetch api
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

  if (res.status === 401 && retry) { //check if access token is valid
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
      saveTokens(jr.access_token, jr.refresh_token);
      return apiFetch(path, opts, false);
    } catch (e) {
      clearTokens();
      throw { code: 401 };
    }
  }

  return res;
}

//show Login panel and hide app
function showLoginPanel() {
  qs("#login-panel").classList.remove("hidden");
  qs("#main-app").classList.add("hidden");
}

//shop app and hide login panel
function showMainApp() {
  qs("#login-panel").classList.add("hidden");
  qs("#main-app").classList.remove("hidden");
}

//create logout button and header
function renderUserLogoutArea() {
  const ua = qs("#user-login-area");
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
    renderUserLogoutArea();
  };

  ua.appendChild(logoutBtn);
}

//get all conversations of currunt logon user
async function getConversations() {
  try {
    const res = await apiFetch("/conversations", { method: "GET" });
    if (!res.ok) return showLoginPanel();
    const j = await res.json();
    renderConversations(j.conversations || []);
  } catch (e) {
    console.error("getConversations error:", e);
  }
}

//render all conversations of currunt logon user
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

    el.innerHTML = `<div><b>Rozmowa z dnia ${new Date(c.created).toLocaleString("pl-PL")}</b></div>`;

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

//open conversation
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
      if (row.usermessage) {
        appendMsg("user", row.usermessage, row.id, null);
      }

      if (row.llmmessage){
        appendMsg("bot", row.llmmessage, row.id, row.rating);
      }
    });

    scrollChatToBottom();
  } catch (e) {
    console.error("openConversation error:", e);
  }
}

//send chatbot response rating
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

    const stat = await res.json();
    console.log("Ocena zapisana:", stat);
  } catch (e) {
    console.error("sendRate error:", e);
  }
}

//add message in chat
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

    if (historyId != null) {
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

//scroll chat to bottom
function scrollChatToBottom() {
  const w = qs("#chat-window");
  w.scrollTop = w.scrollHeight;
}

//send message to backend
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

    appendMsg("bot", j.llmmessage, j.historyid, null);

    scrollChatToBottom();
  } catch (e) {
    placeholder.textContent = "Błąd podczas wysyłania wiadomości";
  }
}

//create new conversation
async function createNewConversation() {
  try {
    const res = await apiFetch("/conversations/new", { method: "POST" });
    const j = await res.json();
    await getConversations();
    openConversation(j.conversation_id);
  } catch (e) {
    alert("Nie można stworzyć konwersacji");
  }
}

//login
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

  

    renderUserLogoutArea();
    showMainApp();
    await getConversations();

    qs("#login-login").value = "";
    qs("#login-password").value = "";
    qs("#login-msg").textContent = "";

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
    renderUserLogoutArea();
    showMainApp();
    getConversations();
  } else {
    showLoginPanel();
  }
});
