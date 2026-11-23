@rem AI created the file
@rem Author: Copilot
@rem Created: 2026-11-22
@rem Last Changes:
@rem 2026-11-22 21:36 CET: Copilot: Added Windows GUI launcher

@echo off
uv run --project "%~dp0" myfem
if errorlevel 1 pause
