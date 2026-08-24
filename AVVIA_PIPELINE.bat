@echo off
title Pipeline OCR TCG
cd /d "%~dp0"
python run_pipeline.py
echo.
echo Operazione completata! Premi un tasto per chiudere...
pause > nul