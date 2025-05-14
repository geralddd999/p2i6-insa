#include <Encoder.h>
#include <Arduino.h>
#include <SensirionI2cSht4x.h>
#include <Wire.h>

// Motor + Encoder Setup
Encoder myEnc(2, 5); // Encoder on pins 2 and 5
const int dirPin = 12;
const int pwmPin = 3;
const int switchPin = 4; // Changed from 2 to avoid conflict with encoder
long commande = 0;
long Position;
int erreur;
int consigne = 360;
float kp = 5;
float ki = 0.05;
float dt;
long lastUpdateMotor = 0;
long motorInterval = 10000;
long degree_add = 45;
long prevTimeMotor = 0;
long accumulator = 0;

// Temp + Humidity Sensor
SensirionI2cSht4x sensor;
static char errorMessage[64];
static int16_t error;
const int tempHumInterval = 30000;
unsigned long lastUpdateTempHum = 0;

// Light Sensor
const int lightPin = A1;
const unsigned long lightInterval = 10000;
unsigned long lastUpdateLight = 0;

// Function Prototypes
void moteur(int vit);
void readTempHumidity();
void readLight();

void setup() {
  Serial.begin(115200);
  pinMode(dirPin, OUTPUT);
  pinMode(pwmPin, OUTPUT);
  pinMode(switchPin, INPUT_PULLUP);

  // Wait for switch press to start
  Serial.println("Waiting for start...");
  while (digitalRead(switchPin) == HIGH) {
    digitalWrite(pwmPin, HIGH);
  }
  digitalWrite(pwmPin, LOW);

  // Initialize SHT40
  Wire.begin();
  sensor.begin(Wire, SHT40_I2C_ADDR_44);
  sensor.softReset();
  delay(10);
  uint32_t serialNumber = 0;
  error = sensor.serialNumber(serialNumber);
  if (error != 0) {
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.print("SHT40 error: ");
    Serial.println(errorMessage);
  } else {
    Serial.print("SHT40 Serial: ");
    Serial.println(serialNumber);
  }

  // Header
  Serial.println("Time(ms); Position; Erreur; Commande; Consigne");
}

void loop() {
  unsigned long now = millis();

  // ===== MOTOR CONTROL LOOP =====
  dt = now - prevTimeMotor;
  Position = myEnc.read();
  erreur = consigne - Position;
  accumulator += erreur * ki * dt;
  accumulator = constrain(accumulator, -255, 255);
  commande = kp * erreur + accumulator;
  commande = constrain(commande, -255, 255);
  moteur(commande);

  Serial.print(now); Serial.print("; ");
  Serial.print(Position); Serial.print("; ");
  Serial.print(erreur); Serial.print("; ");
  Serial.print(commande); Serial.print("; ");
  Serial.println(consigne);
  prevTimeMotor = now;

  if (now - lastUpdateMotor >= motorInterval) {
    lastUpdateMotor = now;
    consigne += degree_add;
  }

  // ===== TEMP & HUMIDITY MEASUREMENT =====
  if (now - lastUpdateTempHum >= tempHumInterval) {
    lastUpdateTempHum = now;
    readTempHumidity();
  }

  // ===== LIGHT MEASUREMENT =====
  if (now - lastUpdateLight >= lightInterval) {
    lastUpdateLight = now;
    readLight();
  }
}

// Motor command function
void moteur(int vit) {
  vit = constrain(vit, -255, 255);
  analogWrite(pwmPin, abs(vit));
  digitalWrite(dirPin, vit > 0);
}

// Read temperature and humidity
void readTempHumidity() {
  float temperature = 0.0, humidity = 0.0;
  error = sensor.measureLowestPrecision(temperature, humidity);
  if (error != 0) {
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.print("Temp/Humidity error: ");
    Serial.println(errorMessage);
    return;
  }
  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.print(" °C, Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");
}

// Read light sensor
void readLight() {
  int lightReading = analogRead(lightPin);
  float voltage = lightReading * (5.0 / 1023.0);
  Serial.print("Light: ");
  Serial.print(lightReading);
  Serial.print(" | Voltage: ");
  Serial.println(voltage, 2);
}
