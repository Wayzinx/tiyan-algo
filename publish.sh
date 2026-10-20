#!/bin/sh
# 发布到 GitHub Pages：重新生成页面 → 提交源码到 main → 把 public/ 推到 gh-pages 分支
set -e
cd "$(dirname "$0")"
python3 build.py
git add -A
git commit -qm "${1:-更新 $(date "+%Y-%m-%d %H:%M")}" || true
git push -q origin main
git subtree split --prefix public -b gh-pages-build >/dev/null
git push -fq origin gh-pages-build:gh-pages
git branch -D gh-pages-build >/dev/null
echo "已发布，1–2 分钟后生效。"
