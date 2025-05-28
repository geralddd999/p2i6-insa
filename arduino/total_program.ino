#include <Wire.h>
#include <Grove_I2C_Motor_Driver.h>
#include <Encoder.h>
#include <SensirionI2cSht4x.h>

// ------------------- Motor & Encoder Setup -------------------
Encoder myEnc(2, 3);                   // Encoder on pins 2 & 3
#define MOTOR_CHANNEL MOTOR2
byte I2C_ADDRESS = 0x0f;

// ------------------- PI Control Parameters -------------------
float kp = 5.0;
float ki = 0.05;
long consigne = 360;
long degree_step = 45;
unsigned long motor_interval = 10000;

long lastMotorUpdate = 0;
long lastPrintTime = 0;
long previoustime = 0;
float accumulator = 0;
long position = 0;
long erreur = 0;
long commande = 0;

const int switchPin = 7;
bool controlActive = false;

// ------------------- SHT4x Sensor Setup -------------------
#define NO_ERROR 0
SensirionI2cSht4x sensor;
char errorMessage[64];
int16_t error;
uint32_t serialNumber = 0;

unsigned long lastEnvUpdate = 0;
unsigned long envInterval = 10000;

// ------------------- Light Sensor Setup -------------------
const int lightPin = A0;
unsigned long lastLightUpdate = 0;
unsigned long lightInterval = 10000;
void setup() {
  Serial.begin(9600);
  while (!Serial) delay(10);

  Wire.begin();
  pinMode(switchPin, INPUT_PULLUP);

  Motor.begin(I2C_ADDRESS);
  myEnc.write(0);

  // Initialize sensor
  sensor.begin(Wire, SHT40_I2C_ADDR_44);
  sensor.softReset();
  delay(10);
  error = sensor.serialNumber(serialNumber);
  if (error != NO_ERROR) {
    errorToString(error, errorMessage, sizeof(errorMessage));
    Serial.print("SHT4x Error: ");
    Serial.println(errorMessage);
  }

  Serial.println("Motor is rotating... Press button to activate control + sensors");

  // Start rotating motor (open loop)
  Motor.speed(MOTOR_CHANNEL, 50); // Arbitrary speed

  // Wait for button press (goes LOW)
  while (digitalRead(switchPin) == HIGH) {
    delay(10);
  }

  Serial.println("Button pressed. Starting control + sensors.");

  // Stop open-loop motor, reset encoder
  Motor.stop(MOTOR_CHANNEL);
  myEnc.write(0);

  delay(200);  // Debounce delay
  controlActive = true;
  previoustime = millis(); // Initialize control loop timer
}
  
void loop() {
  unsigned long currentTime = millis();

  if (controlActive) {
    // --- PI Motor Control ---
    float dt = (currentTime - previoustime) / 1000.0;
    previoustime = currentTime;

    position = myEnc.read();
    erreur = consigne - position;

    accumulator += erreur * ki * dt;
    accumulator = constrain(accumulator, -255, 255);

    commande = kp * erreur + accumulator;
    commande = constrain(commande, -255, 255);

    Motor.speed(MOTOR_CHANNEL, commande);

    if (currentTime - lastMotorUpdate >= motor_interval) {
      lastMotorUpdate = currentTime;
      consigne += degree_step;
    }

    // --- Temp & Humidity Sensor ---
    if (currentTime - lastEnvUpdate >= envInterval) {
      lastEnvUpdate = currentTime;
      float temperature = 0.0, humidity = 0.0;
      error = sensor.measureLowestPrecision(temperature, humidity);
      if (error != NO_ERROR) {
        errorToString(error, errorMessage, sizeof(errorMessage));
        Serial.print("SHT4x Error: ");
        Serial.println(errorMessage);
      } else {
        Serial.print("Temperature: ");
        Serial.print(temperature, 2);
        Serial.print(" °C ; Humidity: ");
        Serial.print(humidity, 2);
      }
    }

    // --- Light Sensor ---
    if (currentTime - lastLightUpdate >= lightInterval) {
      lastLightUpdate = currentTime;
      int lightReading = analogRead(lightPin);
      float voltage = lightReading * (5.0 / 1023.0);
      Serial.print("; Light: ");
      Serial.print(lightReading);
      Serial.print("; Voltage: ");
      Serial.println(voltage, 2);
    }
  }
}
