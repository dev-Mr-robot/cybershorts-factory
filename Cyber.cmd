@echo off
where python >nul 2>nul
if errorlevel 1 goto py
python "%~dp0bootstrap.py" %*
exit /b %errorlevel%
:py
py -3 "%~dp0bootstrap.py" %*
exit /b %errorlevel%
