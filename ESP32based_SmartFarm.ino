#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>

// --- 1. 핀 설정 (토양 센서 추가됨) ---
#define SDA_PIN 8
#define SCL_PIN 9
#define DHT_PIN 3
#define DS18B20_PIN 4
#define PUMP_PIN 5
#define CDS_PIN_1 0
#define CDS_PIN_2 1
#define SOIL_PIN 2  // <--- 토양센서 (AO핀 연결)

// --- 2. 네트워크 설정 (수정 필요) ---
const char* ssid = "아이폰_핫스팟_이름";     
const char* password = "핫스팟_비밀번호";  
const char* mqtt_server = "192.168.XX.XX"; 
const int mqtt_port = 1883;
const char* mqtt_topic = "farm/sensor/data"; // 토픽은 그대로 유지 (데이터만 추가)

// --- 3. 객체 생성 ---
WiFiClient espClient;
PubSubClient client(espClient);
LiquidCrystal_I2C lcd(0x27, 16, 2); 
DHT dht(DHT_PIN, DHT22);
OneWire oneWire(DS18B20_PIN);
DallasTemperature sensors(&oneWire);

unsigned long lastMsg = 0;
#define MSG_INTERVAL 3000 

void setup_wifi() {
  lcd.setCursor(0, 0);
  lcd.print("WiFi Conn...");
  WiFi.begin(ssid, password);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 20) { 
    delay(500); retry++;
  }
}

void reconnect() {
  if (!client.connected()) {
    String clientId = "ESP32-" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str())) {
      // 연결 성공
    }
  }
}

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  
  lcd.init();
  lcd.backlight();
  
  dht.begin();
  sensors.begin();
  pinMode(PUMP_PIN, OUTPUT);
  pinMode(SOIL_PIN, INPUT); // 토양센서 핀 설정

  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  lcd.clear();
}

void loop() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!client.connected()) reconnect();
    client.loop();
  }

  unsigned long now = millis();
  if (now - lastMsg > MSG_INTERVAL || lastMsg == 0) {
    lastMsg = now;

    // 1. 센서 읽기
    float hum = dht.readHumidity();
    float temp_air = dht.readTemperature();
    sensors.requestTemperatures(); 
    float temp_water = sensors.getTempCByIndex(0);
    int cds_raw = analogRead(CDS_PIN_1); // CDS 1개만 대표로 표시
    
    // [토양 센서 읽기]
    int soil_raw = analogRead(SOIL_PIN);
    // 보정: 공기중(건조)=4095, 물속(습함)=약 1500 (센서마다 다름)
    // 4095(0%) ~ 1500(100%)로 매핑. map함수는 정수만 반환하므로 주의
    int soil_pct = map(soil_raw, 4095, 1500, 0, 100); 
    soil_pct = constrain(soil_pct, 0, 100); // 0~100 범위 강제 고정

    // 2. LCD 출력 (레이아웃 변경)
    // 윗줄: A:24 H:60 S:50 (공기,습도,흙)
    lcd.setCursor(0, 0);
    lcd.print("A"); lcd.print((int)temp_air);
    lcd.print(" H"); lcd.print((int)hum);
    lcd.print(" S"); lcd.print(soil_pct); lcd.print("%  ");

    // 아랫줄: W:25 L:80 . (수온,조도,상태)
    lcd.setCursor(0, 1);
    lcd.print("W"); 
    if(temp_water == -127) lcd.print("Er"); else lcd.print((int)temp_water);
    lcd.print(" L"); lcd.print(map(cds_raw, 0, 4095, 0, 99));
    
    lcd.setCursor(15, 1);
    if(client.connected()) lcd.print("."); else lcd.print("x");

    // 3. MQTT 전송 (soil 추가)
    if (client.connected()) {
      StaticJsonDocument<256> doc; // 용량 살짝 늘림
      doc["temp_air"] = isnan(temp_air) ? 0.0 : temp_air;
      doc["humidity"] = isnan(hum) ? 0.0 : hum;
      doc["temp_water"] = (temp_water == -127.00) ? 0.0 : temp_water;
      doc["soil"] = soil_pct; // <--- 토양 습도 추가
      doc["cds1"] = cds_raw;
      
      char buffer[256];
      serializeJson(doc, buffer);
      client.publish(mqtt_topic, buffer);
    }
  }
}
