#include <Servo.h>

// ===== Pin config =====
static const int STEERING_PIN = 9;
static const int THROTTLE_PIN = 10;

// ===== RC pulse config =====
static const int PWM_CENTER = 1500;

static const int PWM_CENTER_STEER = 1450;

static const int PWM_STEER_LEFT = 1200;
static const int PWM_STEER_RIGHT = 1700;
static const int PWM_THROTTLE_FORWARD = 1580;
static const int PWM_THROTTLE_BACKWARD = 1450;

// ===== Timing config =====
static const unsigned long FAILSAFE_TIMEOUT_MS = 5000;
static const unsigned long ACTION_FORWARD_MS = 3000;
static const unsigned long ACTION_BACKWARD_MS = 3000;
static const unsigned long ACTION_TURN_MS = 200;
static const unsigned long BOOT_NEUTRAL_MS = 3000;

Servo steeringServo;
Servo throttleServo;

bool armed = false;
bool actionActive = false;
unsigned long lastCommandMs = 0;
unsigned long actionEndMs = 0;

unsigned long lastRampUpdate = 0;
const int RAMP_INTERVAL_MS = 10;  // prueba 10–20

int currentSteerUs = PWM_CENTER_STEER;
int currentThrottleUs = PWM_CENTER;
String currentMode = "STANDBY";
String lastAction = "NONE";

int targetSteerUs = PWM_CENTER_STEER;
int targetThrottleUs = PWM_CENTER;

void setTargets(int steerUs, int throttleUs) {
  targetSteerUs = constrain(steerUs, 1000, 2000);
  targetThrottleUs = constrain(throttleUs, 1000, 2000);
}

void applyOutputs(int steerUs, int throttleUs) {
  currentSteerUs = constrain(steerUs, 1000, 2000);
  currentThrottleUs = constrain(throttleUs, 1000, 2000);
  steeringServo.writeMicroseconds(currentSteerUs);
  throttleServo.writeMicroseconds(currentThrottleUs);
}

void neutralOutputs() {
  //applyOutputs(PWM_CENTER, PWM_CENTER);
  setTargets(PWM_CENTER_STEER, PWM_CENTER);
}

void updateRampold01() {

  const int STEP = 1;  // ajustable (2–5 ideal)
  
  // THROTTLE
  int deltaT = targetThrottleUs - currentThrottleUs;
  if (deltaT > STEP) currentThrottleUs += STEP;
  else if (deltaT < -STEP) currentThrottleUs -= STEP;
  else currentThrottleUs = targetThrottleUs;

  // STEERING
  int deltaS = targetSteerUs - currentSteerUs;
  if (deltaS > STEP) currentSteerUs += STEP;
  else if (deltaS < -STEP) currentSteerUs -= STEP;
  else currentSteerUs = targetSteerUs;
}

void updateRamp02() {

  const int STEP = 1;  // ajustable
  
  // THROTTLE
  int deltaT = targetThrottleUs - currentThrottleUs;
  if (deltaT > STEP) currentThrottleUs += STEP;
  else if (deltaT < -STEP) currentThrottleUs -= STEP;
  else currentThrottleUs = targetThrottleUs;

  // STEERING
  // int deltaS = targetSteerUs - currentSteerUs;
  // if (deltaS > STEP) currentSteerUs += STEP;
  // else if (deltaS < -STEP) currentSteerUs -= STEP;
  // else currentSteerUs = targetSteerUs;
  currentSteerUs = targetSteerUs;
}

void updateRamp() {

  if (millis() - lastRampUpdate < RAMP_INTERVAL_MS) return;
  lastRampUpdate = millis();

  const int STEP = 2;

  // THROTTLE
  int deltaT = targetThrottleUs - currentThrottleUs;
  if (deltaT > STEP) currentThrottleUs += STEP;
  else if (deltaT < -STEP) currentThrottleUs -= STEP;
  else currentThrottleUs = targetThrottleUs;

  // STEERING
  // int deltaS = targetSteerUs - currentSteerUs;
  // if (deltaS > STEP) currentSteerUs += STEP;
  // else if (deltaS < -STEP) currentSteerUs -= STEP;
  // else currentSteerUs = targetSteerUs;
  currentSteerUs = targetSteerUs;

}

void setFailsafe() {
  actionActive = false;
  currentMode = armed ? "GUIDED" : "STANDBY";
  lastAction = "FAILSAFE";
  neutralOutputs();
}

void startTimedAction(int steerUs, int throttleUs, unsigned long durationMs, const char* actionName) {
  if (!armed) {
    Serial.println("ERR NOT_ARMED");
    return;
  }

  //applyOutputs(steerUs, throttleUs);

  if (strcmp(actionName, "MOVE_BACKWARD") == 0) {
    // Paso 1: neutro
    setTargets(PWM_CENTER_STEER, PWM_CENTER);
    delay(300);

    // Paso 2: marcha atrás
    setTargets(steerUs, throttleUs);
  } else {
    setTargets(steerUs, throttleUs);
  }
  
  actionActive = true;
  actionEndMs = millis() + durationMs;
  currentMode = "GUIDED";
  lastAction = actionName;
  lastCommandMs = millis();
  Serial.print("ACK ");
  Serial.println(actionName);
}

