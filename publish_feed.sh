#!/bin/zsh
# Publish local work (new squares, state, feed, dashboard) to GitHub. This folder IS the repo
# github.com/Vimm-Activewear-Br/meta-feed; the hourly refresh runs in GitHub Actions
# (.github/workflows/refresh.yml), so always pull first. Auth = token in the macOS Keychain.
set -e
cd "$(dirname "$0")"
git add -A
git diff --cached --quiet || git commit -q -m "Atualização local do feed do Meta ($(date '+%Y-%m-%d %H:%M'))"
GIT_TERMINAL_PROMPT=0 git pull -q --rebase -X theirs origin main
if [ -z "$(git log origin/main..HEAD --oneline)" ]; then echo "feed unchanged, nothing to publish"; exit 0; fi
GIT_TERMINAL_PROMPT=0 git push -q origin main
echo "published $(($(wc -l < vimm-meta-supplementary-feed.csv) - 2)) rows"
