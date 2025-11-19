#include <Wire.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <BH1750.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <LiquidCrystal_I2C.h>

const char* ssid = "";           // WiFi 이름
const char* password = "";   // WiFi 비밀번호
const char* mqtt_server = "192.168.1.100";     // 라즈베리파이 IP


const int mqtt_port = 1883;
const char* mqtt_client_id = "smartfarm_esp32_001";
const char* mqtt_topic = "smartfarm/lab/esp32_001/telemetry/sensors";
const char* device_id = "esp32_001";

#define DHT_PIN 4
#define ONE_WIRE_BUS 5
#define CDS_PIN_1 0
#define CDS_PIN_2 1
#define PUMP_PIN 10
#define DHT_TYPE AM2302

#define TEMP_MIN 10.0
#define TEMP_MAX 40.0
#define HUMIDITY_MIN 30.0
#define HUMIDITY_MAX 90.0
#define WATER_TEMP_MIN 15.0
#define WATER_TEMP_MAX 30.0
#define LUX_MIN 100.0
#define LUX_MAX 50000.0

DHT dht(DHT_PIN, DHT_TYPE);
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
BH1750 lightMeter1;
BH1750 lightMeter2;
LiquidCrystal_I2C lcd(0x27, 16, 2);

WiFiClient espClient;
PubSubClient client(espClient);

unsigned long alertStartTime = 0;
bool alertActive = false;
String alertMessage = "";

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("WiFi 연결 중: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempt = 0;
  while (WiFi.status() != WL_CONNECTED && attempt < 20) {
    delay(500);
    Serial.print(".");
    attempt++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("WiFi 연결 성공!");
    Serial.print("IP 주소: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("");
    Serial.println("WiFi 연결 실패!");
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("MQTT 브로커 연결 시도...");
    
    if (client.connect(mqtt_client_id)) {
      Serial.println("연결 성공!");
    } else {
      Serial.print("연결 실패, rc=");
      Serial.print(client.state());
      Serial.println(" 5초 후 재시도");
      delay(5000);
    }
  }
}

void publishSensorData(float airTemp, float airHumidity, float waterTemp1, 
                       float waterTemp2, float lux1, float lux2, 
                       int cdsValue1, int cdsValue2, bool pumpStatus) {
  
  StaticJsonDocument<512> doc;
  
  doc["id"] = device_id;
  doc["ts"] = millis() / 1000.0;
  doc["air_temp"] = airTemp;
  doc["air_humidity"] = airHumidity;
  doc["water_temp_1"] = waterTemp1;
  doc["water_temp_2"] = waterTemp2;
  doc["lux_1"] = lux1;
  doc["lux_2"] = lux2;
  doc["cds_raw_1"] = cdsValue1;
  doc["cds_raw_2"] = cdsValue2;
  doc["pump_status"] = pumpStatus;
  
  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer);
  
  if (client.publish(mqtt_topic, jsonBuffer)) {
    Serial.println(">>> MQTT 발행 성공");
  } else {
    Serial.println(">>> MQTT 발행 실패");
  }
}

void checkAnomalies(float airTemp, float airHumidity, float waterTemp1, 
                   float waterTemp2, float lux1, float lux2) {
  
  if (isnan(airTemp) || isnan(airHumidity)) {
    triggerAlert("DHT 센서 오류!");
    return;
  }
  
  if (waterTemp1 <= -127 || waterTemp2 <= -127) {
    triggerAlert("수온 센서 오류!");
    return;
  }
  
  if (airTemp < TEMP_MIN || airTemp > TEMP_MAX) {
    triggerAlert("대기온도 이상!");
    return;
  }
  
  if (airHumidity < HUMIDITY_MIN || airHumidity > HUMIDITY_MAX) {
    triggerAlert("습도 이상!");
    return;
  }
  
  if (waterTemp1 < WATER_TEMP_MIN || waterTemp1 > WATER_TEMP_MAX) {
    triggerAlert("수온1 이상!");
    return;
  }
  
  if (waterTemp2 < WATER_TEMP_MIN || waterTemp2 > WATER_TEMP_MAX) {
    triggerAlert("수온2 이상!");
    return;
  }
  
  if (lux1 < LUX_MIN || lux1 > LUX_MAX) {
    triggerAlert("조도1 이상!");
    return;
  }
  
  if (lux2 < LUX_MIN || lux2 > LUX_MAX) {
    triggerAlert("조도2 이상!");
    return;
  }
}

