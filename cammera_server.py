from flask import Flask, Response, request, jsonify, render_template
from flask_cors import CORS
import base64
import re
import threading
import time

app = Flask(__name__, template_folder="templates")
# Für Entwicklung: alle Origins erlauben. In Produktion: genaue Origin angeben.
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# In‑Memory Speicher für die neuesten Frames pro Kamera
camera_frames = {}
camera_locks = {}

@app.route("/viewer/<camera_id>")
def viewer(camera_id):
    # Liefert eine einfache Seite, die nur den MJPEG-Stream anzeigt
    return render_template("viewer.html", camera_id=camera_id)


@app.route("/upload_frame/<camera_id>", methods=["POST", "OPTIONS"])
def upload_frame(camera_id):
    # OPTIONS wird automatisch von flask-cors behandelt, aber wir akzeptieren es hier
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    data = request.json.get("image") if request.is_json else None
    if not data:
        return jsonify({"error": "no image provided"}), 400

    # Entferne data:image/...;base64, Header falls vorhanden
    img_str = re.sub(r"^data:image/.+;base64,", "", data)
    try:
        img_bytes = base64.b64decode(img_str)
    except Exception as e:
        return jsonify({"error": "invalid base64"}), 400

    # Thread-sichere Speicherung
    if camera_id not in camera_locks:
        camera_locks[camera_id] = threading.Lock()

    with camera_locks[camera_id]:
        camera_frames[camera_id] = {
            "bytes": img_bytes,
            "ts": time.time()
        }

    return jsonify({"status": "ok"}), 200

@app.route("/api/cameras")
def list_cameras():
    # Liefert Liste der aktuell bekannten Kameras
    cams = list(camera_frames.keys())
    return jsonify(cams), 200

@app.route("/api/camera/<camera_id>")
def get_camera_image(camera_id):
    # Liefert das neueste JPEG einer Kamera
    if camera_id not in camera_frames:
        return jsonify({"error": "camera not found"}), 404
    frame = camera_frames[camera_id]["bytes"]
    return Response(frame, mimetype="image/jpeg")

@app.route("/stream/<camera_id>")
def stream_camera(camera_id):
    # MJPEG Stream: multipart/x-mixed-replace
    boundary = b"--frame\r\n"
    if camera_id not in camera_frames:
        return "Camera not found", 404

    def generate():
        while True:
            # Wenn Kamera nicht mehr vorhanden, warte kurz und prüfe weiter
            if camera_id not in camera_frames:
                time.sleep(0.1)
                continue

            with camera_locks.get(camera_id, threading.Lock()):
                frame = camera_frames[camera_id]["bytes"]

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                frame +
                b"\r\n"
            )
            # kleine Pause, damit CPU nicht 100% läuft; Frames werden aktualisiert durch Uploads
            time.sleep(0.03)

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    # Start mit den gewünschten Parametern
    app.run(host="0.0.0.0", port=5001, ssl_context="adhoc", debug=True, threaded=True)