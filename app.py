from flask import Flask, request, jsonify, render_template, make_response, redirect
import datetime
import time
import threading
import db
import uuid
import os
import logging
from threading import Lock

# -----------------------------
# Logging konfigurieren
# -----------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# -----------------------------
# Flask App
# -----------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# -----------------------------
# Locks für Thread-Safety
# -----------------------------
lock = Lock()

# -----------------------------
# Datenstrukturen
# -----------------------------
# Scan Trigger
scan_trigger = {i: False for i in range(1, 7)}
scan_timestamp = {i: 0 for i in range(1, 7)}
SCAN_DURATION = 2  # Sekunden

# Status und Pings
status = {i: False for i in range(1, 7)}
last_ping = {i: 0 for i in range(1, 7)}
PING_TIMEOUT = 1.3

# Client Targets
client_targets = {}

# Race-State
race_state = {
    "running": False,
    "pre_run": False,
    "test_run": False
}

# -----------------------------
# Datenbank Init
# -----------------------------
db.db_in()

# -----------------------------
# Routes
# -----------------------------

@app.route("/")
def index():
    return redirect("/get_id")


@app.route("/get_id")
def get_id():
    client_id = request.cookies.get("client_id")
    if not client_id:
        client_id = uuid.uuid4().hex[:8]

    with lock:
        if client_id not in client_targets:
            client_targets[client_id] = None

    response = make_response(render_template("index.html", client_id=client_id))
    response.set_cookie("client_id", client_id, max_age=60*60*24*365)
    return response


@app.route("/scanner")
def scanner():
    return render_template("scanner.html")


