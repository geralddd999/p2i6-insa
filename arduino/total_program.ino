#include <Wire.h>
#include <Grove_I2C_Motor_Driver.h>
#include <Encoder.h>
#include <SensirionI2cSht4x.h>
Encoder myEnc(2, 3);  
#define MOTOR_CHANNEL MOTOR2
byte I2C_ADDRESS = 0x0f;

float kp = 5.7;
float ki = 0.1;
float kd = 0.1;
long consigne = 0;
long degree_step = -45;
long derive = 0;
unsigned long motor_interval = 10000;

long lastMotorUpdate = 0;
long lastPrintTime = 0;
long previoustime = 0;
float accumulator = 0;
long position = 0;
long erreur = 2000;
long commande = 0;
long previous_error = 0;

const int switchPin = 7;
bool controlActive = false;

#define NO_ERROR 0
SensirionI2cSht4x sensor;
char errorMessage[64];
int16_t error;
uint32_t serialNumber = 0;

unsigned long lastEnvUpdate = 0;
unsigned long envInterval = 10000;

const int lightPin = A1;
unsigned long lastLightUpdate = 0;
unsigned long lightInterval = 10000;
void go_to_zero() {
  const float tolerance = 2.0; 
  const float KP = 16;
  long position = myEnc.read();
  long error_counts = position;
  // Serial.println("Moving to position 0...");
  while (abs(error_counts) > tolerance) {
    position = myEnc.read();
    error_counts = 0 - position; 
    long command = KP * error_counts;
    command = constrain(command, -255, 255);
    Motor.speed(MOTOR_CHANNEL, command);

    // Serial.print("Position: ");
    // Serial.print(position);
    // Serial.print(" ; Error: ");
    // Serial.println(error_counts);

    delay(100);  
  }

  Motor.stop(MOTOR_CHANNEL);
  // Serial.println("Reached position 0.");
  delay(1000);
  myEnc.write(0);
}

void setup() {
  Serial.begin(9600);
  while (!Serial) delay(10);

  Wire.begin();
  pinMode(switchPin, INPUT);

  Motor.begin(I2C_ADDRESS);
  myEnc.write(0);
  sensor.begin(Wire, SHT40_I2C_ADDR_44);
  sensor.softReset();
  delay(10);
  error = sensor.serialNumber(serialNumber);
  if (error != NO_ERROR) {
    errorToString(error, errorMessage, sizeof(errorMessage));
    Serial.print("SHT4x Error: ");
    Serial.println(errorMessage);
  }
  
  Motor.speed(MOTOR_CHANNEL, -255); 
  while (digitalRead(switchPin) == LOW) {
    delay(10);
    // Serial.println("k");
  }
  Motor.stop(MOTOR_CHANNEL);
  delay(1000);
  myEnc.write(60);
  go_to_zero();
  delay(200); 
  controlActive = true;
  previoustime = millis(); 
}

void loop() {
  unsigned long currentTime = millis();
  if (controlActive) {
    float dt = (currentTime - previoustime) / 1000.0;
    previoustime = currentTime;

    position = myEnc.read();
    erreur = consigne - position;

    accumulator += erreur * ki * dt;
    accumulator = constrain(accumulator, -255, 255);

    derive = (error-previous_error)/dt;
    // commande = kp * erreur + accumulator;
    previous_error = error;
    commande = kp * erreur + accumulator - kd * derive;
    commande = constrain(commande, -255, 255);
    // Serial.print("Time: ");
    // Serial.print(currentTime);
    // Serial.print(" ms ; Position: ");
    // Serial.print(position);
    // Serial.print(" ; Error: ");
    // Serial.print(erreur);
    // Serial.print(" ; Command: ");
    // Serial.print(commande);
    // Serial.print(" ; Consigne: ");
    // Serial.println(consigne);
    Motor.speed(MOTOR_CHANNEL, commande);

    if (currentTime - lastMotorUpdate >= motor_interval) {
      lastMotorUpdate = currentTime;
      consigne += degree_step;
    }

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

    if (currentTime - lastLightUpdate >= lightInterval) {
      lastLightUpdate = currentTime;
      int lightReading = analogRead(lightPin);
      float voltage = lightReading * (5.0 / 1023.0);
      Serial.print("; Light: ");
      Serial.print(lightReading);
      Serial.print("; Voltage: ");
      Serial.println(voltage, 2);
    }

    if (digitalRead(switchPin) == HIGH) {
      position = myEnc.read();
      if (abs((position % 1080) - 1020) > 4) {
        go_to_zero();
        consigne = 0;
      }
    }
  }
}