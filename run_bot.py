import sys
import subprocess
import time
import os

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

print("Universal Super Bot 24/7 Auto-Restart Daemon Ishga Tushmoqda...")

python_exe = sys.executable
main_script = os.path.join(os.path.dirname(__file__), "main.py")

while True:
    try:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Bot ishga tushirildi...")
        proc = subprocess.Popen([python_exe, main_script])
        proc.wait()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Bot to'xtadi (exit code: {proc.returncode}). 2 soniyadan so'ng qayta ishga tushadi...")
    except Exception as e:
        print(f"Daemon Error: {e}")
    time.sleep(2)
