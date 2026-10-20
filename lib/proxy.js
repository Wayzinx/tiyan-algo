// 后端核心逻辑：本机 server.mjs 和 Cloudflare Pages Functions 共用。
// 只做三件事：保管 DeepSeek key、校验访问密码、把请求流式转发给 DeepSeek。

const ROLES = new Set(["system", "user", "assistant", "tool"]);
const ERRORS = {
  400: ["bad_request", 400],
  401: ["bad_key", 502],
  402: ["insufficient_balance", 402],
  422: ["bad_request", 400],
  429: ["rate_limited", 429],
};

export function config(env) {
  return {
    key: (env.DEEPSEEK_API_KEY || "").trim(),
    base: (env.DEEPSEEK_BASE_URL || "https://api.deepseek.com").replace(/\/+$/, ""),
    model: env.DEEPSEEK_MODEL || "deepseek-flash",
    pro: env.DEEPSEEK_MODEL_PRO || "deepseek-v4-pro",
    password: env.SITE_PASSWORD || "",
  };
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

function sameText(a, b) {
  if (a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

function authed(request, c) {
  if (!c.password) return true;
  return sameText(request.headers.get("x-site-password") || "", c.password);
}

function cleanMessage(m) {
  const out = { role: m.role, content: typeof m.content === "string" ? m.content : "" };
  if (m.role === "assistant" && Array.isArray(m.tool_calls)) out.tool_calls = m.tool_calls;
  if (m.role === "tool") out.tool_call_id = String(m.tool_call_id || "");
  return out;
}

export function handleConfig(request, env) {
  const c = config(env);
  return json({ hasKey: !!c.key, needPassword: !!c.password, authed: authed(request, c), model: c.model, pro: c.pro, vision: false });
}

export async function handleChat(request, env) {
  const c = config(env);
  if (!authed(request, c)) return json({ error: "locked", message: "需要访问密码" }, 401);
  if (!c.key) return json({ error: "no_key", message: "服务器还没有配置 DEEPSEEK_API_KEY" }, 503);

  const raw = await request.text();
  if (raw.length > 800000) return json({ error: "too_large", message: "请求太大" }, 413);
  let body;
  try { body = JSON.parse(raw); } catch (e) { return json({ error: "bad_request", message: "请求不是 JSON" }, 400); }
  const messages = Array.isArray(body.messages) ? body.messages.filter(m => m && ROLES.has(m.role)).map(cleanMessage) : [];
  if (!messages.length) return json({ error: "bad_request", message: "messages 为空" }, 400);

  const payload = {
    model: body.tier === "complex" ? c.pro : c.model,
    messages,
    stream: true,
    max_tokens: Math.min(Number(body.max_tokens) || 8192, 16384),
  };
  if (Array.isArray(body.tools) && body.tools.length) payload.tools = body.tools.slice(0, 8);
  if (body.json) payload.response_format = { type: "json_object" };

  let upstream;
  try {
    upstream = await fetch(c.base + "/chat/completions", {
      method: "POST",
      headers: { authorization: "Bearer " + c.key, "content-type": "application/json" },
      body: JSON.stringify(payload),
      signal: request.signal,
    });
  } catch (e) {
    return json({ error: "upstream", message: "连不上 DeepSeek：" + ((e && e.message) || e) }, 502);
  }
  if (!upstream.ok) {
    const text = (await upstream.text()).slice(0, 800);
    const [code, status] = ERRORS[upstream.status] || ["upstream", 502];
    return json({ error: code, status: upstream.status, message: text }, status);
  }
  return new Response(upstream.body, {
    headers: { "content-type": "text/event-stream; charset=utf-8", "cache-control": "no-cache, no-transform", "x-accel-buffering": "no" },
  });
}
