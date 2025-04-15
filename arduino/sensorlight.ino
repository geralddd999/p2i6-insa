int lightpin = A0;
long interval = 10000;
long last_moment = 0;
float light = 0.0;
void setup() {
  Serial.begin(115200);
}
void loop() {
  if (millis()-last_moment >= interval){
    last_moment = millis();
    int lightReading = analogRead(lightPin);  
    light = (float)(1023-lightReading)*10/lightReading;
    Serial.println(light)
  }
}
