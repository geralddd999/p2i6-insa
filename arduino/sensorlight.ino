int lightPin = A1;
unsigned long interval = 10000;
unsigned long last_moment = 0;

void setup() {
  Serial.begin(115200);
}

void loop() {
  if (millis() - last_moment >= interval) {
    last_moment = millis();

    int lightReading = analogRead(lightPin);
    float voltage = lightReading * (5.0 / 1023.0);

    Serial.print("Light: ");
    Serial.print(lightReading);
    Serial.print(" | Voltage: ");
    Serial.println(voltage, 2);
  }
}
