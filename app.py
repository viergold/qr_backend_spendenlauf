from flask import Flask, request, jsonify, render_template, make_response, redirect, url_for
import datetime
import time
import threading
import db
import uuid

app = Flask(__name__)

app.secret_key = "secret"

# Ensure database schema exists before handling requests
db.db_in()

# Scan-Trigger für 2 Sekunden aktiv
scan_trigger = {i: False for i in range(1, 7)}
scan_timestamp = {i: 0 for i in range(1, 7)}
SCAN_DURATION = 2  # Sekunden


# Statusliste für IDs 1–6
status = {i: False for i in range(1, 7)}
last_ping = {i: 0 for i in range(1, 7)}

PING_TIMEOUT = 1.3  # Scanner pingt alle 100 ms

# Speichert Zielseiten pro Client (jetzt als NAME)
client_targets = {}


race_state = {
    "running": False,
    "pre_run": False,
    "test_run":False
}


# -----------------------------
# ROUTES
# -----------------------------

@app.route("/scanner")
def scanner():
    return render_template("scanner.html")

@app.route("/get_id")
def get_id():
    client_id = request.cookies.get("client_id")

    if not client_id:
        client_id = uuid.uuid4().hex[:8]

    # Client automatisch registrieren
    if client_id not in client_targets:
        client_targets[client_id] = None

    response = make_response(render_template("index.html", client_id=client_id))
    response.set_cookie("client_id", client_id, max_age=60 * 60 * 24 * 365)

    return response



@app.route("/")
def index():
    return redirect("/get_id")


@app.route("/set_status", methods=["GET"])
def set_status():
    return render_template("set_status.html")


@app.route("/api/race_status", methods=["GET"])
def get_race_status():
    return jsonify(race_state)

@app.route("/api/race_status", methods=["POST"])
def set_race_status():
    data = request.json

    # Nur bekannte Keys aktualisieren
    for key in race_state:
        if key in data:
            race_state[key] = bool(data[key])

    return jsonify({"message": "updated", "new_state": race_state})

@app.route("/api/next_page/<client_id>")
def next_page(client_id):
    # Falls Client unbekannt → automatisch registrieren
    if client_id not in client_targets:
        client_targets[client_id] = None

    return jsonify({"next_page": client_targets[client_id]})


@app.route("/admin", methods=["GET", "POST"])
def admin():
    global client_targets

    if request.method == "POST":
        target_page = request.form.get("target_page")  # jetzt STRING
        target_client = request.form.get("client_id")

        if target_page:
            if target_client == "ALL":
                for cid in client_targets:
                    client_targets[cid] = target_page
            else:
                if target_client not in client_targets:
                    client_targets[target_client] = None

                client_targets[target_client] = target_page

    return render_template("admin.html", clients=client_targets)


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/get_best_15_classes/")
def api_best_15_classes():
    min_avg_runden = request.args.get("min_avg_runden", type=float)
    limit = request.args.get("limit", default=15, type=int)

    klasse = request.args.getlist("klasse") or None

    data = db.get_best_15_classes(limit=limit, min_avg_runden=min_avg_runden, klasse=klasse)

    return jsonify({
        "status": "ok",
        "best_15_classes": [{"klasse": k, "avg_runden": avg} for k, avg in data]
    })


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

    data = db.get_fastest(
        limit=limit,
        klasse=klasse,
        min_runden=min_runden,
        min_beste_zeit=min_beste_zeit,
        max_beste_zeit=max_beste_zeit
    )

    return jsonify({
        "status": "ok",
        "fastest": [
            {
                "id": id,
                "name": name,
                "klasse": klasse,
                "runden": runden,
                "beste_zeit": beste_zeit
            }
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
            {
                "id": id,
                "name": name,
                "klasse": klasse,
                "runden": runden
            }
            for id, name, klasse, runden, _, _ in top15
        ]
    })
@app.route("/status_api")
def status_api():
    return jsonify(status)


@app.route("/qr", methods=["POST"])
def receive_qr():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"status": "error"}), 400

    qr_text = data.get("qr")
    scanner_id = data.get("scanner")  # <-- NEU

    print("QR erkannt:", qr_text)
    print("Zeit:", datetime.datetime.now())
    # --- Deine bestehende Logik ---
    if db.check_id(qr_text):
        # --- SCAN-TRIGGER aktivieren ---
        if scanner_id in scan_trigger:
            scan_trigger[scanner_id] = True
            scan_timestamp[scanner_id] = time.time()
            print(f"📸 Scanner {scanner_id} hat gescannt!")

        print("👤 Benutzer:", db.get_name_klasse(qr_text))
        db.runde_hinzufuegen(qr_text)
    else:
        print("⚠️ Unbekannter QR")

    return jsonify({"status": "ok", "qr": qr_text})
@app.route("/ping")
def ping():
    try:
        client_id = int(request.args.get("id"))
    except:
        return jsonify({"status": "invalid id"}), 400

    if client_id not in status:
        return jsonify({"status": "invalid id"}), 400

    last_ping[client_id] = time.time()
    status[client_id] = True

    return jsonify({"status": "ok"})

@app.route("/api/scan_status/<int:scanner_id>")
def api_scan_status_single(scanner_id):
    if scanner_id not in scan_trigger:
        return jsonify({"status": "invalid id"}), 400

    return jsonify({"scanner": scan_trigger[scanner_id]})


# -----------------------------
# Hintergrund-Threads
# -----------------------------

def monitor_scanners():
    while True:
        now = time.time()
        for scanner_id in status:
            if now - last_ping[scanner_id] > PING_TIMEOUT:
                status[scanner_id] = False
        time.sleep(0.1)


def set_status_open(station_id):
    print(f"✅ Station {station_id} OPEN")


def check_status():
    while True:
        for i in range(1, 7):
            if status[i]:
                set_status_open(i)
        time.sleep(0.5)

def monitor_scan_trigger():
    while True:
        now = time.time()
        for scanner_id in scan_trigger:
            if scan_trigger[scanner_id] and (now - scan_timestamp[scanner_id] > SCAN_DURATION):
                scan_trigger[scanner_id] = False
        time.sleep(0.1)

threading.Thread(target=monitor_scan_trigger, daemon=True).start()
threading.Thread(target=monitor_scanners, daemon=True).start()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        ssl_context="adhoc",
    )