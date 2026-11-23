#!/usr/bin/env sh
# AI created the file
# Author: Copilot
# Created: 2026-11-22
# Last Changes:
# 2026-11-22 21:36 CET: Copilot: Added Linux and WSL GUI launcher

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
exec uv run --project "$SCRIPT_DIR" myfem "$@"
