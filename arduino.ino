#include <SimpleTimer.h>
#include <Wire.h>
SimpleTimer timer;

// --- MPU-6050 ---
const uint8_t MPU_ADDR = 0x68;
double gyro_bias_x = 0, gyro_bias_y = 0, gyro_bias_z = 0;
double w_gyro_filtered = 0;
double w_gyro_x_filtered = 0, w_gyro_y_filtered = 0;
const double alpha_gyro = 0.25;
bool mpu_ok = false;

// --- DETECTION ANOMALIES ---
double accel_z_baseline = 1.0;
double accel_z_filtered = 1.0;
const double ACCEL_Z_THRESHOLD = 0.08;  // catches 1-2° tilts from floor bumps (was 0.3)
const double DIVERGENCE_THRESHOLD = 0.3;
const int ANOMALY_HOLD_CYCLES = 25;  // ~200ms à 128Hz
int anomaly_counter = 0;
bool anomaly_active = false;

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

// --- PID + FEEDFORWARD ---
double Kp = 4.0; double Ki = 20.0; double Kd = 0.02; double Kf = 2.0;  

// --- BOUCLE W EXTERNE ---
double Kp_w = 0.8;
double Ki_w = 1.5;
double w_err_sum = 0;

// --- DEADBAND / KICK-START ---
const int PWM_DEADBAND = 20;
const int PWM_KICK     = 45;
const double SLIP_THRESHOLD = 30.0;
const double TILT_RATE_THRESHOLD = 0.15;  // rad/s — catches floor bump tilting via gyro X/Y

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

// --- MPU-6050 INIT ---
void mpuInit() {
  // Réveil du capteur
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); Wire.write(0x00);
  Wire.endTransmission(true);
  // DLPF à 44 Hz
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1A); Wire.write(0x03);
  Wire.endTransmission(true);
  // Gyro ±250°/s
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1B); Wire.write(0x00);
  Wire.endTransmission(true);
  // Accel ±2g (par défaut)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C); Wire.write(0x00);
  Wire.endTransmission(true);

  // Vérification WHO_AM_I
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x75); Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)1, (uint8_t)true);
  uint8_t who = Wire.read();
  mpu_ok = (who == 0x68);
  Serial.print("MPU WHO_AM_I=0x"); Serial.print(who, HEX);
  Serial.println(mpu_ok ? " OK" : " FAIL");
}

// --- Lecture gyro XYZ (burst read — roll, pitch, yaw) ---
// X = roll rate, Y = pitch rate → detect floor bump tilting
// Z = yaw rate → used for odometry divergence check
// Turns only affect Z.  Tilts only affect X/Y.  No interference.
void mpuReadGyroXYZ(double &gx, double &gy, double &gz) {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x43);  // GYRO_XOUT_H — burst read all 3 axes (6 bytes)
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)6, (uint8_t)true);
  int16_t rx = (Wire.read() << 8) | Wire.read();
  int16_t ry = (Wire.read() << 8) | Wire.read();
  int16_t rz = (Wire.read() << 8) | Wire.read();
  gx = (rx / 131.0) * PI / 180.0;  // rad/s
  gy = (ry / 131.0) * PI / 180.0;
  gz = (rz / 131.0) * PI / 180.0;
}

// --- Lecture accélération Z ---
double mpuReadAccelZ() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3F);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)2, (uint8_t)true);
  int16_t az = (Wire.read() << 8) | Wire.read();
  return az / 16384.0;  // en g
}

