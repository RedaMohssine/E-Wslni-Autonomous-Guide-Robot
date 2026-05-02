#!/usr/bin/env python3
"""
odom_simulator - Makes the robot move autonomously in a slow circle.

Used to validate the full pipeline:
  cmd_vel → cmd_vel_to_arduino → Arduino (or fake) → encoder_ticks → odom → RViz

The robot drives a circle of configurable radius at a configurable speed.
Press Ctrl+C to stop (sends M0:0 stop command).

Usage:
  ros2 run robot_hardware odom_simulator
  ros2 run robot_hardware odom_simulator --ros-args -p linear_speed:=0.1 -p angular_speed:=0.3
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import time


class OdomSimulator(Node):
    def __init__(self):
        super().__init__('odom_simulator')

        # Parameters
        self.declare_parameter('linear_speed', 0.10)   # m/s forward speed
        self.declare_parameter('angular_speed', 0.25)  # rad/s turning rate → circle
        self.declare_parameter('publish_rate', 10.0)   # Hz

        self.linear_speed = self.get_parameter('linear_speed').value
        self.angular_speed = self.get_parameter('angular_speed').value
        self.publish_rate = self.get_parameter('publish_rate').value

        # Publisher on /cmd_vel — same topic Nav2 uses
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Timer
        self.timer = self.create_timer(1.0 / self.publish_rate, self.publish_cmd)

        radius = self.linear_speed / self.angular_speed if self.angular_speed != 0 else float('inf')
        self.get_logger().info(
            f'Odom simulator started — driving circle of radius {radius:.2f}m\n'
            f'  linear={self.linear_speed} m/s, angular={self.angular_speed} rad/s\n'
            f'  Ctrl+C to stop'
        )

    def publish_cmd(self):
        msg = Twist()
        msg.linear.x = self.linear_speed
        msg.angular.z = self.angular_speed
        self.pub.publish(msg)

    def stop(self):
        """Send zero velocity before shutting down."""
        stop_msg = Twist()
        stop_msg.linear.x = 0.0
        stop_msg.angular.z = 0.0
        for _ in range(5):
            self.pub.publish(stop_msg)
            time.sleep(0.05)
        self.get_logger().info('Robot stopped.')


def main(args=None):
    rclpy.init(args=args)
    node = OdomSimulator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
