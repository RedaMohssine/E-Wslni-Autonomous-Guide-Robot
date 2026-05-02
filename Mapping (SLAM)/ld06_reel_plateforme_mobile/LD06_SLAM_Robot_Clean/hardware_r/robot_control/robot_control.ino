#include <Servo.h>


// === Enhanced Robot Control with Servo Steering ===
// Motor control + Encoder reading + Servo steering + ROS2 command interface

// --- Pin Definitions ---
const int ENCA = 2;           // Encoder channel A (interrupt)
const int ENCB = 3;           // Encoder channel B
const int MOTOR_PWM = 6;      // PWM pin for motor speed
const int MOTOR_DIR = 7;      // Motor direction pin
const int SERVO_PIN = 8;      // Servo motor pin

// --- Robot Parameters ---
const int pulsesPerRevolution = 360;  // Encoder ticks per revolution
const float wheelDiameter = 0.065;    // Wheel diameter [m]
const float wheelBase = 0.15;         // Distance between wheels [m]

// --- Servo Parameters ---
const int SERVO_CENTER = 90;          // Center position (straight)
const int SERVO_MAX_LEFT = 135;       // Maximum left turn (was 45, swapped because servo mounted backwards)
const int SERVO_MAX_RIGHT = 45;       // Maximum right turn (was 135, swapped because servo mounted backwards)

// --- Variables ---
volatile long encoderCount = 0;
unsigned long lastTime = 0;
float rpm = 0.0;
float linearSpeed = 0.0;
float steeringAngle = 0.0;            // Current steering angle in degrees

// Target commands (from serial/ROS)
float targetSpeed = 0.0;              // Target linear speed [m/s]
float targetSteering = 0.0;           // Target steering angle [-1.0 to 1.0]

Servo steeringServo;

void setup() {
  Serial.begin(115200);
  
  // Motor pins
  pinMode(ENCA, INPUT_PULLUP);
  pinMode(ENCB, INPUT_PULLUP);
  pinMode(MOTOR_PWM, OUTPUT);
  pinMode(MOTOR_DIR, OUTPUT);
  
  // Servo setup
  steeringServo.attach(SERVO_PIN);
  steeringServo.write(SERVO_CENTER);
  
  // Encoder interrupt
  attachInterrupt(digitalPinToInterrupt(ENCA), encoderISR, RISING);
  
  // Stop motor initially
  analogWrite(MOTOR_PWM, 0);
  
  Serial.println("Robot control ready!");
  Serial.println("Commands: S<speed> T<steering>");
  Serial.println("Example: S0.2 (0.2 m/s), T0.5 (half right turn)");
}

void loop() {
  // Read serial commands
  readSerialCommands();
  
  // Update motor control
  updateMotorControl();
  
  // Update servo steering
  updateSteering();
  
  // Calculate and publish odometry (10Hz)
  unsigned long now = millis();
  if (now - lastTime >= 100) {
    calculateOdometry();
    publishOdometry();
    lastTime = now;
  }
}

void readSerialCommands() {
  // Read up to 3 commands per loop to avoid blocking
  int commandsRead = 0;
  while (Serial.available() > 0 && commandsRead < 3) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd.length() == 0) continue;  // Skip empty commands
    
    commandsRead++;
    
    // Parse speed command: S<value>
    if (cmd.startsWith("S")) {
      targetSpeed = cmd.substring(1).toFloat();
      targetSpeed = constrain(targetSpeed, -0.5, 0.5); // Limit to ±0.5 m/s
    }
    // Parse steering command: T<value> (-1.0 to 1.0)
    else if (cmd.startsWith("T")) {
      String valueStr = cmd.substring(1);
      targetSteering = valueStr.toFloat();
      targetSteering = constrain(targetSteering, -1.0, 1.0);
      // Debug output
      Serial.print("DEBUG: Received T command, value=");
      Serial.print(valueStr);
      Serial.print(", parsed=");
      Serial.println(targetSteering);
    }
    // Stop command
    else if (cmd == "STOP") {
      targetSpeed = 0.0;
      targetSteering = 0.0;
    }
  }
}

void updateMotorControl() {
  // If steering but not moving, use minimum speed for steering
  float effectiveSpeed = targetSpeed;
  if (abs(targetSpeed) < 0.01 && abs(targetSteering) > 0.1) {
    // Turn in place with slow forward motion
    effectiveSpeed = 0.05;  // Minimum speed for steering
  }
  
  if (abs(effectiveSpeed) < 0.01) {
    // Stop motor
    analogWrite(MOTOR_PWM, 0);
    return;
  }
  
  // Set direction
  if (effectiveSpeed > 0) {
    digitalWrite(MOTOR_DIR, HIGH);  // Forward
  } else {
    digitalWrite(MOTOR_DIR, LOW);   // Backward
  }
  
  // Simple speed control (map 0-0.5 m/s to PWM 0-255)
  int pwm = (int)(abs(effectiveSpeed) / 0.5 * 255);
  pwm = constrain(pwm, 0, 255);
  analogWrite(MOTOR_PWM, pwm);
}

void updateSteering() {
  // Map steering command (-1.0 to 1.0) to servo angle
  // -1.0 = full left, 0.0 = center, 1.0 = full right
  int servoAngle;
  if (targetSteering < 0) {
    // Left turn
    servoAngle = map(targetSteering * 1000, -1000, 0, SERVO_MAX_LEFT, SERVO_CENTER);
  } else {
    // Right turn
    servoAngle = map(targetSteering * 1000, 0, 1000, SERVO_CENTER, SERVO_MAX_RIGHT);
  }
  
  steeringServo.write(servoAngle);
  steeringAngle = targetSteering * 45.0; // Convert to degrees for display
}

void calculateOdometry() {
  noInterrupts();
  long count = encoderCount;
  encoderCount = 0;
  interrupts();
  
  // Calculate RPM
  float revs = (float)count / pulsesPerRevolution;
  rpm = revs * 600.0; // 600 = (60 seconds / 0.1 second interval)
  
  // Calculate linear speed
  linearSpeed = (rpm * 3.1416 * wheelDiameter) / 60.0;
}

void publishOdometry() {
  // Send data in same format as before for compatibility with Arduino bridge
  Serial.print("RPM:");
  Serial.print(rpm, 2);
  Serial.print(",Speed:");
  Serial.print(linearSpeed, 4);
  Serial.print(",Steering:");
  Serial.println(steeringAngle, 2);
}

void encoderISR() {
  int b = digitalRead(ENCB);
  if (b > 0) {
    encoderCount++;
  } else {
    encoderCount--;
  }
}
