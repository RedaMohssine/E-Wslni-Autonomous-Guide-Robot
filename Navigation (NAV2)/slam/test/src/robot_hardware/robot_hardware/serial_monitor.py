#!/usr/bin/env python3
"""
serial_monitor - Diagnostic node that shows what commands Nav2 is sending.

Subscribes to /cmd_vel and prints the exact M<V>:<W> serial command that
would be sent to the Arduino. Use this to verify Nav2 is working correctly
without needing real hardware connected.

Also logs to /serial_monitor/commands topic for programmatic checking.

Output example:
  [serial_monitor] ─── CMD_VEL → SERIAL ───
  [serial_monitor]   cmd_vel: linear=0.150 angular=0.300
  [serial_monitor]   serial:  M0.1500:0.3000
  [serial_monitor]   rate:    10.2 Hz  (52 msgs total)
  [serial_monitor] ────────────────────────
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String
import time


class SerialMonitor(Node):
    def __init__(self):
        super().__init__('serial_monitor')

        # Stats
        self.msg_count = 0
        self.first_msg_time = None
        self.last_msg_time = None
        self.last_linear = 0.0
        self.last_angular = 0.0

        # Subscribe to /cmd_vel (same topic the real bridge listens to)
        self.subscription = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10
        )

        # Publish the formatted serial command as a string (for logging/testing)
        self.cmd_pub = self.create_publisher(
            String,
            '/serial_monitor/commands',
            10
        )

        # Periodic summary (every 2 seconds)
        self.summary_timer = self.create_timer(2.0, self.print_summary)

        self.get_logger().info(
            '\n'
            '╔══════════════════════════════════════════╗\n'
            '║   SERIAL MONITOR — Watching /cmd_vel     ║\n'
            '║   Shows M<V>:<W> commands for Arduino    ║\n'
            '║   No serial port needed (diagnostic)     ║\n'
            '╚══════════════════════════════════════════╝'
        )

    def cmd_vel_callback(self, msg: Twist):
        """Format and display the serial command that would be sent."""
        now = time.time()

        if self.first_msg_time is None:
            self.first_msg_time = now

        self.msg_count += 1
        self.last_msg_time = now
        self.last_linear = msg.linear.x
        self.last_angular = msg.angular.z

        # Build the exact command string the Arduino would receive
        serial_cmd = f'M{msg.linear.x:.4f}:{msg.angular.z:.4f}'

        # Calculate rate
        elapsed = now - self.first_msg_time if self.first_msg_time else 0
        rate = self.msg_count / elapsed if elapsed > 0.1 else 0.0

        # Log to terminal
        self.get_logger().info(
            f'─── CMD_VEL → SERIAL ───\n'
            f'  cmd_vel: linear={msg.linear.x:+.3f}  angular={msg.angular.z:+.3f}\n'
            f'  serial:  {serial_cmd}\n'
            f'  rate:    {rate:.1f} Hz  ({self.msg_count} msgs)\n'
            f'────────────────────────'
        )

        # Also publish as a topic for programmatic checking
        cmd_msg = String()
        cmd_msg.data = serial_cmd
        self.cmd_pub.publish(cmd_msg)

    def print_summary(self):
        """Periodic summary when no commands are flowing."""
        if self.last_msg_time is None:
            self.get_logger().info('⏳ Waiting for /cmd_vel messages... (set a Nav2 Goal in RViz)')
            return

        idle_time = time.time() - self.last_msg_time
        if idle_time > 2.0:
            self.get_logger().info(
                f'⏸  No /cmd_vel for {idle_time:.1f}s | '
                f'Last: linear={self.last_linear:+.3f} angular={self.last_angular:+.3f} | '
                f'Total: {self.msg_count} msgs'
            )


def main(args=None):
    rclpy.init(args=args)
    node = SerialMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
