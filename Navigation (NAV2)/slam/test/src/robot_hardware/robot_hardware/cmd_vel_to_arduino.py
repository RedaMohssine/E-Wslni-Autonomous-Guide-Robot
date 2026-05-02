#!/usr/bin/env python3
"""
cmd_vel_to_arduino — Bidirectional bridge between ROS2 Nav2 and Arduino.

OUTBOUND (ROS2 → Arduino):
    Subscribes to /cmd_vel (geometry_msgs/Twist)
    Sends: "M<linear_x>:<angular_z>\n"
    The Arduino handles inverse kinematics, PID, ramping.

INBOUND (Arduino → ROS2):
    The Arduino sends telemetry every ~10 control cycles (~78ms) in the format:
      RPM:<avgRPM>,Speed:<V_m/s>,W_cmd:<W>,W_mes:<W_rad/s>,W_gyr:<W>,
      W_cor:<W>,AccDev:<a>,ANOMALY:<0|1>,Volt:<V>,Bat%:<pct>

    This node parses that line and publishes:
      /wheel_velocities  (Float32MultiArray: [linear_V, angular_W])  → encoder_odometry
      /battery_percent   (Int32)
      /anomaly_status    (Int32: 0=ok, 1=anomaly detected)

Safety watchdog: if no /cmd_vel received for timeout period,
sends M0:0 (stop) to the Arduino.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray, Int32
import serial
import time
import threading


class CmdVelToArduino(Node):
    def __init__(self):
        super().__init__('cmd_vel_to_arduino')

        # ── Declare parameters ──
        self.declare_parameter('serial_port', '/dev/ttyACM0')
        self.declare_parameter('baud_rate', 57600)
        self.declare_parameter('cmd_vel_timeout', 0.5)
        self.declare_parameter('publish_rate', 20.0)

        # ── Get parameters ──
        self.serial_port  = self.get_parameter('serial_port').value
        self.baud_rate    = self.get_parameter('baud_rate').value
        self.cmd_vel_timeout = self.get_parameter('cmd_vel_timeout').value
        self.publish_rate = self.get_parameter('publish_rate').value

        # ── State ──
        self.last_cmd_vel_time  = time.time()
        self.current_linear     = 0.0
        self.current_angular    = 0.0
        self.serial_conn        = None
        self.running            = True
        self.serial_lock        = threading.Lock()

        # ── Open serial connection ──
        self._connect_serial()

        # ── Subscribe to /cmd_vel ──
        self.subscription = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, 10)

        # ── Publishers ──
        # [linear_V (m/s),  angular_W (rad/s)] — measured by Arduino encoders
        self.wheel_vel_pub = self.create_publisher(
            Float32MultiArray, '/wheel_velocities', 10)
        self.battery_pub = self.create_publisher(
            Int32, '/battery_percent', 10)
        self.anomaly_pub = self.create_publisher(
            Int32, '/anomaly_status', 10)

        # ── Timer: send commands to Arduino at fixed rate ──
        self.timer = self.create_timer(
            1.0 / self.publish_rate, self.timer_callback)

        # ── Serial reader thread ──
        self.serial_thread = threading.Thread(
            target=self._serial_reader, daemon=True)
        self.serial_thread.start()

        self.get_logger().info(
            f'cmd_vel_to_arduino started:\n'
            f'  Serial: {self.serial_port} @ {self.baud_rate} baud\n'
            f'  Protocol out : M<V>:<W>\\n\n'
            f'  Protocol in  : RPM:...,Speed:...,W_mes:...,Bat%:...\n'
            f'  Timeout: {self.cmd_vel_timeout}s'
        )

    # ──────────────────────────────────────────────────────────
    def _connect_serial(self):
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=0.1
            )
            time.sleep(2.0)   # wait for Arduino reset
            if self.serial_conn.in_waiting:
                self.serial_conn.read(self.serial_conn.in_waiting)
            self.get_logger().info(f'Serial connected: {self.serial_port}')
        except serial.SerialException as e:
            self.get_logger().error(f'Cannot open {self.serial_port}: {e}')
            self.serial_conn = None

    # ──────────────────────────────────────────────────────────
    def _serial_reader(self):
        """Background thread: read and dispatch Arduino serial lines."""
        while self.running:
            if self.serial_conn is None or not self.serial_conn.is_open:
                time.sleep(1.0)
                continue
            try:
                with self.serial_lock:
                    waiting = self.serial_conn.in_waiting
                    if waiting > 0:
                        line = self.serial_conn.readline()\
                                   .decode('utf-8', errors='ignore').strip()
                    else:
                        line = None

                if line is None:
                    time.sleep(0.002)
                    continue

                if line.startswith('RPM:'):
                    self._parse_telemetry(line)
                elif line.startswith('ROBOT') or line.startswith('MPU') or \
                     line.startswith('CALIB') or 'RELAIS' in line or \
                     'PRET' in line or 'biais' in line.lower():
                    self.get_logger().info(f'[ARDUINO] {line}')
                elif 'ALERTE' in line or 'BLOQUE' in line:
                    self.get_logger().error(f'[ARDUINO ALERT] {line}')

            except serial.SerialException as e:
                self.get_logger().warn(f'Serial read error: {e}')
                self.serial_conn = None
                time.sleep(1.0)
            except Exception as e:
                self.get_logger().debug(f'Serial reader error: {e}')
                time.sleep(0.01)

    # ──────────────────────────────────────────────────────────
    def _parse_telemetry(self, line: str):
        """
        Parse the Arduino telemetry line:
          RPM:<avg>,Speed:<V>,W_cmd:<W>,W_mes:<W>,W_gyr:<W>,W_cor:<W>,
          AccDev:<a>,ANOMALY:<0|1>,Volt:<v>,Bat%:<pct>

        Publishes:
          /wheel_velocities  → [Speed (m/s), W_mes (rad/s)]
          /battery_percent   → Bat%
          /anomaly_status    → ANOMALY
        """
        try:
            fields = {}
            for part in line.split(','):
                if ':' in part:
                    k, v = part.split(':', 1)
                    fields[k.strip()] = v.strip()

            # Negate: Arduino "positive" direction is robot backward in ROS frame
            linear_v  = -float(fields.get('Speed', 0.0))
            angular_w = -float(fields.get('W_mes', 0.0))

            # Publish wheel velocities for encoder_odometry
            vel_msg = Float32MultiArray()
            vel_msg.data = [float(linear_v), float(angular_w)]
            self.wheel_vel_pub.publish(vel_msg)

            # Publish battery
            if 'Bat%' in fields:
                bat_msg = Int32()
                bat_msg.data = int(float(fields['Bat%']))
                self.battery_pub.publish(bat_msg)

            # Publish anomaly flag
            if 'ANOMALY' in fields:
                an_msg = Int32()
                an_msg.data = int(fields['ANOMALY'])
                self.anomaly_pub.publish(an_msg)
                if an_msg.data == 1:
                    self.get_logger().warn(
                        f'[IMU ANOMALY] V={linear_v:.3f} W={angular_w:.3f}'
                        f' AccDev={fields.get("AccDev", "?")}')

        except (ValueError, KeyError) as e:
            self.get_logger().debug(f'Telemetry parse error "{line}": {e}')

    # ──────────────────────────────────────────────────────────
    def cmd_vel_callback(self, msg: Twist):
        self.current_linear  = msg.linear.x
        self.current_angular = msg.angular.z
        self.last_cmd_vel_time = time.time()

    def timer_callback(self):
        elapsed = time.time() - self.last_cmd_vel_time
        if elapsed > self.cmd_vel_timeout:
            self.current_linear  = 0.0
            self.current_angular = 0.0
        self._send_command(self.current_linear, self.current_angular)

    def _send_command(self, linear_vel: float, angular_vel: float):
        if self.serial_conn is None or not self.serial_conn.is_open:
            self._connect_serial()
            if self.serial_conn is None:
                return
        # Negate both: ROS +x forward maps to Arduino -V (confirmed by calibration),
        # ROS CCW+ maps to Arduino CW+ so angular is also negated.
        command = f'M{-linear_vel:.4f}:{-angular_vel:.4f}\n'
        try:
            with self.serial_lock:
                self.serial_conn.write(command.encode('utf-8'))
            if abs(linear_vel) > 0.001 or abs(angular_vel) > 0.001:
                self.get_logger().info(
                    f'[ROS2>>>] M{-linear_vel:.4f}:{-angular_vel:.4f}')
        except serial.SerialException as e:
            self.get_logger().warn(f'Serial write error: {e}')
            self.serial_conn = None

    # ──────────────────────────────────────────────────────────
    def destroy_node(self):
        self.get_logger().info('Shutting down — sending stop to Arduino')
        self.running = False
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(b'M0:0\n')
                time.sleep(0.1)
                self.serial_conn.close()
            except Exception:
                pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelToArduino()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
