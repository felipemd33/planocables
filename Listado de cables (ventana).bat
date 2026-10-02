@echo off
rem Ventana clasica. Tambien se pueden arrastrar planos PDF encima de este archivo.
cd /d "%~dp0"
start "" pythonw "%~dp0programa\app.py" %*
