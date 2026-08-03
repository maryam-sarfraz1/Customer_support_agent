"""Single-file admin dashboard served at /admin.

Dependency-free (vanilla JS, system fonts) so it works offline and inside
locked-down networks. Talks to the same REST API the rest of the world uses.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Support Ops — Admin</title>
<style>
  :root {
    --bg: #10131f;
    --surface: #181c2c;
    --surface-2: #1f2437;
    --line: #2b3149;
    --ink: #e9e7de;
    --ink-dim: #9aa0b4;
    --amber: #e8a33d;       /* AI health / signature */
    --teal: #55b3a5;        /* resolved / positive */
    --red: #d96c5f;         /* escalations / errors */
    --blue: #7aa2e8;        /* links / customer */
    font-size: 16px;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; }
  body {
    background: var(--bg); color: var(--ink);
    font: 400 1rem/1.5 "Segoe UI", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .mono { font-family: Consolas, "Cascadia Mono", ui-monospace, monospace; }

  /* ---------- header ---------- */
  header {
    display: flex; align-items: baseline; gap: 1rem;
    padding: 1.1rem 2rem; border-bottom: 1px solid var(--line);
    background: var(--surface);
  }
  .wordmark {
    font-family: Georgia, "Iowan Old Style", serif;
    font-size: 1.25rem; letter-spacing: .01em; margin: 0;
  }
  .wordmark em { color: var(--amber); font-style: normal; }
  header .sub { color: var(--ink-dim); font-size: .8rem; }
  header .spacer { flex: 1; }
  #whoami { color: var(--ink-dim); font-size: .8rem; }
  #logoutBtn {
    background: none; border: 1px solid var(--line); color: var(--ink-dim);
    border-radius: 6px; padding: .25rem .7rem; font-size: .8rem; cursor: pointer;
  }
  #logoutBtn:hover { color: var(--ink); border-color: var(--ink-dim); }

  main { max-width: 1080px; margin: 0 auto; padding: 1.6rem 2rem 4rem; }
  h2 {
    font-family: Georgia, serif; font-weight: 400; font-size: 1.05rem;
    color: var(--ink-dim); letter-spacing: .06em; text-transform: uppercase;
    margin: 2.2rem 0 .9rem;
  }
  h2:first-child { margin-top: 0; }

  /* ---------- login ---------- */
  #loginView {
    min-height: calc(100vh - 70px); display: flex;
    align-items: center; justify-content: center; padding: 2rem;
  }
  .loginCard {
    width: 340px; background: var(--surface); border: 1px solid var(--line);
    border-radius: 12px; padding: 2rem;
  }
  .loginCard h1 {
    font-family: Georgia, serif; font-weight: 400;
    font-size: 1.3rem; margin: 0 0 .3rem;
  }
  .loginCard p { color: var(--ink-dim); font-size: .85rem; margin: 0 0 1.4rem; }
  label { display: block; font-size: .78rem; color: var(--ink-dim); margin: .9rem 0 .3rem; }
  input {
    width: 100%; background: var(--bg); color: var(--ink);
    border: 1px solid var(--line); border-radius: 8px;
    padding: .6rem .75rem; font-size: .95rem;
  }
  input:focus { outline: 2px solid var(--amber); outline-offset: 1px; border-color: transparent; }
  .btn {
    background: var(--amber); color: #221a08; font-weight: 600;
    border: none; border-radius: 8px; padding: .65rem 1rem;
    font-size: .95rem; cursor: pointer; width: 100%; margin-top: 1.3rem;
  }
  .btn:hover { filter: brightness(1.08); }
  .btn:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
  .error { color: var(--red); font-size: .85rem; margin-top: .8rem; min-height: 1.2em; }

  /* ---------- metric tiles ---------- */
  .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: .8rem; }
  .tile {
    background: var(--surface); border: 1px solid var(--line);
    border-radius: 10px; padding: .85rem .95rem .95rem;
  }
  .tile .v { font-size: 1.55rem; font-weight: 600; }
  .tile .k { font-size: .72rem; color: var(--ink-dim); letter-spacing: .05em; text-transform: uppercase; margin-top: .1rem; }
  .meter { height: 4px; background: var(--surface-2); border-radius: 2px; margin-top: .6rem; overflow: hidden; }
  .meter i { display: block; height: 100%; border-radius: 2px; background: var(--amber); }
  .meter.teal i { background: var(--teal); }
  .meter.red i { background: var(--red); }

  /* ---------- intents ---------- */
  .intents { display: flex; flex-direction: column; gap: .45rem; }
  .intentRow { display: grid; grid-template-columns: 130px 1fr 3.5rem; gap: .8rem; align-items: center; font-size: .85rem; }
  .intentRow .bar { height: 10px; background: var(--surface-2); border-radius: 5px; overflow: hidden; }
  .intentRow .bar i { display: block; height: 100%; background: var(--blue); border-radius: 5px; }
  .intentRow .n { text-align: right; color: var(--ink-dim); }

  /* ---------- tickets ---------- */
  .tableWrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 10px; background: var(--surface); }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; }
  th {
    text-align: left; color: var(--ink-dim); font-weight: 500; font-size: .72rem;
    text-transform: uppercase; letter-spacing: .06em;
    padding: .6rem .8rem; border-bottom: 1px solid var(--line);
  }
  td { padding: .55rem .8rem; border-bottom: 1px solid var(--line); vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  .pill {
    display: inline-block; padding: .1rem .55rem; border-radius: 999px;
    font-size: .72rem; border: 1px solid var(--line); color: var(--ink-dim);
  }
  .pill.open, .pill.escalated { color: var(--red); border-color: var(--red); }
  .pill.in_progress { color: var(--amber); border-color: var(--amber); }
  .pill.resolved, .pill.closed { color: var(--teal); border-color: var(--teal); }
  td select {
    background: var(--bg); color: var(--ink); border: 1px solid var(--line);
    border-radius: 6px; padding: .2rem .3rem; font-size: .78rem;
  }
  .empty { color: var(--ink-dim); font-size: .85rem; padding: 1rem; }

  /* ---------- chat tester ---------- */
  .chatPanel { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 1rem; }
  #chatLog { display: flex; flex-direction: column; gap: .7rem; max-height: 340px; overflow-y: auto; margin-bottom: .9rem; }
  .msg { max-width: 85%; padding: .55rem .8rem; border-radius: 10px; font-size: .9rem; white-space: pre-wrap; }
  .msg.user { align-self: flex-end; background: var(--surface-2); border: 1px solid var(--line); }
  .msg.bot  { align-self: flex-start; background: var(--bg); border: 1px solid var(--line); }
  .msg .meta { display: block; margin-top: .45rem; font-size: .72rem; color: var(--ink-dim); }
  .msg .meta b.ok { color: var(--teal); font-weight: 500; }
  .msg .meta b.warn { color: var(--red); font-weight: 500; }
  .chatForm { display: flex; gap: .6rem; }
  .chatForm input { flex: 1; }
  .chatForm button { width: auto; margin: 0; padding: .6rem 1.1rem; }

  .refreshRow { display: flex; align-items: center; gap: .8rem; margin-top: 1rem; }
  #refreshBtn {
    background: none; border: 1px solid var(--line); color: var(--ink-dim);
    border-radius: 8px; padding: .4rem .9rem; font-size: .82rem; cursor: pointer;
  }
  #refreshBtn:hover { color: var(--ink); }
  #updatedAt { color: var(--ink-dim); font-size: .75rem; }

  @media (max-width: 640px) {
    header, main { padding-left: 1rem; padding-right: 1rem; }
    .intentRow { grid-template-columns: 90px 1fr 3rem; }
  }
  @media (prefers-reduced-motion: no-preference) {
    .meter i, .intentRow .bar i { transition: width .5s ease; }
  }
</style>
</head>
<body>
<header>
  <h1 class="wordmark">Support<em>·</em>Ops</h1>
  <span class="sub">AI customer support console</span>
  <span class="spacer"></span>
  <span id="whoami"></span>
  <button id="logoutBtn" style="display:none" onclick="logout()">Sign out</button>
</header>

<div id="loginView">
  <form class="loginCard" onsubmit="login(event)">
    <h1>Sign in</h1>
    <p>Use a staff account (admin or agent role).</p>
    <label for="email">Email</label>
    <input id="email" type="email" autocomplete="username" required>
    <label for="password">Password</label>
    <input id="password" type="password" autocomplete="current-password" required>
    <button class="btn" type="submit">Sign in</button>
    <div class="error" id="loginError" role="alert"></div>
  </form>
</div>

<main id="appView" style="display:none">
  <h2>Last 30 days</h2>
  <div class="tiles" id="tiles"></div>

  <h2>Intents</h2>
  <div class="intents" id="intents"><div class="empty">No conversations yet.</div></div>

  <h2>Recent tickets</h2>
  <div class="tableWrap">
    <table>
      <thead><tr><th>Ticket</th><th>Subject</th><th>Status</th><th>Priority</th><th>Category</th><th>Customer</th><th>Opened</th></tr></thead>
      <tbody id="ticketRows"></tbody>
    </table>
    <div class="empty" id="ticketsEmpty" style="display:none">No tickets yet — they appear when the agent escalates or a complaint comes in.</div>
  </div>

  <h2>Chat tester</h2>
  <div class="chatPanel">
    <div id="chatLog"></div>
    <form class="chatForm" onsubmit="sendChat(event)">
      <input id="chatInput" placeholder="Ask the agent something, e.g. “What is the refund policy?”" autocomplete="off">
      <button class="btn" type="submit">Send</button>
    </form>
  </div>

  <div class="refreshRow">
    <button id="refreshBtn" onclick="loadAll()">Refresh data</button>
    <span id="updatedAt"></span>
  </div>
</main>

<script>
let token = sessionStorage.getItem("token") || "";
let chatConversationId = null;
const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: "Bearer " + token } : {}),
      ...(options.headers || {}),
    },
  });
  if (res.status === 401 || res.status === 403) { logout(); throw new Error("unauthorized"); }
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json();
}

async function login(ev) {
  ev.preventDefault();
  $("loginError").textContent = "";
  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: $("email").value, password: $("password").value }),
    });
    if (!res.ok) {
      $("loginError").textContent = res.status === 401
        ? "Wrong email or password."
        : "Sign-in failed (" + res.status + "). Is the API running?";
      return;
    }
    token = (await res.json()).access_token;
    sessionStorage.setItem("token", token);
    await enter();
  } catch {
    $("loginError").textContent = "Can't reach the API. Is the server running?";
  }
}

function logout() {
  token = ""; sessionStorage.removeItem("token");
  $("appView").style.display = "none";
  $("loginView").style.display = "flex";
  $("logoutBtn").style.display = "none";
  $("whoami").textContent = "";
}

async function enter() {
  const me = await api("/api/v1/auth/me");
  if (me.role === "customer") {
    logout();
    $("loginError").textContent = "This account has no staff access.";
    return;
  }
  $("whoami").textContent = me.email + " · " + me.role;
  $("loginView").style.display = "none";
  $("appView").style.display = "block";
  $("logoutBtn").style.display = "inline-block";
  await loadAll();
}

function tile(label, value, meterPct, meterClass) {
  const meter = meterPct == null ? "" :
    `<div class="meter ${meterClass || ""}"><i style="width:${Math.round(meterPct * 100)}%"></i></div>`;
  return `<div class="tile"><div class="v mono">${value ?? "—"}</div><div class="k">${label}</div>${meter}</div>`;
}

async function loadAll() {
  const o = await api("/api/v1/analytics/overview?days=30");
  $("tiles").innerHTML =
    tile("Conversations", o.conversations) +
    tile("Messages", o.messages) +
    tile("AI confidence", o.avg_confidence, o.avg_confidence, "") +
    tile("Deflection rate", o.deflection_rate == null ? null : Math.round(o.deflection_rate * 100) + "%", o.deflection_rate, "teal") +
    tile("Escalations", o.escalations, o.messages ? o.escalations / Math.max(o.messages, 1) : null, "red") +
    tile("Open tickets", o.open_tickets) +
    tile("Avg reply", o.avg_latency_ms == null ? null : (o.avg_latency_ms / 1000).toFixed(1) + "s") +
    tile("CSAT", o.avg_feedback_rating == null ? null : o.avg_feedback_rating + " / 5", (o.avg_feedback_rating || 0) / 5, "teal");

  const intents = Object.entries(o.intent_breakdown || {});
  if (intents.length) {
    const max = Math.max(...intents.map(([, n]) => n));
    $("intents").innerHTML = intents
      .sort((a, b) => b[1] - a[1])
      .map(([name, n]) =>
        `<div class="intentRow"><span>${name}</span>` +
        `<span class="bar"><i style="width:${Math.round((n / max) * 100)}%"></i></span>` +
        `<span class="n mono">${n}</span></div>`)
      .join("");
  }

  const tickets = await api("/api/v1/tickets?limit=25");
  $("ticketsEmpty").style.display = tickets.length ? "none" : "block";
  $("ticketRows").innerHTML = tickets.map((t) =>
    `<tr>
      <td class="mono">${t.id.slice(0, 8)}</td>
      <td>${escapeHtml(t.subject).slice(0, 80)}</td>
      <td><select onchange="setStatus('${t.id}', this.value)">
        ${["open","in_progress","escalated","resolved","closed"].map(
          (s) => `<option value="${s}" ${s === t.status ? "selected" : ""}>${s.replace("_", " ")}</option>`).join("")}
      </select></td>
      <td><span class="pill ${t.priority === "high" || t.priority === "urgent" ? "open" : ""}">${t.priority}</span></td>
      <td>${t.category}</td>
      <td>${escapeHtml(t.customer_email) || "—"}</td>
      <td class="mono">${new Date(t.created_at).toLocaleString()}</td>
    </tr>`).join("");

  $("updatedAt").textContent = "Updated " + new Date().toLocaleTimeString();
}

async function setStatus(id, status) {
  await api("/api/v1/tickets/" + id, { method: "PATCH", body: JSON.stringify({ status }) });
  await loadAll();
}

async function sendChat(ev) {
  ev.preventDefault();
  const text = $("chatInput").value.trim();
  if (!text) return;
  $("chatInput").value = "";
  addMsg("user", escapeHtml(text));
  const thinking = addMsg("bot", "…");
  try {
    const r = await api("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, conversation_id: chatConversationId, channel: "admin-tester" }),
    });
    chatConversationId = r.conversation_id;
    const cites = (r.citations || []).map((c) => `[${c.index}] ${escapeHtml(c.source)}`).join(" · ");
    thinking.innerHTML = escapeHtml(r.answer) +
      `<span class="meta">` +
      `confidence <b class="${r.confidence >= 0.55 ? "ok" : "warn"}">${r.confidence.toFixed(2)}</b>` +
      ` · intent ${r.intent}` +
      (r.escalated ? ` · <b class="warn">escalated</b>` : "") +
      (r.ticket_id ? ` · ticket <span class="mono">${r.ticket_id.slice(0, 8)}</span>` : "") +
      (cites ? `<br>${cites}` : "") +
      `</span>`;
    if (r.ticket_id) loadAll();
  } catch {
    thinking.textContent = "The agent didn't respond — check that the API and model provider are running.";
  }
}

function addMsg(kind, html) {
  const div = document.createElement("div");
  div.className = "msg " + kind;
  div.innerHTML = html;
  $("chatLog").appendChild(div);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
  return div;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

if (token) enter().catch(logout);
</script>
</body>
</html>"""
