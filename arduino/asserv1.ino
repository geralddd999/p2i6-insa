#include <Encoder.h>
Encoder myEnc(2, 5);

long commande = 0;
long Position;
int erreur;
int consigne = 360; //consigne en position à atteindre
float kp = 5;
float ki = 0.05;
float dt;
long last_moment = 0;
long interval = 10000;
long degree_add = 45;
long previoustemps, accumulator = 0;
// int temppin = A0;
// int humitypin = A5;
// float temperature = 0.0;
// float humidity = 0.0;

void setup() {
  //initialisation et acquisition de la valeur du correcteur proportionnel Kp à travers le moniteur série
  Serial.begin(115200);
  pinMode(12, OUTPUT);    //pin Direction
  pinMode(3, OUTPUT);    //pin PWM
  Serial.print("temps (ms)");
  Serial.print(" ; ");
  Serial.print("position");
  Serial.print(" ; ");
  Serial.print("consigne");
  Serial.print(" ; ");
  Serial.println("commande");
}


void loop() {
  //Attention, mettre le moniteur serie a 115200 baud pour pouvoir lire l'affichage
  long temps = millis();
  dt = temps - previoustemps;
  Position = myEnc.read();  //lecture de la position du codeur
  erreur = consigne - Position; // calcul de la valeur de l'erreur
  accumulator = accumulator + erreur * ki * dt;
  accumulator=constrain(accumulator,-255,255);
  commande = kp * erreur + accumulator;  // calcul de la valeur de commande moteur en fonction de kp et de erreur;
  commande=constrain(commande,-255,255);
  moteur(commande);
  //Serial.print(millis());
  //Serial.print(" ; ");
  Serial.print(Position);
  Serial.print(" ; ");
  Serial.print(erreur);
  Serial.print(" ; ");
  Serial.print(commande);
  Serial.print(" ; ");
  Serial.println(consigne);
  previoustemps = temps;
  // int tempReading = analogRead(tempPin);  
  // temperature = (tempReading * (5.0 / 1023.0)) * 100.0;  
  // int humidityReading = analogRead(humidityPin);  
  // humidity = (humidityReading * (100.0 / 1023.0)); 
  if (millis()-last_moment >= interval){
    last_moment = millis();
    consigne += degree_add;
  }
}


//Commande du moteur
void moteur(int vit) {
  //vit est un entier
  //accepte et gere les vitesse positives ou negatives
  if (vit > 255) vit = 255;
  if (vit < -255) vit = -255;
  analogWrite(3, abs(vit));
  digitalWrite(12, (vit > 0));
}
