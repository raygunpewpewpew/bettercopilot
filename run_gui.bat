@echo off
setlocal
echo Starting BetterCopilot GUI...
python "%~dp0scripts\run_gui_launcher.py" %*
endlocal
exit /b %ERRORLEVEL%
