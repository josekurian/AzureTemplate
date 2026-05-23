#!/usr/bin/env bash
set -euo pipefail
curl -s http://127.0.0.1:8000/health | grep -q "ok" || { echo "API is not running"; exit 1; }
curl -s -X POST http://127.0.0.1:8000/concierge/chat \
  -H 'content-type: application/json' \
  -d '{"message":"Do you have a vegan tasting menu?"}' | grep -q "answer"
echo "Smoke test passed"
