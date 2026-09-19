@echo off
chcp 65001 >nul
title Claude Toolbox - Claude Desktop
rem ============================================================
rem  Claude Desktop toolbox (ASCII-only file content)
rem  [1] localize  [2] DeepSeek gateway  [3] relay  [4] all
rem  [5] status    [6] restore official  [7] remove DeepSeek
rem ============================================================
setlocal
set "PYEXE="
where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE where py >nul 2>nul && set "PYEXE=py"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYEXE if exist "C:\Users\Lime\.workbuddy\binaries\python\versions\3.13.12\python.exe" set "PYEXE=C:\Users\Lime\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not defined PYEXE (
  echo [ERROR] Python 3 not found. Install Python 3.10+ and make sure "python" is on PATH.
  pause
  exit /b 1
)
"%PYEXE%" "%~dp0scripts\claude-toolbox.py"
endlocal
