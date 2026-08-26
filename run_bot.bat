@echo off
title Universal Super Bot - 24/7 Runner
echo Bot ishga tushmoqda...
:loop
"C:\Users\Husanboy\AppData\Local\Programs\Python\Python311\python.exe" "C:\Users\Husanboy\.gemini\antigravity\scratch\universal_super_bot\main.py"
echo Bot to'xtadi! 5 soniyadan so'ng qayta ishga tushirilmoqda...
timeout /t 5
goto loop