// --- Calibration au démarrage (robot immobile) ---
void calibrateSensors() {
  if (!mpu_ok) return;
  Serial.println("CALIBRATION - Ne pas bouger le robot pendant 2 sec...");
  const int N = 500;
  double sum_gx = 0, sum_gy = 0, sum_gz = 0;
  double sum_a = 0;
  for (int i = 0; i < N; i++) {
    double gx, gy, gz;
    mpuReadGyroXYZ(gx, gy, gz);
    sum_gx += gx; sum_gy += gy; sum_gz += gz;
    sum_a += mpuReadAccelZ();
    delay(4);
  }
  gyro_bias_x = sum_gx / N;
  gyro_bias_y = sum_gy / N;
  gyro_bias_z = sum_gz / N;
  accel_z_baseline = sum_a / N;
  accel_z_filtered = accel_z_baseline;
  Serial.print("Biais gyro X="); Serial.print(gyro_bias_x, 5);
  Serial.print(" Y="); Serial.print(gyro_bias_y, 5);
  Serial.print(" Z="); Serial.print(gyro_bias_z, 5);
  Serial.print(" | Baseline accel Z="); Serial.println(accel_z_baseline, 3);
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

  // === LECTURE IMU ===
  double gx_raw, gy_raw, gz_raw;
  mpuReadGyroXYZ(gx_raw, gy_raw, gz_raw);
  gx_raw -= gyro_bias_x;
  gy_raw -= gyro_bias_y;
  gz_raw -= gyro_bias_z;
  w_gyro_filtered   = alpha_gyro * gz_raw + (1.0 - alpha_gyro) * w_gyro_filtered;
  w_gyro_x_filtered = alpha_gyro * gx_raw + (1.0 - alpha_gyro) * w_gyro_x_filtered;
  w_gyro_y_filtered = alpha_gyro * gy_raw + (1.0 - alpha_gyro) * w_gyro_y_filtered;
  
  double accel_z = mpuReadAccelZ();
  accel_z_filtered = 0.3 * accel_z + 0.7 * accel_z_filtered;
  double accel_deviation = abs(accel_z_filtered - accel_z_baseline);

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

  // BOUCLE W EXTERNE (INCHANGÉE, utilise encodeurs)
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

  // === DETECTION ANOMALIE ===
  double divergence = abs(w_gyro_filtered - w_mesure);
  double tilt_rate = sqrt(w_gyro_x_filtered * w_gyro_x_filtered + w_gyro_y_filtered * w_gyro_y_filtered);
  bool anomaly_now = (accel_deviation > ACCEL_Z_THRESHOLD)
                  || (divergence > DIVERGENCE_THRESHOLD)
                  || (tilt_rate > TILT_RATE_THRESHOLD);
  if (anomaly_now) {
    anomaly_counter = ANOMALY_HOLD_CYCLES;
  }
  if (anomaly_counter > 0) {
    anomaly_counter--;
    anomaly_active = true;
  } else {
    anomaly_active = false;
  }

  // CINEMATIQUE INVERSE (INCHANGÉE)
  double v_roue_gauche = current_V - (w_corrected * ENTRAXE / 2.0);
  double v_roue_droite = current_V + (w_corrected * ENTRAXE / 2.0);
  double setpointRPM1 = (v_roue_gauche * 60.0) / (2.0 * PI * RAYON_ROUE);
  double setpointRPM2 = (v_roue_droite * 60.0) / (2.0 * PI * RAYON_ROUE);

  bool slip1 = abs(rpm1_filtered - setpointRPM1) > SLIP_THRESHOLD;
  bool slip2 = abs(rpm2_filtered - setpointRPM2) > SLIP_THRESHOLD;

  // PID MOTEUR 1 (INCHANGÉ)
  double output1 = 0;
  if (target_V == 0 && target_W == 0 && abs(rpm1_filtered) < 1.0) {
     errorSum1 = 0; output1 = 0;
  } else {
     double error1 = setpointRPM1 - rpm1_filtered;
     errorSum1 += error1 * dt;
     errorSum1 = constrain(errorSum1, -4.0, 4.0); 
     if (slip1) errorSum1 *= 0.5;
     output1 = (Kp * error1) + (Ki * errorSum1) + (Kd * (error1 - lastError1)/dt) + (Kf * setpointRPM1);
     lastError1 = error1;
     if (slip1) output1 *= 0.6;
  }

  // PID MOTEUR 2 (INCHANGÉ)
  double output2 = 0;
  if (target_V == 0 && target_W == 0 && abs(rpm2_filtered) < 1.0) {
     errorSum2 = 0; output2 = 0;
  } else {
     double error2 = setpointRPM2 - rpm2_filtered;
     errorSum2 += error2 * dt;
     errorSum2 = constrain(errorSum2, -4.0, 4.0); 
     if (slip2) errorSum2 *= 0.5;
     output2 = (Kp * error2) + (Ki * errorSum2) + (Kd * (error2 - lastError2)/dt) + (Kf * setpointRPM2);
     lastError2 = error2;
     if (slip2) output2 *= 0.6;
  }

  // Kick-start (INCHANGÉ)
  static int kick_counter1 = 0;
  static int kick_counter2 = 0;
  if (abs(setpointRPM1) > 1.0 && abs(rpm1_filtered) < 2.0 && kick_counter1 < 20) {
    output1 += (setpointRPM1 > 0 ? PWM_KICK : -PWM_KICK);
    kick_counter1++;
  } else if (abs(rpm1_filtered) >= 2.0) kick_counter1 = 0;
  if (abs(setpointRPM2) > 1.0 && abs(rpm2_filtered) < 2.0 && kick_counter2 < 20) {
    output2 += (setpointRPM2 > 0 ? PWM_KICK : -PWM_KICK);
    kick_counter2++;
  } else if (abs(rpm2_filtered) >= 2.0) kick_counter2 = 0;

  setMotorPWM((int)output1, M1_PWM, M1_DIR);
  setMotorPWM((int)output2, M2_PWM, M2_DIR);

  // AFFICHAGE (avec ANOMALY en plus)
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
    Serial.print(",W_gyr:"); Serial.print(w_gyro_filtered, 3);
    Serial.print(",W_cor:"); Serial.print(w_corrected, 3);
    Serial.print(",AccDev:"); Serial.print(accel_deviation, 3);
    Serial.print(",Tilt:"); Serial.print(tilt_rate, 3);
    Serial.print(",ANOMALY:"); Serial.print(anomaly_active ? 1 : 0);
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
  if (line == "RECAL") {
    calibrateSensors();
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
  Wire.begin();
  Wire.setClock(400000);

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

  mpuInit();
  delay(200);
  calibrateSensors();
  
  timer.setInterval(1000 / fe, boucle_controle);
  Serial.println("ROBOT PRET - Detection anomalie IMU active");
}

void loop() { timer.run(); readCommands(); }