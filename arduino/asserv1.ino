#include <Encoder.h>
Encoder myEnc(2, 5);

long commande = 0;
long Position;
int erreur;
int consigne = 360; 
float kp = 5;
float ki = 0.05;
float dt;
long last_moment = 0;
long interval = 10000;
long degree_add = 45;
long previoustemps, accumulator = 0;

void setup() {
  Serial.begin(115200);
  pinMode(12, OUTPUT);    
  pinMode(3, OUTPUT);    
  Serial.print("temps (ms)");
  Serial.print(" ; ");
  Serial.print("position");
  Serial.print(" ; ");
  Serial.print("consigne");
  Serial.print(" ; ");
  Serial.println("commande");
}


void loop() {
  long temps = millis();
  dt = temps - previoustemps;
  Position = myEnc.read();  
  erreur = consigne - Position; 
  accumulator = accumulator + erreur * ki * dt;
  accumulator=constrain(accumulator,-255,255);
  commande = kp * erreur + accumulator;  
  commande=constrain(commande,-255,255);
  moteur(commande);
  Serial.print(Position);
  Serial.print(" ; ");
  Serial.print(erreur);
  Serial.print(" ; ");
  Serial.print(commande);
  Serial.print(" ; ");
  Serial.println(consigne);
  previoustemps = temps;
  if (millis()-last_moment >= interval){
    last_moment = millis();
    consigne += degree_add;
  }
}


void moteur(int vit) {
  if (vit > 255) vit = 255;
  if (vit < -255) vit = -255;
  analogWrite(3, abs(vit));
  digitalWrite(12, (vit > 0));
}