void triggerAlert(String message) {
  alertMessage = message;
  alertStartTime = millis();
  alertActive = true;
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("!! WARNING !!");
  lcd.setCursor(0, 1);
  lcd.print(message);
  
  Serial.print(">>> 경고: ");
  Serial.println(message);
}

void updateLCD(float airTemp, float airHumidity, float waterTemp1, bool pumpStatus) {
  if (alertActive) {
    if (millis() - alertStartTime >= 5000) {
      alertActive = false;
      lcd.clear();
    } else {
      return;
    }
  }
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("T:");
  lcd.print(airTemp, 1);
  lcd.print("C H:");
  lcd.print(airHumidity, 0);
  lcd.print("%");
  
  lcd.setCursor(0, 1);
  lcd.print("W:");
  lcd.print(waterTemp1, 1);
  lcd.print("C P:");
  lcd.print(pumpStatus ? "ON " : "OFF");
}

void setup() {
  Serial.begin(115200);
  Serial.println("========================================");
  Serial.println("ESP32 스마트팜 MQTT Publisher");
  Serial.println("========================================");
  
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW);
  
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SmartFarm v1.0");
  lcd.setCursor(0, 1);
  lcd.print("Starting...");
  delay(2000);
  
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  
  dht.begin();
  sensors.begin();
  Wire.begin();
  
  lightMeter1.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x23, &Wire);
  lightMeter2.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x5C, &Wire);
  
  Serial.println("========================================");
  Serial.println("초기화 완료");
  Serial.println("========================================");
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("System Ready");
  delay(1000);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi 재연결 중...");
    setup_wifi();
  }
  
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  float airHumidity = dht.readHumidity();
  float airTemp = dht.readTemperature();
  
  sensors.requestTemperatures();
  float waterTemp1 = sensors.getTempCByIndex(0);
  float waterTemp2 = sensors.getTempCByIndex(1);
  
  float lux1 = lightMeter1.readLightLevel();
  float lux2 = lightMeter2.readLightLevel();
  
  int cdsValue1 = analogRead(CDS_PIN_1);
  int cdsValue2 = analogRead(CDS_PIN_2);
  
  Serial.println("============================");
  Serial.print("대기 온도: ");
  Serial.print(airTemp);
  Serial.println(" °C");
  Serial.print("대기 습도: ");
  Serial.print(airHumidity);
  Serial.println(" %");
  Serial.print("물 온도 1: ");
  Serial.print(waterTemp1);
  Serial.println(" °C");
  Serial.print("물 온도 2: ");
  Serial.print(waterTemp2);
  Serial.println(" °C");
  Serial.print("조도 1: ");
  Serial.print(lux1);
  Serial.println(" lx");
  Serial.print("조도 2: ");
  Serial.print(lux2);
  Serial.println(" lx");
  Serial.println("============================");
  
  bool pumpStatus = false;
  if (waterTemp1 < 20.0 && waterTemp1 > 0.0) {
    Serial.println("-> 펌프 ON");
    digitalWrite(PUMP_PIN, HIGH);
    pumpStatus = true;
  } else {
    Serial.println("-> 펌프 OFF");
    digitalWrite(PUMP_PIN, LOW);
    pumpStatus = false;
  }
  
  checkAnomalies(airTemp, airHumidity, waterTemp1, waterTemp2, lux1, lux2);
  updateLCD(airTemp, airHumidity, waterTemp1, pumpStatus);
  publishSensorData(airTemp, airHumidity, waterTemp1, waterTemp2, 
                    lux1, lux2, cdsValue1, cdsValue2, pumpStatus);
  
  Serial.println("");
  delay(5000);
}