import time
from flask import Flask, jsonify, request
import requests
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

REMOTE_SERVER = "https://localhost:5000"

# ==========================================================
# Globale HTTP-Session & ThreadPool
# ==========================================================

session = requests.Session()
session.verify = False  # falls gewollt
REQUEST_TIMEOUT = 1

executor = ThreadPoolExecutor(max_workers=16)

# ==========================================================
# STATUS API (ultraschnell, wie scan_lock)
# ==========================================================

status = {i: False for i in range(1, 7)}
status_last_update = 0.0
STATUS_CACHE_MAX_AGE = 1.0
status_lock = Lock()


def update_status_async():
    """Holt Status vom Remote-Server im Hintergrund."""
    global status_last_update
    try:
        r = session.get(f"{REMOTE_SERVER}/status_api", timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            now = time.time()
            with status_lock:
                for i in range(1, 7):
                    if str(i) in data:
                        status[i] = data[str(i)]
                status_last_update = now
    except Exception:
        # Remote down → Cache bleibt gültig
        pass


@app.route("/status_api", methods=["GET"])
def status_api():
    # 1. Sofort Antwort aus Cache
    with status_lock:
        response = status.copy()
        age = time.time() - status_last_update

    # 2. Wenn Cache alt → Hintergrund-Update starten
    if age > STATUS_CACHE_MAX_AGE:
        executor.submit(update_status_async)

    return jsonify(response)


# ==========================================================
# RACE STATUS
# ==========================================================

status_race_json = {
    "running": False,
    "pre_run": False,
    "test_run": False
}

race_lock = Lock()

local_dirty = False
awaiting_remote_confirm = False


@app.route("/api/race_status", methods=["GET"])
def race_status_get():
    with race_lock:
        return jsonify(status_race_json)


def forward_post(data):
    global local_dirty, awaiting_remote_confirm
    try:
        r = session.post(
            f"{REMOTE_SERVER}/api/race_status",
            json=data,
            timeout=REQUEST_TIMEOUT
        )
        if r.status_code == 200:
            with race_lock:
                local_dirty = False
                awaiting_remote_confirm = False
    except Exception:
        # Forwarding fehlgeschlagen → lokaler Zustand bleibt
        pass


@app.route("/api/race_status", methods=["POST"])
def race_status_post():
    global local_dirty, awaiting_remote_confirm
    data = request.json or {}

    with race_lock:
        for key in status_race_json:
            if key in data:
                status_race_json[key] = bool(data[key])

        local_dirty = True
        awaiting_remote_confirm = True

    executor.submit(forward_post, data)

    return jsonify({"ok": True})


def polling_thread():
    global status_race_json, local_dirty, awaiting_remote_confirm
    while True:
        try:
            r = session.get(
                f"{REMOTE_SERVER}/api/race_status",
                timeout=REQUEST_TIMEOUT
            )
            if r.status_code == 200:
                remote_data = r.json()
                with race_lock:
                    if not local_dirty and not awaiting_remote_confirm:
                        # nur Felder übernehmen, die wir kennen
                        for key in status_race_json:
                            if key in remote_data:
                                status_race_json[key] = bool(remote_data[key])
        except Exception:
            # Remote Server nicht erreichbar
            pass

        time.sleep(0.25)  # schnelleres Polling, aber noch moderat


# ==========================================================
# SCAN LOCK PROXY (ultraschnell)
# ==========================================================

scan_lock_cache = {i: False for i in range(1, 7)}
scan_lock_timestamp = {i: 0.0 for i in range(1, 7)}
SCAN_CACHE_MAX_AGE = 1.0
scan_lock_lock = Lock()


def update_scan_lock_async(scanner_id):
    """Holt Wert vom Remote-Server im Hintergrund."""
    try:
        r = session.get(
            f"{REMOTE_SERVER}/api/scan_lock/{scanner_id}",
            timeout=REQUEST_TIMEOUT
        )
        if r.status_code == 200:
            data = r.json()
            value = data.get("locked", False)
            now = time.time()
            with scan_lock_lock:
                scan_lock_cache[scanner_id] = value
                scan_lock_timestamp[scanner_id] = now
    except Exception:
        pass


@app.route("/api/scan_lock/<int:scanner_id>", methods=["GET"])
def scan_lock_get(scanner_id):
    # 1. Sofort Antwort aus Cache
    with scan_lock_lock:
        value = scan_lock_cache.get(scanner_id, False)
        age = time.time() - scan_lock_timestamp.get(scanner_id, 0.0)

    # 2. Wenn Cache alt → Hintergrund-Update starten
    if age > SCAN_CACHE_MAX_AGE:
        executor.submit(update_scan_lock_async, scanner_id)

    return jsonify({"locked": value})


@app.route("/api/scan_lock/<int:scanner_id>", methods=["POST"])
def scan_lock_post(scanner_id):
    payload = request.get_json(silent=True) or {}
    value = bool(payload.get("locked", False))

    # 1. Cache sofort aktualisieren
    now = time.time()
    with scan_lock_lock:
        scan_lock_cache[scanner_id] = value
        scan_lock_timestamp[scanner_id] = now

    # 2. Remote im Hintergrund aktualisieren
    def send_post():
        try:
            session.post(
                f"{REMOTE_SERVER}/api/scan_lock/{scanner_id}",
                json={"locked": value},
                timeout=REQUEST_TIMEOUT
            )
        except Exception:
            pass

    executor.submit(send_post)

    return jsonify({"locked": value})


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":
    Thread(target=polling_thread, daemon=True).start()
    # Für echte Performance: lieber mit Gunicorn/Uvicorn starten
    app.run(host="0.0.0.0", port=5003, threaded=True)