# Flashing the Arduino UNO R4 WiFi (RA4M1) from Raspberry Pi

## Scope and tested configuration

This is the procedure **actually tested on the CognitiveOps rover on 2026-10-29**. It covers compiling and flashing the `ra4m1_rover_controller` sketch directly from the Raspberry Pi without using a laptop.

| Item | Tested configuration |
| --- | --- |
| Raspberry Pi OS | Raspbian Bookworm **32-bit (armhf userspace)** on an aarch64-capable CPU |
| `getconf LONG_BIT` / `uname -m` | `32` / `aarch64` |
| Project | `~/CognitiveOps` |
| Board | Arduino UNO R4 WiFi, Renesas RA4M1 |
| Board FQBN | `arduino:renesas_uno:unor4wifi` |
| Arduino CLI | `~/.local/bin/arduino-cli` (1.5.1) |
| Renesas platform | `arduino:renesas_uno@1.6.0` |
| Cross-compiler | Raspbian `gcc-arm-none-eabi`, GCC 12.2.1 at `/usr/bin/` |
| Servo library | Arduino Servo 1.3.0 |
| Upload port | `/dev/ttyACM0` in the tested setup (confirm each time) |
| USB by-id | `/dev/serial/by-id/usb-Arduino_UNO_WiFi_R4_CMSIS-DAP_3CDC7544B664-if01` |
| BOSSA source | `https://github.com/arduino/BOSSA.git`, branch `unor4wifi`, tested commit `91c7b0e` |
| BOSSA executable | `~/arduino-tools/BOSSA/bin/bossac` (compiled locally for armhf) |

**Safety:** Keep ESC and motors **unpowered** when compiling, flashing, resetting, and validating the controller. Stop CognitiveOps and close any other process using the serial port. The experimental firmware interprets a missing HC-SR04 echo (`-1`) as clear; this **cannot distinguish a clear path from a failed ultrasonic sensor**.

## 1. Install Arduino CLI and board support (one time)

```bash
mkdir -p "$HOME/.local/bin"
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh \
  | BINDIR="$HOME/.local/bin" sh
~/.local/bin/arduino-cli version

~/.local/bin/arduino-cli core update-index
~/.local/bin/arduino-cli core install arduino:renesas_uno
~/.local/bin/arduino-cli lib install "Servo"
```

**ARM32 caveat:** Arduino's package resolver downloaded several **ARM64 executables** even though this Raspberry runs a 32-bit userspace. Errors such as `fork/exec ...: no such file or directory` can therefore mean an **incompatible binary/interpreter**, not a missing file.

## 2. Install ARM32 compiler and ctags (one time)

```bash
sudo apt update
sudo apt install gcc-arm-none-eabi arduino-ctags
/usr/bin/arm-none-eabi-g++ --version
/usr/bin/arduino-ctags --version
```

The build property `compiler.path=/usr/bin/` selects the working armhf cross-compiler instead of the Arduino package's non-running ARM64 compiler.

Arduino CLI also downloaded an incompatible `ctags`. In the tested installation, it was replaced with a symlink to Raspbian's compatible binary **after backing up the original**:

```bash
CTAGS_DIR="$HOME/.arduino15/packages/builtin/tools/ctags/5.8-arduino11"
mv "$CTAGS_DIR/ctags" "$CTAGS_DIR/ctags.original"
ln -s /usr/bin/arduino-ctags "$CTAGS_DIR/ctags"
```

These package-path substitutions are installation-specific and may need to be reapplied after an Arduino CLI tools update.

## 3. Build the Arduino-specific BOSSA for ARM32 (one time)

The generic Raspbian `bossa-cli` and Arduino's older downloaded `arduino2` ARM32 binary both ran but initially reported `No device found`. We built the Arduino `unor4wifi` branch locally instead:

```bash
mkdir -p ~/arduino-tools
cd ~/arduino-tools
git clone https://github.com/arduino/BOSSA.git
cd BOSSA
git switch -c unor4wifi origin/unor4wifi
# Reproduce the tested source revision:
git checkout 91c7b0e
make bossac
file bin/bossac
bin/bossac --help | head -5
```

Expected: a **32-bit ARM EABI5** executable at `~/arduino-tools/BOSSA/bin/bossac`.

A `make: wx-config: No such file or directory` warning appeared in our build, but the `bossac` CLI still linked successfully. We did **not** need the graphical BOSSA application.

## 4. Compile the CognitiveOps RA4M1 sketch

Make sure the Raspberry has the intended firmware revision:

```bash
cd ~/CognitiveOps
git pull --ff-only origin feature/hc-sr04-front-safety
grep -n -A7 'if (echoUs == 0)' ra4m1_rover_controller/ra4m1_rover_controller.ino
```

In the tested experimental firmware, this section includes `frontDistanceCm = -1.0f;`, `frontSensorStatus = "CLEAR";` and `frontBlocked = false;`.

Build an explicit `.bin` output:

```bash
~/.local/bin/arduino-cli compile \
  --fqbn arduino:renesas_uno:unor4wifi \
  --build-property compiler.path=/usr/bin/ \
  --output-dir /tmp/cognitiveops-ra4m1 \
  ra4m1_rover_controller
```

Expected binary:

```text
/tmp/cognitiveops-ra4m1/ra4m1_rover_controller.ino.bin
```

The successful test build reported **65,724 bytes (25%) Flash** and **7,188 bytes (21%) RAM**. These values can change as firmware evolves.

## 5. Flash using a 1200-baud touch followed by BOSSA

