import sqlite3
import paho.mqtt.client as mqtt
import json
from datetime import datetime

DB_FILE = "farm_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # soil_moisture 컬럼 추가됨
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            temp_air REAL,
            humidity REAL,
            temp_water REAL,
            soil_moisture INTEGER, 
            cds1 INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # INSERT 문에도 soil 추가
        sql = '''
            INSERT INTO sensor_logs (timestamp, temp_air, humidity, temp_water, soil_moisture, cds1)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        cursor.execute(sql, (
            current_time, 
            data.get("temp_air"), 
            data.get("humidity"), 
            data.get("temp_water"), 
            data.get("soil"),  # JSON 키값 'soil'
            data.get("cds1")
        ))
        conn.commit()
        conn.close()
        print(f"[{current_time}] 저장 완료 (Soil: {data.get('soil')}%)")

    except Exception as e:
        print(f"Error: {e}")

init_db()
client = mqtt.Client()
client.on_connect = lambda c, u, f, rc: c.subscribe("farm/sensor/data")
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.loop_forever()
