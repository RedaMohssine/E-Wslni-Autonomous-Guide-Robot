#include <SimpleTimer.h>
SimpleTimer timer;

// --- MOTEURS ---
const int M1_DIR = 7; const int M1_PWM = 6;
const int M2_DIR = 4; const int M2_PWM = 5;

// --- ENCODEURS ---
#define ENC1_A 2 
#define ENC1_B 3
#define ENC2_A 18
#define ENC2_B 19

// --- BATTERIE GRAPHENE 3S ---
const int PIN_BATTERIE = A15;
const int PIN_RELAY = 10;
const float VOLT_MAX = 12.6;
const float VOLT_MIN = 10.2;
const float VOLT_STOP = 10;
const float RATIO_CAPTEUR = 4.841;
bool batterie_critique = false;
bool relay_active = false;

// --- GEOMETRIE ROBOT ---
const double RAYON_ROUE = 0.10; 
const double ENTRAXE = 0.488;    

// --- PARAMETRES PHYSIQUES ---
const int rapport_reducteur = 131;
const int resolution = 64;
const int fe = 128; 
const double dt = 1.0 / fe; 

// --- PID + FEEDFORWARD (INCHANGÉ) ---
double Kp = 15; double Ki = 5; double Kd = 0.02; double Kf = 2.3;  

// --- BOUCLE W EXTERNE (correction cap) ---
double Kp_w = 0.8;
double Ki_w = 1.5;
double w_err_sum = 0;

// --- DEADBAND ---
const int PWM_DEADBAND = 20;
const double SLIP_THRESHOLD = 30.0;

// --- CIBLES CINEMATIQUES ---
double target_V = 0; double target_W = 0;
double current_V = 0; double current_W = 0;

double accel_V_step = (0.16 / fe); 
double decel_V_step = (0.22 / fe); 
double accel_W_step = (0.5  / fe); 

double rpm1_filtered = 0; double rpm2_filtered = 0;
double errorSum1 = 0, lastError1 = 0;
double errorSum2 = 0, lastError2 = 0;
volatile long tick1 = 0; volatile long tick2 = 0;
int plotCounter = 0;

// --- INTERRUPTIONS ---
void ISR_Enc1A() { if (digitalRead(ENC1_A) == digitalRead(ENC1_B)) tick1--; else tick1++; }
void ISR_Enc1B() { if (digitalRead(ENC1_A) == digitalRead(ENC1_B)) tick1++; else tick1--; }
void ISR_Enc2A() { if (digitalRead(ENC2_A) == digitalRead(ENC2_B)) tick2++; else tick2--; }
void ISR_Enc2B() { if (digitalRead(ENC2_A) == digitalRead(ENC2_B)) tick2--; else tick2++; }

void setMotorPWM(int pwm, int pinPWM, int pinDIR) {
  pwm = constrain(pwm, -255, 255);
  if (pwm > 0 && pwm < PWM_DEADBAND) pwm = PWM_DEADBAND;
  if (pwm < 0 && pwm > -PWM_DEADBAND) pwm = -PWM_DEADBAND;
  if (abs(pwm) < 5) pwm = 0;
  if (pinDIR == M2_DIR) pwm = -pwm;
  if (pwm >= 0) { digitalWrite(pinDIR, LOW); analogWrite(pinPWM, abs(pwm)); }
  else          { digitalWrite(pinDIR, HIGH); analogWrite(pinPWM, abs(pwm)); }
}

float lireVoltage() {
  int raw = analogRead(PIN_BATTERIE);
  return (raw * 5.0 / 1024.0) * RATIO_CAPTEUR;
}

int calculerPourcentage(float v) {
  float p = (v - VOLT_MIN) / (VOLT_MAX - VOLT_MIN) * 100.0;
  return constrain((int)p, 0, 100);
}

