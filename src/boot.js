// ---------- 启动 ----------
(function boot() {
  Store.init();
  updateChips();
  window.addEventListener("hashchange", render);
  render();
  Py.start();
  AI.init();
  Buddy.init();
  // 可安装的网页应用：缓存页面、前端库和 Python 运行环境，离线也能刷题判题
  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1")) {
    navigator.serviceWorker.register("sw.js").catch(() => { /* 不支持就算了 */ });
  }
})();
