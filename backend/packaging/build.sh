#!/usr/bin/env bash
# Build the GhostNet app bundle: frontend → backend → PyInstaller.
# Output: backend/dist/GhostNet/   (run it: ./dist/GhostNet/GhostNet)
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "==> building dashboard"
cd "$repo/frontend"
npm run build

echo "==> packaging backend"
cd "$repo/backend"
uv sync --group packaging
uv run pyinstaller --noconfirm packaging/ghostnet.spec

echo "==> done: backend/dist/GhostNet/"
