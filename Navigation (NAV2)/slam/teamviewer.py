#!/usr/bin/env python3
"""
Robot Keyboard Controller
=========================
Controls the robot via serial commands matching the Arduino protocol:
  S<value>  → set linear speed (m/s)
  T<value>  → set angular speed (rad/s)
  M<v>:<w>  → set both simultaneously

Keys:
  W / ↑        → increase speed
  S / ↓        → decrease speed
  A / ←        → turn left
  D / →        → turn right
  SPACE        → emergency stop
  Q            → quit

  + / -        → adjust speed increment
  [ / ]        → adjust turn increment

Usage:
  python3 robot_control.py              # auto-detect port
  python3 robot_control.py /dev/ttyUSB0 # specify port
"""

import sys
import time
import glob
import threading
import termios
import tty
import select
import serial


# ── Configuration ──────────────────────────────────────────────
BAUD_RATE = 57600
SPEED_STEP = 0.05      # m/s per keypress
TURN_STEP = 0.15       # rad/s per keypress
MAX_SPEED = 1.0        # m/s
MAX_TURN = 3.0         # rad/s
SERIAL_TIMEOUT = 0.1


# ── Terminal raw-mode key reading ──────────────────────────────
class RawInput:
    """Read single keypresses without blocking, no curses needed."""

    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)

    def __enter__(self):
        tty.setraw(self.fd)
        return self

    def __exit__(self, *args):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)

    def get_key(self, timeout=0.05):
        """Return a key string or None if nothing pressed."""
        if select.select([sys.stdin], [], [], timeout)[0]:
            ch = sys.stdin.read(1)
            if ch == '\x1b':  # escape sequence (arrow keys)
                if select.select([sys.stdin], [], [], 0.02)[0]:
                    ch += sys.stdin.read(1)
                    if select.select([sys.stdin], [], [], 0.02)[0]:
                        ch += sys.stdin.read(1)
            return ch
        return None


# ── Serial helpers ─────────────────────────────────────────────
def find_serial_port():
    """Auto-detect the most likely serial port."""
    patterns = ['/dev/ttyUSB*', '/dev/ttyACM*', '/dev/ttyAMA*']
    ports = []
    for p in patterns:
        ports.extend(glob.glob(p))
    if not ports:
        return None
    return sorted(ports)[0]


def serial_reader(ser, running_flag):
    """Background thread: print lines from the robot."""
    while running_flag.is_set():
        try:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    # Move to column 0, clear line, print telemetry, then redraw prompt
                    sys.stdout.write(f"\r\033[K  📡 {line}\n")
                    sys.stdout.flush()
        except Exception:
            break
        time.sleep(0.02)


# ── Display ────────────────────────────────────────────────────
CLEAR = "\033[2J\033[H"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def draw_hud(speed, turn, speed_step, turn_step, port):
    """Draw a compact heads-up display."""
    bar_len = 20
    # Speed bar
    s_ratio = speed / MAX_SPEED
    s_filled = int(abs(s_ratio) * bar_len)
    if speed >= 0:
        s_bar = '▓' * s_filled + '░' * (bar_len - s_filled)
    else:
        s_bar = '░' * (bar_len - s_filled) + '▓' * s_filled

    # Turn bar (center = straight)
    t_ratio = turn / MAX_TURN
    t_mid = bar_len // 2
    t_offset = int(t_ratio * t_mid)
    t_chars = list('░' * bar_len)
    t_chars[t_mid] = '│'
    if t_offset > 0:
        for i in range(t_mid + 1, min(t_mid + 1 + t_offset, bar_len)):
            t_chars[i] = '▓'
    elif t_offset < 0:
        for i in range(max(t_mid + t_offset, 0), t_mid):
            t_chars[i] = '▓'
    t_bar = ''.join(t_chars)

    direction = "FORWARD" if speed > 0 else "REVERSE" if speed < 0 else "STOPPED"
    steering = "LEFT" if turn < 0 else "RIGHT" if turn > 0 else "STRAIGHT"
    color = GREEN if speed != 0 or turn != 0 else YELLOW

    sys.stdout.write(f"\r\033[8A")  # move up 8 lines
    lines = [
        f"  {BOLD}{CYAN}═══ ROBOT CONTROLLER ═══{RESET}  [{port}]",
        f"",
        f"  {color}Speed: {speed:+.2f} m/s{RESET}  ({direction})   step: {speed_step:.2f}",
        f"  [{s_bar}]",
        f"  {color}Turn:  {turn:+.2f} rad/s{RESET} ({steering})   step: {turn_step:.2f}",
        f"  [{t_bar}]",
        f"",
        f"  {YELLOW}W/S{RESET}=speed  {YELLOW}A/D{RESET}=turn  {RED}SPACE{RESET}=stop  {YELLOW}+/-{RESET}=step  {YELLOW}Q{RESET}=quit",
    ]
    for l in lines:
        sys.stdout.write(f"\033[K{l}\n")
    sys.stdout.flush()


