from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import base64, re, threading, time, io
from PIL import Image
import cv2
import numpy as np

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

camera_frames = {}
camera_locks = {}
camera_last_frame = {}
camera_last_time = {}

TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
TARGET_FPS = 60
FRAME_INTERVAL = 1.0 / TARGET_FPS


def upscale_720_to_1080(img_bytes):
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except:
        return img_bytes

    w, h = img.size
    if w == TARGET_WIDTH and h == TARGET_HEIGHT:
        return img_bytes

    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    upscaled = cv2.resize(cv_img, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_LANCZOS4)
    ok, buf = cv2.imencode(".jpg", upscaled, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes() if ok else img_bytes


def interpolate_frames(frame_a, frame_b, alpha):
    """Erzeugt Zwischenframe: A*(1-alpha) + B*alpha"""
    imgA = cv2.imdecode(np.frombuffer(frame_a, np.uint8), cv2.IMREAD_COLOR)
    imgB = cv2.imdecode(np.frombuffer(frame_b, np.uint8), cv2.IMREAD_COLOR)
    blended = cv2.addWeighted(imgA, 1 - alpha, imgB, alpha, 0)
    ok, buf = cv2.imencode(".jpg", blended, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes() if ok else frame_a


@app.route("/upload_frame/<camera_id>", methods=["POST"])
def upload_frame(camera_id):
    data = request.json.get("image")
    if not data:
        return jsonify({"error": "no image"}), 400

    img_str = re.sub(r"^data:image/.+;base64,", "", data)
    img_bytes = base64.b64decode(img_str)

    img_bytes = upscale_720_to_1080(img_bytes)

    now = time.time()

    if camera_id not in camera_locks:
        camera_locks[camera_id] = threading.Lock()

    with camera_locks[camera_id]:
        camera_last_frame[camera_id] = img_bytes
        camera_last_time[camera_id] = now

    return jsonify({"status": "ok"}), 200


@app.route("/stream/<camera_id>")
def stream_camera(camera_id):
    def generate():
        last_output = None
        last_output_time = 0

        while True:
            now = time.time()

            if now - last_output_time < FRAME_INTERVAL:
                time.sleep(0.001)
                continue

            with camera_locks.get(camera_id, threading.Lock()):
                new_frame = camera_last_frame.get(camera_id)
                new_time = camera_last_time.get(camera_id)

            if new_frame is None:
                time.sleep(0.01)
                continue

            if last_output is None:
                last_output = new_frame
                last_output_time = now
            else:
                dt = new_time - last_output_time

                if dt > FRAME_INTERVAL:
                    alpha = min(1.0, FRAME_INTERVAL / dt)
                    new_frame = interpolate_frames(last_output, new_frame, alpha)

                last_output = new_frame
                last_output_time = now

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                last_output +
                b"\r\n"
            )

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/cameras")
def list_cameras():
    return jsonify(list(camera_last_frame.keys()))


@app.route("/api/camera/<camera_id>")
def get_camera_image(camera_id):
    if camera_id not in camera_last_frame:
        return jsonify({"error": "camera not found"}), 404
    return Response(camera_last_frame[camera_id], mimetype="image/jpeg")


if __name__ == "__main__":
    app.run("0.0.0.0", 5001, debug=True, threaded=True)