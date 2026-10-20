#!/usr/bin/env node
// 本机运行：node server.mjs            → http://127.0.0.1:8787
//           node server.mjs --lan      → 同一 Wi-Fi 下的手机也能访问（建议同时设置 SITE_PASSWORD）
//           node server.mjs --port=9000
// DeepSeek key 读取顺序：环境变量 DEEPSEEK_API_KEY → .dev.vars → ~/.deepseek_key
import http from "node:http";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { handleChat, handleConfig } from "./lib/proxy.js";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PUB = path.join(ROOT, "public");
const args = process.argv.slice(2);
const LAN = args.includes("--lan");
const PORT = Number((args.find(a => a.startsWith("--port=")) || "").split("=")[1]) || Number(process.env.PORT) || 8787;

function loadEnv() {
  const env = { ...process.env };
  const devVars = path.join(ROOT, ".dev.vars");
  if (fs.existsSync(devVars)) {
    for (const line of fs.readFileSync(devVars, "utf8").split("\n")) {
      const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*"?(.*?)"?\s*$/);
      if (m && !env[m[1]]) env[m[1]] = m[2];
    }
  }
  const keyFile = path.join(os.homedir(), ".deepseek_key");
  if (!env.DEEPSEEK_API_KEY && fs.existsSync(keyFile)) env.DEEPSEEK_API_KEY = fs.readFileSync(keyFile, "utf8").trim();
  return env;
}
const ENV = loadEnv();

const MIME = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8", ".wasm": "application/wasm",
  ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".txt": "text/plain; charset=utf-8", ".map": "application/json",
};

async function api(req, res, url) {
  const ctl = new AbortController();
  res.on("close", () => { if (!res.writableEnded) ctl.abort(); });
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const headers = {};
  for (const k of ["content-type", "x-site-password"]) if (req.headers[k]) headers[k] = String(req.headers[k]);
  const request = new Request(url, {
    method: req.method, headers, signal: ctl.signal,
    body: req.method === "GET" || req.method === "HEAD" ? undefined : Buffer.concat(chunks),
  });
  let response;
  if (url.pathname === "/api/chat" && req.method === "POST") response = await handleChat(request, ENV);
  else if (url.pathname === "/api/config" && req.method === "GET") response = handleConfig(request, ENV);
  else response = new Response("not found", { status: 404 });
  res.writeHead(response.status, Object.fromEntries(response.headers));
  if (response.body) {
    try { for await (const chunk of response.body) res.write(chunk); } catch (e) { /* 浏览器断开了 */ }
  }
  res.end();
}

function serveStatic(req, res, url) {
  let rel = decodeURIComponent(url.pathname);
  if (rel.endsWith("/")) rel += "index.html";
  const file = path.normalize(path.join(PUB, rel));
  if (!file.startsWith(PUB + path.sep)) { res.writeHead(403).end(); return; }
  fs.stat(file, (err, st) => {
    if (err || !st.isFile()) { res.writeHead(404, { "content-type": "text/plain; charset=utf-8" }).end("not found"); return; }
    const longCache = rel.startsWith("/pyodide/") || rel.startsWith("/vendor/");
    res.writeHead(200, {
      "content-type": MIME[path.extname(file)] || "application/octet-stream",
      "content-length": st.size,
      "cache-control": longCache ? "public, max-age=604800" : "no-cache",
    });
    if (req.method === "HEAD") { res.end(); return; }
    fs.createReadStream(file).pipe(res);
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);
  try {
    if (url.pathname.startsWith("/api/")) await api(req, res, url);
    else serveStatic(req, res, url);
  } catch (e) {
    console.error(e);
    if (!res.headersSent) res.writeHead(500, { "content-type": "text/plain; charset=utf-8" });
    res.end("服务器出错：" + ((e && e.message) || e));
  }
});

server.listen(PORT, LAN ? "0.0.0.0" : "127.0.0.1", () => {
  console.log(`题眼算法陪练已启动：http://127.0.0.1:${PORT}`);
  if (LAN) {
    for (const list of Object.values(os.networkInterfaces())) for (const a of list || []) {
      if (a.family === "IPv4" && !a.internal) console.log(`  局域网访问：http://${a.address}:${PORT}`);
    }
    if (!ENV.SITE_PASSWORD) console.log("  提醒：局域网模式下没有设置 SITE_PASSWORD，同一网络的人都能用你的 DeepSeek 额度。");
  }
  console.log(ENV.DEEPSEEK_API_KEY ? `  DeepSeek：已配置（${ENV.DEEPSEEK_MODEL || "deepseek-flash"}）` : "  DeepSeek：还没有 key —— 把 key 存到 ~/.deepseek_key 或 .dev.vars 后重启；不配也能刷题判题，只是没有 AI 老师。");
});
