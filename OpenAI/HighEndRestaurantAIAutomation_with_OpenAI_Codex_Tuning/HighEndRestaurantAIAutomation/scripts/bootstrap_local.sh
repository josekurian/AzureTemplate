#!/usr/bin/env bash
set -euo pipefail
TARGET="/Users/josekurian/AzureTemplate/OpenAI"
PROJECT="HighEndRestaurantAIAutomation"
mkdir -p "$TARGET"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cp -R "$ROOT_DIR" "$TARGET/$PROJECT"
echo "Project copied to $TARGET/$PROJECT"
