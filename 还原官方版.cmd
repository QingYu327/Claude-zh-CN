@echo off
chcp 65001 >nul
title Restore official Claude Desktop
rem Reinstalls the pristine package from the official installer cache
rem (the patched package has a higher version, so ForceUpdateFromAnyVersion is required)
setlocal
set "BASE=%LOCALAPPDATA%\ClaudeInstaller\cache\Claude-win-x64.msix"
if not exist "%BASE%" (
  echo [ERROR] base installer cache not found:
  echo         %BASE%
  pause
  exit /b 1
)
echo ============================================================
echo   Restore OFFICIAL Claude Desktop (English, unpatched)
echo ============================================================
powershell -NoProfile -Command "Add-AppxPackage -Path '%BASE%' -ForceUpdateFromAnyVersion -ForceApplicationShutdown -ErrorAction Stop; Write-Output RESTORE-OK"
echo ------------------------------------------------------------
echo  Exit code: %ERRORLEVEL%
echo  After restore the Chinese patch is gone (rerun the toolbox [1] to reapply).
echo ------------------------------------------------------------
pause
endlocal
