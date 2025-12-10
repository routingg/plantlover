import sqlite3
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import sys
import traceback

# ===================== CONFIGURATION ===================== #
DB_FILE = "farm_data.db"

MQTT_BROKER_HOST = "localhost"      # Change this to your MQTT broker IP if needed
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "farm/sensor/data"

# If you want very verbose MQTT logs, set this to True
ENABLE_MQTT_LOG = False
# ========================================================= #


def init_db():
    """Initialize the SQLite database and create table if it does not exist."""
    print("[INFO] Initializing SQLite database...")
    print(f"[INFO] Database file path: {DB_FILE}")

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        print("[INFO] Creating table 'sensor_logs' if it does not exist...")
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS sensor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                temp_air REAL,
                humidity REAL,
                temp_water REAL,
                soil_moisture INTEGER,
                cds1 INTEGER
            )
            '''
        )

        conn.commit()
        conn.close()
        print("[INFO] Database initialization completed successfully.")
    except Exception as e:
        print("[ERROR] Failed to initialize database.")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {e}")
        traceback.print_exc()
        sys.exit(1)  # Stop the program if DB cannot be initialized


def save_to_db(data_dict):
    """Save one row of sensor data into the database with detailed debug output."""
    print("[INFO] Preparing to save data into database...")
    print(f"[DEBUG] Data dict received for DB insert: {data_dict}")

    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        sql = '''
            INSERT INTO sensor_logs (timestamp, temp_air, humidity, temp_water, soil_moisture, cds1)
            VALUES (?, ?, ?, ?, ?, ?)
        '''

        temp_air = data_dict.get("temp_air")
        humidity = data_dict.get("humidity")
        temp_water = data_dict.get("temp_water")
        soil = data_dict.get("soil")
        cds1 = data_dict.get("cds1")

        print(f"[DEBUG] Insert values -> timestamp: {current_time}, "
              f"temp_air: {temp_air}, humidity: {humidity}, "
              f"temp_water: {temp_water}, soil_moisture: {soil}, cds1: {cds1}")

        cursor.execute(sql, (current_time, temp_air, humidity, temp_water, soil, cds1))
        conn.commit()
        conn.close()

        print(f"[INFO] Successfully saved one row into database at {current_time}.")
    except Exception as e:
        print("[ERROR] Failed to save data into database.")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {e}")
        traceback.print_exc()


def on_connect(client, userdata, flags, rc):
    """Callback when the client connects to the MQTT broker."""
    print("[CALLBACK] on_connect called.")
    print(f"[DEBUG] on_connect parameters -> rc: {rc}, flags: {flags}, userdata: {userdata}")

    if rc == 0:
        print("[INFO] Successfully connected to MQTT broker!")
        print(f"[INFO] Subscribing to topic: '{MQTT_TOPIC}'")
        client.subscribe(MQTT_TOPIC)
    else:
        print("[ERROR] Failed to connect to MQTT broker.")
        print(f"[ERROR] Return code: {rc}")
        print("        0: Connection successful")
        print("        1: Incorrect protocol version")
        print("        2: Invalid client identifier")
        print("        3: Server unavailable")
        print("        4: Bad username or password")
        print("        5: Not authorized")
        print("        >5: Reserved for future use")


def on_message(client, userdata, msg):
    """Callback when a message is received from the subscribed topic."""
    print("[CALLBACK] on_message called.")
    print(f"[DEBUG] Topic: {msg.topic}")
    print(f"[DEBUG] Raw payload (bytes): {msg.payload}")

    try:
        payload_str = msg.payload.decode("utf-8")
        print(f"[DEBUG] Decoded payload (string): {payload_str}")

        data = json.loads(payload_str)
        print(f"[DEBUG] Parsed JSON data: {data}")

        # Optional: check for expected keys
        expected_keys = ["temp_air", "humidity", "temp_water", "soil", "cds1"]
        for key in expected_keys:
            if key not in data:
                print(f"[WARN] Key '{key}' is missing in the received JSON data.")

        save_to_db(data)

    except UnicodeDecodeError as e:
        print("[ERROR] Failed to decode payload as UTF-8 string.")
        print(f"[ERROR] Exception: {e}")
        traceback.print_exc()
    except json.JSONDecodeError as e:
        print("[ERROR] Failed to parse payload as JSON.")
        print(f"[ERROR] Exception: {e}")
        traceback.print_exc()
        print("[HINT] Please check if the ESP32 is sending valid JSON.")
    except Exception as e:
        print("[ERROR] Unexpected error in on_message.")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {e}")
        traceback.print_exc()


def on_disconnect(client, userdata, rc):
    """Callback when the client disconnects from the MQTT broker."""
    print("[CALLBACK] on_disconnect called.")
    print(f"[DEBUG] on_disconnect parameters -> rc: {rc}, userdata: {userdata}")

    if rc != 0:
        print("[WARN] Unexpected disconnection from MQTT broker.")
        print("[HINT] The broker might have stopped, or there might be a network issue.")
    else:
        print("[INFO] Clean disconnection from MQTT broker.")


def on_log(client, userdata, level, buf):
    """Optional detailed MQTT log callback."""
    # This can generate a lot of logs, so only enable if needed
    print(f"[MQTT-LOG] Level: {level}, Message: {buf}")


def main():
    print("===================================================")
    print("     Smart Farm MQTT → SQLite Subscriber (Debug)   ")
    print("===================================================")
    print("[INFO] Program is starting...")
    print(f"[INFO] MQTT broker host: {MQTT_BROKER_HOST}")
    print(f"[INFO] MQTT broker port: {MQTT_BROKER_PORT}")
    print(f"[INFO] MQTT topic: {MQTT_TOPIC}")
    print("---------------------------------------------------")

    # 1. Initialize DB
    init_db()

    # 2. Set up MQTT client
    print("[INFO] Creating MQTT client instance...")
    client = mqtt.Client()

    # Attach callbacks
    print("[INFO] Attaching MQTT callbacks (on_connect, on_message, on_disconnect)...")
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    if ENABLE_MQTT_LOG:
        print("[INFO] MQTT detailed logging is ENABLED.")
        client.on_log = on_log
    else:
        print("[INFO] MQTT detailed logging is DISABLED. "
              "Set ENABLE_MQTT_LOG = True if you need more logs.")

    # 3. Connect to MQTT broker
    try:
        print(f"[INFO] Attempting to connect to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}...")
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        print("[INFO] Connection request sent. Waiting for on_connect callback...")
    except Exception as e:
        print("[ERROR] Could not connect to MQTT broker.")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {e}")
        print("[HINT] Check if:")
        print("       1) The MQTT broker (e.g., Mosquitto) is running.")
        print("       2) The host and port are correct.")
        print("       3) The network connection is stable.")
        traceback.print_exc()
        sys.exit(1)

    # 4. Start network loop
    print("[INFO] Starting MQTT network loop (loop_forever)...")
    print("[INFO] This program will keep running and wait for incoming messages.")
    print("[INFO] Press Ctrl + C to stop the program safely.")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[INFO] KeyboardInterrupt detected. Stopping the program...")
    except Exception as e:
        print("[ERROR] Unexpected error in main loop.")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        print(f"[ERROR] Exception message: {e}")
        traceback.print_exc()
    finally:
        try:
            print("[INFO] Disconnecting MQTT client...")
            client.disconnect()
        except Exception as e:
            print("[WARN] Error while disconnecting MQTT client.")
            print(f"[WARN] Exception: {e}")
        print("[INFO] Program has been stopped. Goodbye!")


if __name__ == "__main__":
    main()
