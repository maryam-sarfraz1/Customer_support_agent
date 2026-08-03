"""Customer-facing chat page and embeddable widget script.

Both are white-labeled through Settings (company name, brand color,
greeting) so each client deployment looks like its own product.
"""

from __future__ import annotations

import json

from app.core.config import Settings

_CHAT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__COMPANY__ — Support</title>
<style>
  :root {
    --brand: __BRAND__;
    --bg: #f7f5f1;
    --card: #ffffff;
    --ink: #26241f;
    --ink-dim: #7d7a72;
    --line: #e6e2da;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; }
  body {
    background: var(--bg); color: var(--ink);
    font: 400 1rem/1.5 "Segoe UI", system-ui, sans-serif;
    display: flex; flex-direction: column;
  }
  body.embed { background: var(--card); }

  header {
    background: var(--brand); color: #fff;
    padding: .9rem 1.3rem; display: flex; align-items: center; gap: .7rem;
  }
  header .dot { width: 9px; height: 9px; border-radius: 50%; background: #8ee6a1; }
  header h1 { font-size: 1rem; font-weight: 600; margin: 0; }
  header .sub { font-size: .75rem; opacity: .85; }

  #chat {
    flex: 1; overflow-y: auto; padding: 1.2rem;
    display: flex; flex-direction: column; gap: .8rem;
    max-width: 720px; width: 100%; margin: 0 auto;
  }
  .msg { max-width: 85%; padding: .65rem .9rem; border-radius: 14px; font-size: .95rem; white-space: pre-wrap; }
  .msg.user { align-self: flex-end; background: var(--brand); color: #fff; border-bottom-right-radius: 4px; }
  .msg.bot { align-self: flex-start; background: var(--card); border: 1px solid var(--line); border-bottom-left-radius: 4px; }
  body.embed .msg.bot { background: var(--bg); }

  .cites { display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .55rem; }
  .cite {
    font-size: .72rem; color: var(--ink-dim); background: var(--bg);
    border: 1px solid var(--line); border-radius: 999px; padding: .1rem .55rem;
  }
  body.embed .cite { background: var(--card); }
  .notice { font-size: .78rem; color: var(--ink-dim); margin-top: .5rem; font-style: italic; }

  .rate { margin-top: .5rem; display: flex; gap: .4rem; align-items: center; }
  .rate span { font-size: .72rem; color: var(--ink-dim); }
  .rate button {
    background: none; border: 1px solid var(--line); border-radius: 6px;
    padding: .1rem .45rem; cursor: pointer; font-size: .85rem;
  }
  .rate button:hover { border-color: var(--brand); }
  .rate .done { font-size: .75rem; color: var(--brand); }

  form {
    display: flex; gap: .6rem; padding: .9rem 1.2rem 1.1rem;
    max-width: 720px; width: 100%; margin: 0 auto;
  }
  input {
    flex: 1; border: 1px solid var(--line); border-radius: 10px;
    padding: .7rem .9rem; font-size: .95rem; background: var(--card);
  }
  input:focus { outline: 2px solid var(--brand); border-color: transparent; }
  button.send {
    background: var(--brand); color: #fff; border: none; border-radius: 10px;
    padding: .7rem 1.2rem; font-size: .95rem; font-weight: 600; cursor: pointer;
  }
  button.send:hover { filter: brightness(1.07); }
  button.send:focus-visible, .rate button:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }
  .typing { color: var(--ink-dim); font-style: italic; }
</style>
</head>
<body>
<header>
  <span class="dot" aria-hidden="true"></span>
  <div>
    <h1>__COMPANY__ support</h1>
    <div class="sub">AI assistant · answers cite our official docs · humans step in when needed</div>
  </div>
</header>
<div id="chat" aria-live="polite"></div>
<form onsubmit="send(event)">
  <input id="box" placeholder="Type your question…" autocomplete="off" aria-label="Your question">
  <button class="send" type="submit">Send</button>
</form>
<script>
const GREETING = __GREETING__;
let conversationId = null;
if (new URLSearchParams(location.search).get("embed") === "1") document.body.classList.add("embed");

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function add(kind, html) {
  const d = document.createElement("div");
  d.className = "msg " + kind;
  d.innerHTML = html;
  document.getElementById("chat").appendChild(d);
  d.scrollIntoView({ block: "end" });
  return d;
}
add("bot", esc(GREETING));

async function send(ev) {
  ev.preventDefault();
  const box = document.getElementById("box");
  const text = box.value.trim();
  if (!text) return;
  box.value = "";
  add("user", esc(text));
  const wait = add("bot", '<span class="typing">Thinking…</span>');
  try {
    const res = await fetch("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, conversation_id: conversationId, channel: "web-widget" }),
    });
    if (!res.ok) throw new Error(res.status);
    const r = await res.json();
    conversationId = r.conversation_id;
    let html = esc(r.answer);
    const cites = (r.citations || []).map((c) => `<span class="cite">[${c.index}] ${esc(c.source)}</span>`).join("");
    if (cites) html += `<div class="cites">${cites}</div>`;
    if (r.escalated) html += `<div class="notice">A human team member has been looped in and will follow up.</div>`;
    html += rateBar(r.conversation_id, r.message_id);
    wait.innerHTML = html;
  } catch {
    wait.innerHTML = esc("Sorry — I couldn't process that just now. Please try again in a moment.");
  }
}

