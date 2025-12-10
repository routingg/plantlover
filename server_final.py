from flask import Flask, request, jsonify
import csv, os
from datetime import datetime
import logging

app = Flask(__name__)
CSV_FILE = "sensor_data.csv"

# ---------------- LOG CONFIG ----------------
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
log = logging.getLogger("SmartFarm")

# ---------------- ROUTE ----------------
@app.route("/log", methods=["POST"])
def log_data():
    log.debug("========== NEW DATA ==========")
    log.debug(f"Remote IP: {request.remote_addr}")
    log.debug(f"Raw body: {request.data}")

    try:
        data = request.get_json(force=True)
    except Exception as e:
        log.error(f"JSON parse error: {e}")
        return jsonify({"status": "error", "reason": "json_parse"}), 400

    log.debug(f"Parsed JSON: {data}")

    # timestamp + ��� ���� �ڵ� ����
    row = {"timestamp": datetime.now().isoformat()}
    row.update(data)

    file_exists = os.path.exists(CSV_FILE)

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    log.info(f"[SAVED] {row}")

    return jsonify({"status": "ok"}), 200

# ---------------- MAIN ----------------
if __name__ == "__main__":
    log.info("Smart Farm HTTP Server running (port 5000)")
    app.run(host="0.0.0.0", port=5000, debug=True)
