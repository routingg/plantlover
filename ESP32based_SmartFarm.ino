
#include <Arduino.h>
#include <Wire.h>          // I2C 통신용 (BH1750)
#include <DHT.h>           // AM2302 (DHT22)
#include <OneWire.h>       // DS18B20
#include <DallasTemperature.h> // DS18B20
#include <BH1750.h>        // BH1750


#define DHT_PIN 4        
#define ONE_WIRE_BUS 5    
#define CDS_PIN_1 0       
#define CDS_PIN_2 1    
#define PUMP_PIN 10        

#define DHT_TYPE AM2302
DHT dht(DHT_PIN, DHT_TYPE);
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

BH1750 lightMeter1; 
BH1750 lightMeter2;


void setup() {
  Serial.begin(115200);
  Serial.println("--- ESP32-C3 스마트팜 시스템 시작 ---");


  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW);

  // AM2302 시작
  dht.begin();

  // DS18B20 시작
  sensors.begin();
  int ds18b20Count = sensors.getDeviceCount();
  Serial.print(ds18b20Count);
  Serial.println("개의 DS18B20 센서가 발견되었습니다.");

  Wire.begin(); 
  
  if (lightMeter1.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x23, &Wire)) {
    Serial.println("BH1750 (0x23) 시작 성공");
  } else {
    Serial.println("BH1750 (0x23) 시작 실패");
  }

  
  if (lightMeter2.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x5C, &Wire)) {
    Serial.println("BH1750 (0x5C) 시작 성공");
  } else {
    Serial.println("BH1750 (0x5C) 시작 실패");
  }

  Serial.println("설정이 완료되었습니다.");
}

void loop() {



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
  Serial.print("대기 온도: "); Serial.print(airTemp); Serial.println(" °C");
  Serial.print("대기 습도: "); Serial.print(airHumidity); Serial.println(" %");
  Serial.println("---");
  Serial.print("물 온도 1: "); Serial.print(waterTemp1); Serial.println(" °C");
  Serial.print("물 온도 2: "); Serial.print(waterTemp2); Serial.println(" °C");
  Serial.println("---");
  Serial.print("조도 1 (BH1750): "); Serial.print(lux1); Serial.println(" lx");
  Serial.print("조도 2 (BH1750): "); Serial.print(lux2); Serial.println(" lx");
  Serial.println("---");
  Serial.print("조도 1 (CdS Raw): "); Serial.println(cdsValue1);
  Serial.print("조도 2 (CdS Raw): "); Serial.println(cdsValue2);
  Serial.println("============================");


  if (waterTemp1 < 20.0 && waterTemp1 > 0.0) {
    Serial.println("-> 물 온도가 낮습니다. 펌프(릴레이) ON");
    digitalWrite(PUMP_PIN, HIGH);
  } else {
    Serial.println("-> 물 온도가 적정합니다. 펌프(릴레이) OFF");
    digitalWrite(PUMP_PIN, LOW);
  }

  // 5초 간격
  delay(5000); 
}