void boucle_controle() {
  float vBatCurrent = lireVoltage();

  if (relay_active) {
    target_V = 0; target_W = 0;
    current_V = 0; current_W = 0;
    w_err_sum = 0;
    errorSum1 = 0; errorSum2 = 0;
    setMotorPWM(0, M1_PWM, M1_DIR);
    setMotorPWM(0, M2_PWM, M2_DIR);
    return;
  }

  long t1, t2;
  noInterrupts(); t1 = tick1; tick1 = 0; t2 = tick2; tick2 = 0; interrupts();

  double rpm1_raw = ((double)t1 / dt) * 60.0 / ((double)resolution * (double)rapport_reducteur);
  double rpm2_raw = ((double)t2 / dt) * 60.0 / ((double)resolution * (double)rapport_reducteur);

  double alpha_dyn = (abs(rpm1_raw) < 5 || abs(rpm2_raw) < 5) ? 0.15 : 0.30;
  rpm1_filtered = (alpha_dyn * rpm1_raw) + ((1.0 - alpha_dyn) * rpm1_filtered);
  rpm2_filtered = (alpha_dyn * rpm2_raw) + ((1.0 - alpha_dyn) * rpm2_filtered);

  // RAMPES
  if (abs(target_V) > abs(current_V)) {
      if (current_V < target_V) current_V += accel_V_step;
      else current_V -= accel_V_step;
  } else {
      if (current_V < target_V) current_V += decel_V_step;
      else current_V -= decel_V_step;
  }
  if (abs(current_V - target_V) < decel_V_step) current_V = target_V;

  if (current_W < target_W) current_W += accel_W_step;
  else if (current_W > target_W) current_W -= accel_W_step;
  if (abs(current_W - target_W) < accel_W_step) current_W = target_W;

  // BOUCLE W EXTERNE
  double v_g_mes = (rpm1_filtered * 2.0 * PI * RAYON_ROUE) / 60.0;
  double v_d_mes = (rpm2_filtered * 2.0 * PI * RAYON_ROUE) / 60.0;
  double w_mesure = (v_d_mes - v_g_mes) / ENTRAXE;

  double w_corrected = current_W;
  if (abs(current_V) > 0.02 || abs(current_W) > 0.02) {
    double w_err = current_W - w_mesure;
    w_err_sum += w_err * dt;
    w_err_sum = constrain(w_err_sum, -0.5, 0.5);
    w_corrected = current_W + Kp_w * w_err + Ki_w * w_err_sum;
  } else {
    w_err_sum = 0;
  }

  // CINEMATIQUE INVERSE
  double v_roue_gauche = current_V - (w_corrected * ENTRAXE / 2.0);
  double v_roue_droite = current_V + (w_corrected * ENTRAXE / 2.0);
  double setpointRPM1 = (v_roue_gauche * 60.0) / (2.0 * PI * RAYON_ROUE);
  double setpointRPM2 = (v_roue_droite * 60.0) / (2.0 * PI * RAYON_ROUE);

  bool slip1 = abs(rpm1_filtered - setpointRPM1) > SLIP_THRESHOLD;
  bool slip2 = abs(rpm2_filtered - setpointRPM2) > SLIP_THRESHOLD;

  // PID MOTEUR 1
  double output1 = 0;
  if (target_V == 0 && target_W == 0 && abs(rpm1_filtered) < 1.0) {
     errorSum1 = 0; output1 = 0;
  } else {
     double error1 = setpointRPM1 - rpm1_filtered;
     errorSum1 += error1 * dt;
     errorSum1 = constrain(errorSum1, -50.0, 50.0); 
     if (slip1) errorSum1 *= 0.5;
     output1 = (Kp * error1) + (Ki * errorSum1) + (Kd * (error1 - lastError1)/dt) + (Kf * setpointRPM1);
     lastError1 = error1;
     if (slip1) output1 *= 0.6;
  }

  // PID MOTEUR 2
  double output2 = 0;
  if (target_V == 0 && target_W == 0 && abs(rpm2_filtered) < 1.0) {
     errorSum2 = 0; output2 = 0;
  } else {
     double error2 = setpointRPM2 - rpm2_filtered;
     errorSum2 += error2 * dt;
     errorSum2 = constrain(errorSum2, -50.0, 50.0); 
     if (slip2) errorSum2 *= 0.5;
     output2 = (Kp * error2) + (Ki * errorSum2) + (Kd * (error2 - lastError2)/dt) + (Kf * setpointRPM2);
     lastError2 = error2;
     if (slip2) output2 *= 0.6;
  }

  setMotorPWM((int)output1, M1_PWM, M1_DIR);
  setMotorPWM((int)output2, M2_PWM, M2_DIR);

  // AFFICHAGE
  plotCounter++;
  if (plotCounter >= 10) {
    plotCounter = 0;
    int pBat = calculerPourcentage(vBatCurrent);
    double avgRPM = (rpm1_filtered + rpm2_filtered) / 2.0;
    double measured_V = (avgRPM * 2.0 * PI * RAYON_ROUE) / 60.0;

    Serial.print("RPM:"); Serial.print(avgRPM); 
    Serial.print(",Speed:"); Serial.print(measured_V, 4); 
    Serial.print(",W_cmd:"); Serial.print(current_W, 3);
    Serial.print(",W_mes:"); Serial.print(w_mesure, 3);
    Serial.print(",W_cor:"); Serial.print(w_corrected, 3);
    Serial.print(",Volt:"); Serial.print(vBatCurrent, 2);
    Serial.print(",Bat%:"); Serial.println(pBat);
  }
}

void parseCommand(String line) {
  line.toUpperCase();
  if (line.startsWith("S")) { target_V = line.substring(1).toFloat(); target_W = 0; }
  if (line.startsWith("T")) { target_W = line.substring(1).toFloat(); target_V = 0; }
  if (line.startsWith("M")) {
      int separator = line.indexOf(':');
      if (separator != -1) {
        target_V = line.substring(1, separator).toFloat();
        target_W = line.substring(separator+1).toFloat();
      }
  }
  if (line == "STOP") {
    relay_active = true;
    target_V = 0; target_W = 0;
    current_V = 0; current_W = 0;
    digitalWrite(PIN_RELAY, HIGH);
    Serial.println("RELAIS FERME - MOUVEMENT BLOQUE");
  }
  if (line == "RESUME") {
    relay_active = false;
    digitalWrite(PIN_RELAY, LOW);
    Serial.println("RELAIS OUVERT - MOUVEMENT AUTORISE");
  }
}

void readCommands() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0) parseCommand(line);
  }
}

void setup() {
  Serial.begin(57600);
  pinMode(M1_PWM, OUTPUT); pinMode(M1_DIR, OUTPUT);
  pinMode(M2_PWM, OUTPUT); pinMode(M2_DIR, OUTPUT);
  pinMode(PIN_BATTERIE, INPUT);
  pinMode(PIN_RELAY, OUTPUT);
  digitalWrite(PIN_RELAY, LOW);
  pinMode(ENC1_A, INPUT_PULLUP); pinMode(ENC1_B, INPUT_PULLUP);
  pinMode(ENC2_A, INPUT_PULLUP); pinMode(ENC2_B, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENC1_A), ISR_Enc1A, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC1_B), ISR_Enc1B, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC2_A), ISR_Enc2A, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC2_B), ISR_Enc2B, CHANGE);
  
  timer.setInterval(1000 / fe, boucle_controle);
  Serial.println("ROBOT PRET - Sans kick-start");
}

void loop() { timer.run(); readCommands(); }
