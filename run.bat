@echo off
title Black Flame - Family Union System
echo =========================================================================
echo   BLACK FLAME - AI-POWERED FAMILY REUNIFICATION & DISASTER RESPONSE
echo   Emblem: Family Union
echo =========================================================================
cd /d "%~dp0"
if exist "..\disaster-reunify\venv\Scripts\streamlit.exe" (
    "..\disaster-reunify\venv\Scripts\streamlit.exe" run app.py
) else (
    streamlit run app.py
)
pause

