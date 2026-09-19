@echo off
chcp 65001 >nul
title DeepSeek 3P Relay for Claude Desktop
rem Starts the local relay that merges DeepSeek's two URL prefixes
rem   /v1/models -> served locally (model discovery);  /v1/* -> api.deepseek.com/anthropic/v1/*
setlocal
set "PYEXE="
where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE where py >nul 2>nul && set "PYEXE=py"
if not defined PYEXE if exist "C:\Users\Lime\.workbuddy\binaries\python\versions\3.13.12\python.exe" set "PYEXE=C:\Users\Lime\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not defined PYEXE (
  echo [ERROR] Python 3 not found on PATH.
  pause
  exit /b 1
)
"%PYEXE%" "%~dp0scripts\deepseek-3p-proxy.py"
pause
endlocal
