from flask import Flask, jsonify, request, abort
import requests
from urllib.parse import urlparse, parse_qs
import threading
import time
import os
from colorama import Fore, init, Style
import logging
import flask.cli

flask.cli.show_server_banner = lambda *args: None
log = logging.getLogger('werkzeug')
log.disabled = True
log.setLevel(logging.ERROR)

init(autoreset=True)

app = Flask(__name__)

VERIFY_URL = "http://nighthub.site/auth/verify?step=done"
API_KEY = "LonelyHubApiKeyByLongHip12"

keys = []
keys_lock = threading.Lock()

generated = 0
target = 50

def get_key():
    try:
        r = requests.get(VERIFY_URL, allow_redirects=True, timeout=10)
        parsed = urlparse(r.url)
        params = parse_qs(parsed.query)
        key = params.get("key")
        if key:
            return key[0]
    except Exception as e:
        print(Fore.RED + "[ERROR]" + Style.RESET_ALL + f" {e}")
    return None

def key_worker():
    global generated
    while True:
        if generated >= target:
            break
        key = get_key()
        if key:
            expire = time.time() + (400 * 60)
            with keys_lock:
                if key not in [k["key"] for k in keys]:
                    keys.append({
                        "key": key,
                        "expire": expire
                    })
                    generated += 1
                    print(key)
        else:
            print(Fore.YELLOW + "[WARN]" + Style.RESET_ALL + " Key Error")

def generate_keys():
    global generated
    print(Fore.CYAN + "[INFO]" + Style.RESET_ALL + " Generating Key...")
    print(f"{Fore.GREEN}===================KEY==================")
    while True:
        generated = 0
        threads = []
        for _ in range(10):
            t = threading.Thread(target=key_worker)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        print(Fore.GREEN + "=======================================")
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} Posted All Key To Api")
        print(Fore.CYAN + "[INFO]" + Style.RESET_ALL + " Wait 5 Minutes\n")
        time.sleep(300)

def remove_expired():
    while True:
        now = time.time()
        with keys_lock:
            before = len(keys)
            keys[:] = [k for k in keys if k["expire"] > now]
            after = len(keys)
        if before != after:
            print(Fore.CYAN + f"[INFO]" + Style.RESET_ALL + f" removed {before-after} expired keys")
        time.sleep(60)

def check_api():
    client_key = request.headers.get("x-api-key")
    if client_key != API_KEY:
        abort(403)

@app.route("/")
def home():
    return {
        "status": "running",
        "keys": len(keys)
    }

@app.route("/keys")
def api_keys():
    check_api()
    with keys_lock:
        return jsonify([k["key"] for k in keys])

def start_workers():
    threading.Thread(target=generate_keys, daemon=True).start()
    threading.Thread(target=remove_expired, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(Fore.CYAN + f"[INFO]" + Style.RESET_ALL + f" server port opened at: {port}")
    start_workers()
    app.run(host="0.0.0.0", port=port)