function rateBar(convId, msgId) {
  const id = "r" + msgId;
  return `<div class="rate" id="${id}"><span>Helpful?</span>` +
    `<button type="button" aria-label="Yes, helpful" onclick="rate('${convId}','${msgId}',5,'${id}')">&#128077;</button>` +
    `<button type="button" aria-label="No, not helpful" onclick="rate('${convId}','${msgId}',1,'${id}')">&#128078;</button></div>`;
}
async function rate(convId, msgId, rating, elId) {
  try {
    await fetch("/api/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation_id: convId, message_id: msgId, rating }),
    });
    document.getElementById(elId).innerHTML = '<span class="done">Thanks for the feedback!</span>';
  } catch { /* feedback is best-effort */ }
}
</script>
</body>
</html>"""

_WIDGET_TEMPLATE = """(function () {
  if (document.getElementById("sw-bubble")) return;
  var origin = document.currentScript && document.currentScript.src
    ? new URL(document.currentScript.src).origin
    : window.location.origin;

  var bubble = document.createElement("button");
  bubble.id = "sw-bubble";
  bubble.setAttribute("aria-label", "Open support chat");
  bubble.innerHTML = "&#128172;";
  bubble.style.cssText =
    "position:fixed;bottom:22px;right:22px;width:56px;height:56px;border-radius:50%;" +
    "border:none;cursor:pointer;font-size:24px;color:#fff;z-index:99999;" +
    "box-shadow:0 4px 14px rgba(0,0,0,.25);background:__BRAND__;";

  var frame = document.createElement("iframe");
  frame.id = "sw-frame";
  frame.title = "__COMPANY__ support chat";
  frame.src = origin + "/chat?embed=1";
  frame.style.cssText =
    "position:fixed;bottom:90px;right:22px;width:380px;height:560px;max-width:calc(100vw - 32px);" +
    "max-height:calc(100vh - 120px);border:1px solid #ddd;border-radius:14px;z-index:99999;" +
    "box-shadow:0 8px 30px rgba(0,0,0,.25);display:none;background:#fff;";

  bubble.addEventListener("click", function () {
    var open = frame.style.display !== "none";
    frame.style.display = open ? "none" : "block";
    bubble.innerHTML = open ? "&#128172;" : "&#10005;";
  });

  document.body.appendChild(bubble);
  document.body.appendChild(frame);
})();"""


def render_chat_html(settings: Settings) -> str:
    return (
        _CHAT_TEMPLATE
        .replace("__COMPANY__", settings.company_name)
        .replace("__BRAND__", settings.brand_color)
        .replace("__GREETING__", json.dumps(settings.chat_greeting))
    )


def render_widget_js(settings: Settings) -> str:
    return (
        _WIDGET_TEMPLATE
        .replace("__COMPANY__", settings.company_name)
        .replace("__BRAND__", settings.brand_color)
    )
