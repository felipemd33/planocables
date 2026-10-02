@echo off
rem Abre la interfaz web del listado de cables en el navegador.
cd /d "%~dp0"
start "" pythonw "%~dp0programa\web.py"
