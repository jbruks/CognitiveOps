#include <Servo.h>

// ===== Pin config =====
static const int STEERING_PIN = 9;
static const int THROTTLE_PIN = 10;

// ===== RC pulse config =====
static const int PWM_CENTER = 1500;
static const int PWM_STEER_LEFT = 1300;
static const int PWM_STEER_RIGHT = 1700;
static const int PWM_THROTTLE_FORWARD = 1600;

// ===== Timing config =====
static const unsigned long FAILSAFE_TIMEOUT_MS = 50000;
static const unsigned long ACTION_FORWARD_MS = 5000;
static const unsigned long ACTION_TURN_MS = 220;
static const unsigned long BOOT_NEUTRAL_MS = 3000;

Servo steeringServo;
Servo throttleServo;

bool armed = false;
bool actionActive = false;
unsigned long lastCommandMs = 0;
unsigned long actionEndMs = 0;

int currentSteerUs = PWM_CENTER;
int currentThrottleUs = PWM_CENTER;
String currentMode = "STANDBY";
String lastAction = "NONE";

void applyOutputs(int steerUs, int throttleUs) {
  currentSteerUs = constrain(steerUs, 1000, 2000);
  currentThrottleUs = constrain(throttleUs, 1000, 2000);
  steeringServo.writeMicroseconds(currentSteerUs);
  throttleServo.writeMicroseconds(currentThrottleUs);
}

void neutralOutputs() {
  applyOutputs(PWM_CENTER, PWM_CENTER);
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

  applyOutputs(steerUs, throttleUs);
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
    startTimedAction(PWM_CENTER, PWM_THROTTLE_FORWARD, ACTION_FORWARD_MS, "MOVE_FORWARD");
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
  neutralOutputs();
  delay(BOOT_NEUTRAL_MS);
  lastCommandMs = millis();
}

void loop() {
  serviceSerial();
  serviceTimedAction();
  serviceFailsafe();
}
