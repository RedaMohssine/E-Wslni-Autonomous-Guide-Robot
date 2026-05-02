#!/usr/bin/env python3
"""
fake_hardware — Simulates Arduino + LiDAR for testing Nav2 without real hardware.

Replaces both:
  - cmd_vel_to_arduino  (prints M<V>:<W> commands that WOULD go to Arduino)
  - LD06 LiDAR driver   (publishes a fake /scan so AMCL can start)

Publishes:
  /encoder_ticks  — Simulated cumulative encoder ticks (64 Hz)
  /scan           — Fake laser scan (open space, 450 rays)

Subscribes:
  /cmd_vel        — Reads Nav2 velocity commands

Terminal output:
  Every new M<V>:<W> command is printed:
    [ARDUINO >>>] M0.1500:0.2500
  Every 2 seconds a status table is printed:
    [STATUS] cmd_vel: V=0.150 m/s  W=0.250 rad/s
             ticks:   L=1234  R=1456
             odom:    x=0.23m  y=0.05m  θ=12.3°
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Int32MultiArray
from sensor_msgs.msg import LaserScan
import math
import time


class FakeHardware(Node):
    def __init__(self):
        super().__init__('fake_hardware')

        # ── Robot geometry (must match hardware_params.yaml) ──
        self.declare_parameter('wheel_separation', 0.488)
        self.declare_parameter('wheel_radius', 0.10)
        self.declare_parameter('ticks_per_revolution', 8384)

        self.wheel_separation = self.get_parameter('wheel_separation').value
        self.wheel_radius     = self.get_parameter('wheel_radius').value
        self.ticks_per_rev    = self.get_parameter('ticks_per_revolution').value
        self.meters_per_tick  = (2.0 * math.pi * self.wheel_radius) / self.ticks_per_rev

        # ── Current velocity ──
        self.current_linear  = 0.0
        self.current_angular = 0.0
        self.last_printed_linear  = None   # track changes to avoid spamming
        self.last_printed_angular = None

        # ── Simulated cumulative encoder ticks ──
        self.cum_left  = 0
        self.cum_right = 0

        # ── Simulated pose (for status display only) ──
        self.x     = 0.0
        self.y     = 0.0
        self.theta = 0.0

        # ── Status display counter ──
        self.status_counter = 0
        self.STATUS_EVERY_N = 128   # print status every 128 ticks (= 2 seconds at 64Hz)

        # ── Subscriber ──
        self.cmd_sub = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_cb, 10)

        # ── Publishers ──
        self.enc_pub  = self.create_publisher(Int32MultiArray, '/encoder_ticks', 10)
        self.scan_pub = self.create_publisher(LaserScan, '/scan', 10)

        # ── Timers ──
        self.enc_timer  = self.create_timer(1.0 / 64.0, self.publish_encoder)  # 64 Hz
        self.scan_timer = self.create_timer(0.1,         self.publish_scan)     # 10 Hz

        self.get_logger().info(
            '\n'
            '╔══════════════════════════════════════════════════╗\n'
            '║        FAKE HARDWARE MODE  (no Arduino)          ║\n'
            '║  – Prints M<V>:<W> commands as they would be     ║\n'
            '║    sent to the Arduino                           ║\n'
            '║  – Simulates /encoder_ticks so robot moves       ║\n'
            '║    in RViz                                        ║\n'
            '║  – Publishes fake /scan for AMCL                 ║\n'
            '╚══════════════════════════════════════════════════╝'
        )

    # ─────────────────────────────────────────────────────────────
    # cmd_vel callback — print every NEW command
    # ─────────────────────────────────────────────────────────────
    def cmd_vel_cb(self, msg: Twist):
        self.current_linear  = msg.linear.x
        self.current_angular = msg.angular.z

        # Print only when the command actually changes (avoid log spam)
        changed = (
            self.last_printed_linear  is None or
            abs(self.current_linear  - self.last_printed_linear)  > 0.001 or
            abs(self.current_angular - self.last_printed_angular) > 0.001
        )

        if changed:
            cmd_str = f'M{self.current_linear:.4f}:{self.current_angular:.4f}'
            self.get_logger().info(
                f'\n  [ARDUINO >>>]  {cmd_str}\n'
                f'                 linear={self.current_linear:.4f} m/s   '
                f'angular={self.current_angular:.4f} rad/s'
            )
            self.last_printed_linear  = self.current_linear
            self.last_printed_angular = self.current_angular

    # ─────────────────────────────────────────────────────────────
    # Encoder simulation (64 Hz) — also prints periodic status
    # ─────────────────────────────────────────────────────────────
    def publish_encoder(self):
        dt = 1.0 / 64.0

        # Differential drive: V, W → wheel speeds
        v_left  = self.current_linear - (self.current_angular * self.wheel_separation / 2.0)
        v_right = self.current_linear + (self.current_angular * self.wheel_separation / 2.0)

        # Distance each wheel travels this tick
        dist_left  = v_left  * dt
        dist_right = v_right * dt

        # Accumulate ticks
        delta_left  = int(dist_left  / self.meters_per_tick)
        delta_right = int(dist_right / self.meters_per_tick)
        self.cum_left  += delta_left
        self.cum_right += delta_right

        # Update internal pose estimate (for display only)
        d_center = (dist_left + dist_right) / 2.0
        d_theta  = (dist_right - dist_left) / self.wheel_separation
        self.x     += d_center * math.cos(self.theta + d_theta / 2.0)
        self.y     += d_center * math.sin(self.theta + d_theta / 2.0)
        self.theta += d_theta
        self.theta  = math.atan2(math.sin(self.theta), math.cos(self.theta))

        # Publish encoder ticks
        msg = Int32MultiArray()
        msg.data = [self.cum_left, self.cum_right]
        self.enc_pub.publish(msg)

        # ── Periodic status printout ──
        self.status_counter += 1
        if self.status_counter >= self.STATUS_EVERY_N:
            self.status_counter = 0
            theta_deg = math.degrees(self.theta)
            next_cmd  = f'M{self.current_linear:.4f}:{self.current_angular:.4f}'
            self.get_logger().info(
                f'\n'
                f'  ┌─────────────────────────────────────────┐\n'
                f'  │  ARDUINO command:  {next_cmd:<22}│\n'
                f'  │  cmd_vel:  V={self.current_linear:+.3f} m/s   W={self.current_angular:+.3f} rad/s │\n'
                f'  │  ticks:    L={self.cum_left:<8d}   R={self.cum_right:<8d}    │\n'
                f'  │  odom:     x={self.x:+.3f}m  y={self.y:+.3f}m  θ={theta_deg:+.1f}° │\n'
                f'  └─────────────────────────────────────────┘'
            )

    # ─────────────────────────────────────────────────────────────
    # Fake laser scan (open space — AMCL needs it to start)
    # ─────────────────────────────────────────────────────────────
    def publish_scan(self):
        scan = LaserScan()
        scan.header.stamp    = self.get_clock().now().to_msg()
        scan.header.frame_id = 'lidar_link'
        scan.angle_min       = -math.pi
        scan.angle_max       =  math.pi
        scan.angle_increment = 2.0 * math.pi / 450.0
        scan.time_increment  = 0.0
        scan.scan_time       = 0.1
        scan.range_min       = 0.5
        scan.range_max       = 12.0
        scan.ranges          = [12.0] * 450   # all max range = open space
        scan.intensities     = [100.0] * 450
        self.scan_pub.publish(scan)


def main(args=None):
    rclpy.init(args=args)
    node = FakeHardware()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
