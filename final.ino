#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>
#include <stdarg.h>

// ======================= DEBUG SETTINGS ==========================
#define DEBUG_SERIAL true

void debugPrintf(const char *fmt, ...) {
  if (!DEBUG_SERIAL) return;
  char buf[256];
  va_list args;
  va_start(args, fmt);
  vsnprintf(buf, sizeof(buf), fmt, args);
  va_end(args);
  Serial.print(buf);
}
// ================================================================

// -------------------- PIN CONFIG --------------------
#define SDA_PIN 8
#define SCL_PIN 9
#define DHT_PIN 3
#define DS18B20_PIN 4
#define PUMP_PIN 5
#define CDS_PIN 0
#define SOIL_PIN 2

// -------------------- NETWORK --------------------
const char* ssid = "you";
const char* password = "12345678990";
const char* SERVER_URL = "http://192.168.182.174:5000/log";

// -------------------- OBJECTS --------------------
LiquidCrystal_I2C lcd(0x27, 16, 2);
DHT dht(DHT_PIN, DHT22);
OneWire oneWire(DS18B20_PIN);
DallasTemperature sensors(&oneWire);

// -------------------- TIMING --------------------
unsigned long lastSend = 0;
#define SEND_INTERVAL 3000

// ======================= WIFI ==========================
void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  lcd.clear();
  lcd.print("WiFi Connecting");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    debugPrintf("[WIFI] Connecting...\n");
  }

  debugPrintf("[WIFI] Connected, IP=%s\n",
               WiFi.localIP().toString().c_str());

  lcd.clear();
  lcd.print("WiFi OK");
  lcd.setCursor(0,1);
  lcd.print(WiFi.localIP());
}

// ======================= SETUP ==========================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Wire.begin(SDA_PIN, SCL_PIN);
  lcd.init();
  lcd.backlight();

  dht.begin();
  sensors.begin();

  pinMode(PUMP_PIN, OUTPUT);
  pinMode(SOIL_PIN, INPUT);

  connectWiFi();
}

// ======================= LOOP ==========================
void loop() {
  if (millis() - lastSend >= SEND_INTERVAL || lastSend == 0) {
    lastSend = millis();

    // ---------- SENSOR READ ----------
    float hum = dht.readHumidity();
    float temp_air = dht.readTemperature();

    sensors.requestTemperatures();
    float temp_water = sensors.getTempCByIndex(0);

    int cds_raw = analogRead(CDS_PIN);
    int soil_raw = analogRead(SOIL_PIN);

    int soil_pct = map(soil_raw, 4095, 1500, 0, 100);
    soil_pct = constrain(soil_pct, 0, 100);

    int light_pct = map(cds_raw, 0, 4095, 0, 99);

    // ---------- DEBUG ----------
    debugPrintf(
      "[SENSOR] air=%.1fC hum=%.1f%% water=%.1fC cds=%d soil=%d(%d%%)\n",
      temp_air, hum, temp_water,
      cds_raw, soil_raw, soil_pct
    );

    // ---------- LCD ----------
    lcd.setCursor(0,0);
    lcd.printf("A%d H%d S%d%% ",
               (int)temp_air, (int)hum, soil_pct);

    lcd.setCursor(0,1);
    lcd.printf("W%d L%d ",
               (int)temp_water, light_pct);

    // ---------- HTTP ----------
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(SERVER_URL);
      http.addHeader("Content-Type", "application/json");

      StaticJsonDocument<256> doc;
      doc["temp_air"]   = isnan(temp_air) ? 0 : temp_air;
      doc["humidity"]   = isnan(hum) ? 0 : hum;
      doc["temp_water"] = (temp_water == -127) ? 0 : temp_water;
      doc["cds_raw"]    = cds_raw;
      doc["light_pct"]  = light_pct;
      doc["soil_raw"]   = soil_raw;
      doc["soil_pct"]   = soil_pct;

      char buffer[256];
      serializeJson(doc, buffer);

      debugPrintf("[HTTP] POST %s\n", buffer);

      int code = http.POST(buffer);
      debugPrintf("[HTTP] Response code=%d\n", code);

      lcd.setCursor(15,1);
      lcd.print(code == 200 ? "." : "x");

      http.end();
    }
  }
}
