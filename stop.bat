@echo off
REM Stop opencode-cli-mcp fleet ports
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
if errorlevel 1 pause