# ── Main ───────────────────────────────────────────────────────
def main():
    # Determine port
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = find_serial_port()
        if port is None:
            print(f"{RED}No serial port found. Plug in the Arduino or specify the port:{RESET}")
            print(f"  python3 {sys.argv[0]} /dev/ttyUSB0")
            sys.exit(1)

    print(f"{CYAN}Connecting to {port} at {BAUD_RATE} baud...{RESET}")
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=SERIAL_TIMEOUT)
    except serial.SerialException as e:
        print(f"{RED}Could not open {port}: {e}{RESET}")
        sys.exit(1)

    time.sleep(2)  # wait for Arduino reset after serial connect
    ser.reset_input_buffer()

    speed = 0.0
    turn = 0.0
    speed_step = SPEED_STEP
    turn_step = TURN_STEP

    running = threading.Event()
    running.set()
    reader_thread = threading.Thread(target=serial_reader, args=(ser, running), daemon=True)
    reader_thread.start()

    # Initial screen
    sys.stdout.write(CLEAR)
    print("\n" * 8)  # reserve space for HUD
    draw_hud(speed, turn, speed_step, turn_step, port)

    def send_command():
        """Send the current speed/turn to the robot."""
        if speed != 0 and turn != 0:
            cmd = f"M{speed:.3f}:{turn:.3f}\n"
        elif turn != 0:
            cmd = f"T{turn:.3f}\n"
        else:
            cmd = f"S{speed:.3f}\n"
        ser.write(cmd.encode())

    try:
        with RawInput() as raw:
            while True:
                key = raw.get_key()
                if key is None:
                    continue

                changed = False

                # Quit
                if key in ('q', 'Q', '\x03'):  # q or Ctrl-C
                    break

                # Forward / backward
                elif key in ('w', 'W', '\x1b[A'):  # w or Up arrow
                    speed = min(speed + speed_step, MAX_SPEED)
                    changed = True
                elif key in ('s', 'S', '\x1b[B'):  # s or Down arrow
                    speed = max(speed - speed_step, -MAX_SPEED)
                    changed = True

                # Turn left / right
                elif key in ('a', 'A', '\x1b[D'):  # a or Left arrow
                    turn = max(turn - turn_step, -MAX_TURN)
                    changed = True
                elif key in ('d', 'D', '\x1b[C'):  # d or Right arrow
                    turn = min(turn + turn_step, MAX_TURN)
                    changed = True

                # Emergency stop
                elif key == ' ':
                    speed = 0.0
                    turn = 0.0
                    changed = True

                # Adjust increments
                elif key in ('+', '='):
                    speed_step = min(speed_step + 0.01, 0.5)
                    changed = True
                elif key in ('-', '_'):
                    speed_step = max(speed_step - 0.01, 0.01)
                    changed = True
                elif key == ']':
                    turn_step = min(turn_step + 0.05, 1.0)
                    changed = True
                elif key == '[':
                    turn_step = max(turn_step - 0.05, 0.05)
                    changed = True

                # Round near-zero to zero
                if abs(speed) < 0.001:
                    speed = 0.0
                if abs(turn) < 0.001:
                    turn = 0.0

                if changed:
                    send_command()
                    draw_hud(speed, turn, speed_step, turn_step, port)

    except KeyboardInterrupt:
        pass
    finally:
        # Stop the robot before exiting
        ser.write(b"S0\n")
        time.sleep(0.1)
        running.clear()
        ser.close()
        # Restore terminal
        sys.stdout.write(f"\n{GREEN}Robot stopped. Connection closed.{RESET}\n")


if __name__ == "__main__":
    main()