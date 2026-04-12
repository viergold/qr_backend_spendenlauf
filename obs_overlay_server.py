from flask import Flask, jsonify, render_template
import requests

app = Flask(__name__)

REMOTE_SERVER = "https://localhost:5000"   # <- hier deine echte API-Domain eintragen


# -----------------------------------
# Overlay HTML ausliefern
# -----------------------------------
@app.route("/overlay")
def overlay():
    return render_template("obs_overlay.html")


# -----------------------------------
# API: Race Status (Proxy)
# -----------------------------------
@app.route("/api/race_status")
def race_status():
    try:
        r = requests.get(f"{REMOTE_SERVER}/api/race_status", timeout=2,verify=False)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": "Server nicht erreichbar"}), 500


# -----------------------------------
# API: Globaler Status (Proxy)
# -----------------------------------
@app.route("/api/global_status")
def global_status():
    try:
        r = requests.get(f"{REMOTE_SERVER}/status_api", timeout=2)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": "Server nicht erreichbar"}), 500


# -----------------------------------
# Flask starten (HTTP!)
# -----------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)