#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_DIR"

# Brief network wait on cold boot; skip quickly if already online.
for _ in {1..6}; do
  if ping -c 1 -t 1 1.1.1.1 >/dev/null 2>&1 || ping -c 1 -t 1 8.8.8.8 >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

source venv/bin/activate
exec python3 telemetry_daemon.py