First, confirm which serial device is connected:

```bash
ls -l /dev/serial/by-id/
ls -l /dev/ttyACM*
```

**Crucial finding:** Calling `bossac` directly returned `No device found on ttyACM0`, **even after experimenting with a double RESET**. Opening and closing the serial port at **1200 baud immediately before BOSSA** successfully activated the bootloader.

With ESC/motors unpowered and all serial clients stopped:

```bash
python3 - <<'PY'
import serial
import time
with serial.Serial('/dev/ttyACM0', 1200, timeout=1):
    pass
time.sleep(2)
PY

~/arduino-tools/BOSSA/bin/bossac \
  --port=ttyACM0 \
  -U -e -w -v \
  /tmp/cognitiveops-ra4m1/ra4m1_rover_controller.ino.bin \
  -R
```

**Do not blindly retry after an error.** This command erases/writes MCU flash. In our run, BOSSA reported:

```text
Erase flash
Done in 0.001 seconds
Write 65732 bytes to flash (17 pages)
[==============================] 100% (17/17 pages)
Done in 4.222 seconds
Verify 65732 bytes of flash
SAM-BA operation failed
```

This **was not a successful verification**. The Arduino initially failed to answer application commands. After **disconnecting USB power, waiting about 10 seconds and reconnecting**, it answered `PING` and exposed both new protocol commands. This shows the updated firmware was running, but **does not prove the flash contents passed an independent byte-for-byte verification**. Treat the BOSSA verification failure as an unresolved issue; investigate before relying on this workflow for unattended or safety-critical updates.

For a **non-writing** bootloader communication test, first do the 1200-baud touch above, then:

```bash
~/arduino-tools/BOSSA/bin/bossac -d --port=ttyACM0 -U -i
```

In our test this reported `Arduino Bootloader (SAM-BA extended) 2.0` and an `nRF52840-QIAA` device identifier. This is the bootloader's identification response, not proof that the rover application runs on the nRF52840; the sketch targets the UNO R4 WiFi RA4M1.

## 6. Verify the running sketch over USB serial

If the application doesn't answer after flashing, **do not flash again immediately**. First power-cycle the board via USB with motors and ESC unpowered, allow USB to re-enumerate, and confirm the actual serial device.

```bash
python3 - <<'PY'
import serial
import time

with serial.Serial('/dev/ttyACM0', 115200, timeout=2) as ser:
    time.sleep(2)
    ser.reset_input_buffer()
    for cmd in ('PING', 'GET_DISTANCE', 'GET_ECHO'):
        ser.write((cmd + '\n').encode())
        ser.flush()
        print(cmd, '->', ser.readline().decode(errors='replace').strip())
PY
```

**Actual successful test output (2026-10-29):**

```text
PING -> PONG
GET_DISTANCE -> DISTANCE_CM=-1.0 BLOCKED=0 SENSOR_STATE=CLEAR
GET_ECHO -> ECHO_LEVEL=1 ECHO_AFTER_PULSE=1 DISTANCE_CM=-1.0 BLOCKED=0
```

The `SENSOR_STATE` field and `GET_ECHO` command distinguish the new firmware from the older version. Previously, the board answered `DISTANCE_CM=-1.0 BLOCKED=1` and `ERR UNKNOWN_CMD GET_ECHO`.

**Diagnostic observation:** `ECHO_LEVEL=1` and `ECHO_AFTER_PULSE=1` suggest the ultrasonic ECHO line was HIGH at those sampled moments. They do not alone establish why it is HIGH or prove a sensor failure.

## 7. Known limitations and troubleshooting

- **`dfu-discovery ... no such file or directory`** from `arduino-cli board list`: on this ARM32 userspace, the Arduino-downloaded discovery executable is incompatible. Serial discovery still identified `/dev/ttyACM0`; this warning did not stop the tested manual BOSSA flow.
- **`arm-none-eabi-g++ ... no such file or directory`**: use the installed Raspbian ARM32 cross-compiler via `--build-property compiler.path=/usr/bin/`.
- **`Servo.h: No such file or directory`**: `arduino-cli lib install "Servo"`.
- **`ctags ... no such file or directory`**: use the backed-up executable/symlink procedure in section 2.
- **`No device found on ttyACM0`**: check the port, ensure the port isn't in use, then use the **1200-baud touch** immediately before the compatible `bossac`.
- **`SAM-BA operation failed` during verification**: upload result is **indeterminate**, even if the write progress reached 100%. Do not treat this as fully verified. Recover/reflash with a known-good method if the application fails to start.
- **`PING` yields no reply**: disconnect/reconnect USB once, re-check port, and retry the serial test before contemplating another flash.
- **Firmware appears old despite a successful upload**: check the exact `.ino` path and local Git changes. An earlier laptop session had a locally modified sketch missing `GET_ECHO` and `frontSensorStatus`, despite Git HEAD pointing at the correct commit.

## Safety and architecture notes

The RA4M1 locally drives steering/ESC PWM and enforces front-distance thresholds. The experimental firmware treats `echoUs == 0` as **`DISTANCE_CM=-1.0 BLOCKED=0 SENSOR_STATE=CLEAR`**. This is a deliberately non-fail-safe choice: **missing echo does not establish obstacle-free space**. Valid close readings still trigger the configured threshold/hysteresis behavior. Independently, the CognitiveOps navigation planner issues `HOLD` when there is no valid GPS position.

This document records **what worked and what remains uncertain**, rather than promising a universally reliable flashing procedure.