void handleCommand(const String& cmdRaw) {
  String cmd = cmdRaw;
  cmd.trim();
  if (cmd.length() == 0) {
    return;
  }

  lastCommandMs = millis();

  if (cmd == "PING") {
    Serial.println("PONG");
    return;
  }

  if (cmd == "ARM") {
    armed = true;
    currentMode = "GUIDED";
    lastAction = "ARM";
    neutralOutputs();
    Serial.println("ACK ARM");
    return;
  }

  if (cmd == "DISARM") {
    armed = false;
    actionActive = false;
    currentMode = "STANDBY";
    lastAction = "DISARM";
    neutralOutputs();
    Serial.println("ACK DISARM");
    return;
  }

  if (cmd == "STOP") {
    actionActive = false;
    lastAction = "STOP";
    currentMode = armed ? "GUIDED" : "STANDBY";
    neutralOutputs();
    Serial.println("ACK STOP");
    return;
  }

  if (cmd == "HOLD") {
    actionActive = false;
    lastAction = "HOLD";
    currentMode = armed ? "GUIDED" : "STANDBY";
    neutralOutputs();
    Serial.println("ACK HOLD");
    return;
  }

  if (cmd == "MOVE_FORWARD") {
    startTimedAction(PWM_CENTER_STEER, PWM_THROTTLE_FORWARD, ACTION_FORWARD_MS, "MOVE_FORWARD");
    return;
  }

  if (cmd == "MOVE_BACKWARD") {
    startTimedAction(PWM_CENTER_STEER, PWM_THROTTLE_BACKWARD, ACTION_BACKWARD_MS, "MOVE_BACKWARD");
    return;
  }

  if (cmd == "TURN_LEFT") {
    startTimedAction(PWM_STEER_LEFT, PWM_CENTER, ACTION_TURN_MS, "TURN_LEFT");
    return;
  }

  if (cmd == "TURN_RIGHT") {
    startTimedAction(PWM_STEER_RIGHT, PWM_CENTER, ACTION_TURN_MS, "TURN_RIGHT");
    return;
  }

  if (cmd == "FORWARD_LEFT") {
    startTimedAction(PWM_STEER_LEFT, PWM_THROTTLE_FORWARD, ACTION_FORWARD_MS, "FORWARD_LEFT");
    return;
  }

  if (cmd == "FORWARD_RIGHT") {
    startTimedAction(PWM_STEER_RIGHT, PWM_THROTTLE_FORWARD, ACTION_FORWARD_MS, "FORWARD_RIGHT");
    return;
  }
  

  if (cmd == "GET_STATE") {
    Serial.print("STATE armed=");
    Serial.print(armed ? 1 : 0);
    Serial.print(" mode=");
    Serial.print(currentMode);
    Serial.print(" speed_m_s=");
    Serial.print(currentThrottleUs == PWM_CENTER ? 0 : 0.1);
    Serial.print(" heading_deg=0 x=0 y=0 ");
    Serial.print(" steer_us=");
    Serial.print(currentSteerUs);
    Serial.print(" throttle_us=");
    Serial.print(currentThrottleUs);
    Serial.print(" last_action=");
    Serial.println(lastAction);
    return;
  }

 
  Serial.print("ERR UNKNOWN_CMD ");
  Serial.println(cmd);
}

void serviceSerial() {
  static String line;
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (line.length() > 0) {
        handleCommand(line);
        line = "";
      }
    } else {
      line += c;
      if (line.length() > 80) {
        line = "";
        Serial.println("ERR LINE_TOO_LONG");
      }
    }
  }
}

void serviceTimedAction() {
  if (actionActive && millis() >= actionEndMs) {
    actionActive = false;
    neutralOutputs();
  }
}

void serviceFailsafe() {
  if (!armed) {
    return;
  }
  if (millis() - lastCommandMs > FAILSAFE_TIMEOUT_MS) {
    setFailsafe();
  }
}

void setup() {
    Serial.begin(115200);

    steeringServo.attach(STEERING_PIN);
    throttleServo.attach(THROTTLE_PIN);

    // Inicializar valores
    currentThrottleUs = PWM_CENTER;
    currentSteerUs = PWM_CENTER_STEER;;

    targetThrottleUs = PWM_CENTER;
    targetSteerUs = PWM_CENTER_STEER;;

    // 🔥 FORZAR neutro varias veces
    for (int i = 0; i < 20; i++) {
        throttleServo.writeMicroseconds(PWM_CENTER);
        steeringServo.writeMicroseconds(PWM_CENTER_STEER);
        delay(20);
    }

   

    Serial.println("READY");
}

void setup_old_01() {
  Serial.begin(115200);
  steeringServo.attach(STEERING_PIN);
  throttleServo.attach(THROTTLE_PIN);
  neutralOutputs();
  delay(BOOT_NEUTRAL_MS);
  lastCommandMs = millis();
}

void loop() {
  serviceSerial();
  serviceTimedAction();
  serviceFailsafe();

  updateRamp();
  applyOutputs(currentSteerUs, currentThrottleUs);
}
