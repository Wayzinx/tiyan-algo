# 题眼算法陪练

AI 老师陪你刷 Python 算法题：13 个题型教程、47 道高频题（浏览器里用 Pyodide 真实判题）、AI 批改 / 找反例 / 思路→代码 / 出变体、动画讲解配语音、间隔复习。AI 由 DeepSeek 驱动，可以装成手机 / 电脑上的 App，离线也能刷题判题。另有两个按里程碑实现的项目实战（可部署的 Agent 服务、Agent 评测 Runner）。

## 两种用法

### 1. 网页版（GitHub Pages，推荐）

打开网站后，点右上角「填写 DeepSeek key」，填入你在 platform.deepseek.com 创建的 key。
key 只存在当前浏览器里，由浏览器直接发给 DeepSeek，不经过任何其他服务器；别人打开网站需要填他们自己的 key。

**安装成 App**：电脑 Chrome / Edge 地址栏右侧点「安装」；iPhone 用 Safari 打开 →「分享」→「添加到主屏幕」；安卓 Chrome 菜单 →「安装应用」。
装好后题库、教程、判题都能离线用，只有 AI 老师需要联网。

更新网站：改完代码运行 `python3 build.py`，再运行 `./publish.sh`。

### 2. 本机运行（带后端，key 存在本机文件里）

```bash
printf '%s' 'sk-你的key' > ~/.deepseek_key && chmod 600 ~/.deepseek_key   # 在自己的终端里运行
cd ~/tiyan-algo && node server.mjs                                         # 打开 http://127.0.0.1:8787
```

同一 Wi-Fi 的手机访问：在 `.dev.vars` 里设置 `SITE_PASSWORD=...`，再运行 `node server.mjs --lan`。
模型可在 `.dev.vars` 里改：`DEEPSEEK_MODEL`（对话，默认 deepseek-flash）、`DEEPSEEK_MODEL_PRO`（出题和动画，默认 deepseek-v4-pro）。

`functions/` 是给 Cloudflare Pages 准备的同一套后端，以后想换到 Cloudflare 可以直接用（`npx wrangler pages deploy`）。

## 目录

- `public/`：网站本体（`index.html`、`sw.js` 由 `build.py` 生成；`pyodide/` 是浏览器里的 Python；`vendor/` 是前端库；`manifest.webmanifest` 和 `icons/` 用于安装成 App）
- `functions/api/`：Cloudflare 上的接口；`lib/proxy.js` 是本机和 Cloudflare 共用的转发逻辑
- `server.mjs`：本机服务器
- `src/`：前端源码
- `data/`：内容和校验脚本
  - 算法题库：`problems.py` → `gen.py` → `problems.json`
  - AI 知识（5 门课）：`k2/*.py` → `gen_knowledge2.py` → `knowledge.json`
  - 手写实战：`labs/*.py` → `gen_labs.py`（需要带 numpy 的 Python 3.12）→ `labs.json`
  - Python 刷题语法：`python_features.py` → `gen_python.py` → `python.json`
  - 算法题独立校验：`oracles.py`（每题的暴力解 + 随机小输入 + 性能用的大输入），`gen.py` 会交叉验证参考解
  - 设计编码：`sd/*.py`（12 道积木题 + 10 道设计题；`EXTRAS` 给每道设计题配 10 问压力追问 / 指标口径 / 技术选型五句；`toolbox.py` 是机制工具箱）→ `gen_sd.py` → `sd.json`；对应的编码题在 `labs/sd_*.py`
  - 项目实战：`capstones/<id>/meta.py`（里程碑说明）、`skeleton/`（公开的项目骨架，打包成 `public/capstones/<id>.zip`）、`reference/`（参考实现，只在本机，不提交）→ `gen_capstones.py` → `capstones.json`

改了 `src/` 或 `data/problems.json` 之后运行 `python3 build.py` 重新生成页面。

进度存在浏览器里：换浏览器或设备前，在「复习」页导出，再到新地方导入。
