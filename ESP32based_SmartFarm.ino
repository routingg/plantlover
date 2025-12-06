#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>

// --- 1. 핀 설정 (C3 Supermini) ---
#define SDA_PIN 8
#define SCL_PIN 9
#define DHT_PIN 3
#define Dz S18B20_PIN 4
#define PUMP_PIN 5
#define CDS_PIN_1 0
#define CDS_PIN_2 1

// --- 2. 네트워크 정보 (수정 필수) ---
const char* ssid = ".의 Z Flip6";
const char* password = "tml72390";
const char* mqtt_server = "192.168.XX.XX"; // 라즈베리파이 IP
const int mqtt_port = 1883;
const char* mqtt_topic = "farm/sensor/data";

// --- 3. 객체 생성 ---
WiFiClient espClient;
PubSubClient client(espClient);
LiquidCrystal_I2C lcd(0x27, 16, 2); 
DHT dht(DHT_PIN, DHT22);
OneWire oneWire(DS18B20_PIN);
DallasTemperature sensors(&oneWire);

unsigned long lastMsg = 0;
#define MSG_INTERVAL 3000 // 3초마다 갱신 (반응 속도 높임)

void setup_wifi() {
  lcd.setCursor(0, 0);
  lcd.print("WiFi Conn...");
  WiFi.begin(ssid, password);

  int retry = 0;
  // 10초(20번)만 시도하고 안 되면 일단 센서 화면으로 넘어감 (Non-blocking 느낌)
  while (WiFi.status() != WL_CONNECTED && retry < 20) { 
    delay(500);
    retry++;
  }

  if(WiFi.status() == WL_CONNECTED) {
    lcd.setCursor(0, 1);
    lcd.print("OK: ");
    lcd.print(WiFi.localIP());
    delay(1000); // IP 확인용 1초 대기
  } else {
    lcd.setCursor(0, 1);
    lcd.print("Skip WiFi...");
    delay(1000);
  }
}

void reconnect() {
  // 연결이 끊겼을 때 한 번만 시도하고 바로 나감 (LCD 멈춤 방지)
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
  digitalWrite(PUMP_PIN, LOW);

  // 와이파이 연결 시도
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);

  // 시작하자마자 화면 클리어
  lcd.clear();
}

void loop() {
  // MQTT 연결 관리 (연결 되어있으면 유지, 아니면 재접속 시도하되 멈추지 않음)
  if (WiFi.status() == WL_CONNECTED) {
    if (!client.connected()) {
      reconnect();
    }
    client.loop();
  }

  unsigned long now = millis();
  // 3초마다 실행 (또는 시작 직후 실행)
  if (now - lastMsg > MSG_INTERVAL || lastMsg == 0) {
    lastMsg = now;

    // 1. 센서 읽기
    float hum = dht.readHumidity();
    float temp_air = dht.readTemperature();
    sensors.requestTemperatures(); 
    float temp_water = sensors.getTempCByIndex(0);
    int cds1 = analogRead(CDS_PIN_1);
    int cds2 = analogRead(CDS_PIN_2);

    // 2. LCD 출력 (화면 깜빡임 최소화)
    // 값만 갱신하는 것이 좋지만, 간단하게 전체 갱신
    lcd.setCursor(0, 0);
    lcd.print("A:"); 
    if(isnan(temp_air)) lcd.print("err"); else lcd.print((int)temp_air); // 정수형으로 짧게 표시
    lcd.print("C W:"); 
    if(temp_water == -127.00) lcd.print("err"); else lcd.print((int)temp_water);
    lcd.print("C  "); // 잔상 제거용 공백

    lcd.setCursor(0, 1);
    lcd.print("H:"); 
    if(isnan(hum)) lcd.print("err"); else lcd.print((int)hum);
    lcd.print("% L:"); 
    lcd.print(map(cds1, 0, 4095, 0, 99)); // 2자리 수로 맞춤
    lcd.print("% "); 
    
    // MQTT 연결 상태 표시 (우측 하단 점)
    if(client.connected()) lcd.print("."); else lcd.print("x");

    // 3. MQTT 전송
    if (client.connected()) {
      StaticJsonDocument<200> doc;
      doc["temp_air"] = isnan(temp_air) ? 0.0 : temp_air;
      doc["humidity"] = isnan(hum) ? 0.0 : hum;
      doc["temp_water"] = (temp_water == -127.00) ? 0.0 : temp_water;
      doc["cds1"] = cds1;
      doc["cds2"] = cds2;
      char buffer[256];
      serializeJson(doc, buffer);
      client.publish(mqtt_topic, buffer);
    }
  }
}