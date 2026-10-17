@echo off
title ReadyCheck Server - AZINHACK 26
cd /d " %~dp0\
echo Starting ReadyCheck Server on http://127.0.0.1:8000 ...
.\tinyfish\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
pause