@app.route("/set_status")
def set_status_page():
    return render_template("set_status.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# -----------------------------
# Admin
# -----------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    global client_targets
    if request.method == "POST":
        target_page = request.form.get("target_page")
        target_client = request.form.get("client_id")
        with lock:
            if target_page:
                if target_client == "ALL":
                    for cid in client_targets:
                        client_targets[cid] = target_page
                else:
                    client_targets[target_client] = target_page
    with lock:
        clients_copy = client_targets.copy()
    return render_template("admin.html", clients=clients_copy)


# -----------------------------
# Race API
# -----------------------------
@app.route("/api/race_status", methods=["GET"])
def get_race_status():
    with lock:
        state_copy = race_state.copy()
    return jsonify(state_copy)

@app.route("/api/race_status", methods=["POST"])
def set_race_status():
    data = request.json
    with lock:
        for key in race_state:
            if key in data:
                race_state[key] = bool(data[key])
        new_state = race_state.copy()
    return jsonify({"message": "updated", "new_state": new_state})


# -----------------------------
# Client Next Page API
# -----------------------------
@app.route("/api/next_page/<client_id>")
def next_page(client_id):
    with lock:
        if client_id not in client_targets:
            client_targets[client_id] = None
        next_page = client_targets[client_id]
    return jsonify({"next_page": next_page})


# -----------------------------
# DB APIs
# -----------------------------
@app.route("/api/get_best_15_classes/")
def api_best_15_classes():
    min_avg_runden = request.args.get("min_avg_runden", type=float)
    limit = request.args.get("limit", default=15, type=int)
    klasse = request.args.getlist("klasse") or None
    data = db.get_best_15_classes(limit=limit, min_avg_runden=min_avg_runden, klasse=klasse)
    return jsonify({"status": "ok", "best_15_classes":[{"klasse": k, "avg_runden": avg} for k, avg in data]})


@app.route("/api/get_total_kilometer/")
def api_get_total_kilometer():
    klasse = request.args.getlist("klasse") or None
    total = db.get_total_kilometer(0.7, klasse=klasse)
    return jsonify({"status": "ok", "total_kilometer": total})


@app.route("/api/get_total_runden/")
def api_get_total_runden():
    klasse = request.args.getlist("klasse") or None
    total = db.get_total_runden(klasse=klasse)
    return jsonify({"status": "ok", "total_runden": total})


@app.route("/api/get_fastest/")
def api_get_fastest():
    klasse = request.args.getlist("klasse") or None
    min_runden = request.args.get("min_runden", type=int)
    min_beste_zeit = request.args.get("min_beste_zeit", type=float)
    max_beste_zeit = request.args.get("max_beste_zeit", type=float)
    limit = request.args.get("limit", default=15, type=int)

    data = db.get_fastest(limit=limit, klasse=klasse, min_runden=min_runden, min_beste_zeit=min_beste_zeit, max_beste_zeit=max_beste_zeit)
    return jsonify({
        "status": "ok",
        "fastest": [
            {"id": id, "name": name, "klasse": klasse, "runden": runden, "beste_zeit": beste_zeit}
            for id, name, klasse, runden, beste_zeit in data
        ]
    })


@app.route("/api/get_best_15/")
def get_best_15():
    klasse = request.args.getlist("klasse") or None
    min_runden = request.args.get("min_runden", type=int)
    limit = request.args.get("limit", default=15, type=int)
    top15 = db.get_top_15(limit=limit, klasse=klasse, min_runden=min_runden)
    return jsonify({
        "status": "ok",
        "top15": [
            {"id": id, "name": name, "klasse": klasse, "runden": runden}
            for id, name, klasse, runden, _, _ in top15
        ]
    })


# -----------------------------
# Status API
# -----------------------------
@app.route("/status_api")
def status_api():
    with lock:
        return jsonify(status.copy())


# -----------------------------
# QR Scanner
# -----------------------------
@app.route("/qr", methods=["POST"])
def receive_qr():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error"}), 400

    qr_text = data.get("qr")
    try:
        scanner_id = int(data.get("scanner"))
    except:
        scanner_id = None

    logging.info(f"QR erkannt: {qr_text} | Scanner: {scanner_id} | Zeit: {datetime.datetime.now()}")

    if db.check_id(qr_text):
        if scanner_id in scan_trigger:
            with lock:
                scan_trigger[scanner_id] = True
                scan_timestamp[scanner_id] = time.time()
            logging.info(f"📸 Scanner {scanner_id} hat gescannt!")
        logging.info(f"👤 Benutzer: {db.get_name_klasse(qr_text)}")
        db.runde_hinzufuegen(qr_text)
    else:
        logging.warning("⚠️ Unbekannter QR")

    return jsonify({"status": "ok", "qr": qr_text})


# -----------------------------
# Ping API
# -----------------------------
@app.route("/ping")
def ping():
    client_id = request.args.get("id", type=int)
    if client_id is None or client_id not in status:
        return jsonify({"status": "invalid id"}), 400
    with lock:
        last_ping[client_id] = time.time()
        status[client_id] = True
    return jsonify({"status": "ok"})


# -----------------------------
# Scan Status APIs
# -----------------------------
@app.route("/api/scan_status/<int:scanner_id>")
def api_scan_status_single(scanner_id):
    if scanner_id not in scan_trigger:
        return jsonify({"status": "invalid id"}), 400
    with lock:
        value = scan_trigger[scanner_id]
    return jsonify({"scanner": value})


@app.route("/api/scan_status_all/")
def api_scan_status_all():
    with lock:
        return jsonify({"scanner": scan_trigger.copy()})


# -----------------------------
# Hintergrund-Threads
# -----------------------------
def monitor_scanners():
    while True:
        now = time.time()
        with lock:
            for scanner_id in status:
                if now - last_ping[scanner_id] > PING_TIMEOUT:
                    status[scanner_id] = False
        time.sleep(0.1)

def monitor_scan_trigger():
    while True:
        now = time.time()
        with lock:
            for scanner_id in scan_trigger:
                if scan_trigger[scanner_id] and (now - scan_timestamp[scanner_id] > SCAN_DURATION):
                    scan_trigger[scanner_id] = False
        time.sleep(0.1)

def check_status():
    while True:
        with lock:
            for i in range(1, 7):
                if status[i]:
                    logging.info(f"✅ Station {i} OPEN")
        time.sleep(0.5)


# -----------------------------
# Threads starten
# -----------------------------
threading.Thread(target=monitor_scanners, daemon=True).start()
threading.Thread(target=monitor_scan_trigger, daemon=True).start()
threading.Thread(target=check_status, daemon=True).start()


# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, ssl_context="adhoc")
