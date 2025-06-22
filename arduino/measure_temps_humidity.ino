#include <Arduino.h>
#include <SensirionI2cSht4x.h>
#include <Wire.h>

#ifdef NO_ERROR
#undef NO_ERROR
#endif
#define NO_ERROR 0

SensirionI2cSht4x sensor;

static char errorMessage[64];
static int16_t error;

int timelapse = 30000;
void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(100);
  }
  Wire.begin();
  sensor.begin(Wire, SHT40_I2C_ADDR_44);

  sensor.softReset();
  delay(10);
  uint32_t serialNumber = 0;
  error = sensor.serialNumber(serialNumber);
  if (error != NO_ERROR) {
    Serial.print("Error trying to execute serialNumber(): ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
    return;
  }
  Serial.print("serialNumber: ");
  Serial.print(serialNumber);
  Serial.println();
}

void loop() {
  float temperature = 0.0;
  float humidity = 0.0;
  delay(timelapse);
  error = sensor.measureLowestPrecision(temperature, humidity);
  if (error != NO_ERROR) {
    Serial.print("Error trying to execute measureLowestPrecision(): ");
    errorToString(error, errorMessage, sizeof errorMessage);
    Serial.println(errorMessage);
    return;
  }
  Serial.println(temperature + "," + humidity);
}
