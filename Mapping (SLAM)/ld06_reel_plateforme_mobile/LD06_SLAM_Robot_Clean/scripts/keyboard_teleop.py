#!/usr/bin/env python3
"""
Simple keyboard teleop for the robot
Use arrow keys to control the robot
"""

import sys
import tty
import termios
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__('keyboard_teleop')
        self.publisher = self.create_publisher(Twist, 'cmd_vel', 10)
        
        # Speed settings
        self.linear_speed = 0.1  # m/s (reduced from 0.2)
        self.angular_speed = 0.5  # rad/s
        self.speed_increment = 0.05
        
        print("\n" + "="*50)
        print("  Robot Keyboard Control (AZERTY)")
        print("="*50)
        print("\nControls:")
        print("  Z/↑  : Move forward")
        print("  S/↓  : Move backward")
        print("  Q/←  : Turn left")
        print("  D/→  : Turn right")
        print("  Space: Stop")
        print("  +/-  : Increase/decrease speed")
        print("  A    : Quit")
        print(f"\nCurrent speed: {self.linear_speed} m/s")
        print("="*50 + "\n")
        
    def send_velocity(self, linear, angular):
        """Send velocity command"""
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        self.publisher.publish(msg)
        
    def stop(self):
        """Stop the robot"""
        self.send_velocity(0.0, 0.0)

def get_key():
    """Get a single keypress"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def main():
    rclpy.init()
    teleop = KeyboardTeleop()
    
    try:
        while rclpy.ok():
            key = get_key()
            
            if key == 'a' or key == '\x03':  # a or Ctrl+C
                print("\nQuitting...")
                break
            elif key == 'z' or key == '\x1b[A':  # z or up arrow
                teleop.send_velocity(teleop.linear_speed, 0.0)
                print(f"\r→ Forward at {teleop.linear_speed:.2f} m/s     ", end='', flush=True)
            elif key == 's' or key == '\x1b[B':  # s or down arrow
                teleop.send_velocity(-teleop.linear_speed, 0.0)
                print(f"\r← Backward at {teleop.linear_speed:.2f} m/s    ", end='', flush=True)
            elif key == 'q' or key == '\x1b[D':  # q or left arrow
                teleop.send_velocity(0.1, -teleop.angular_speed)  # Negative angular = left (T-)
                print(f"\r↶ Turn left at {teleop.angular_speed:.2f} rad/s ", end='', flush=True)
            elif key == 'd' or key == '\x1b[C':  # d or right arrow
                teleop.send_velocity(0.1, teleop.angular_speed)  # Positive angular = right (T+)
                print(f"\r↷ Turn right at {teleop.angular_speed:.2f} rad/s", end='', flush=True)
            elif key == ' ':
                teleop.stop()
                print("\r⏸  Stopped                           ", end='', flush=True)
            elif key == '+' or key == '=':
                teleop.linear_speed = min(0.5, teleop.linear_speed + teleop.speed_increment)
                print(f"\r⚡ Speed: {teleop.linear_speed:.2f} m/s         ", end='', flush=True)
            elif key == '-':
                teleop.linear_speed = max(0.05, teleop.linear_speed - teleop.speed_increment)
                print(f"\r🐢 Speed: {teleop.linear_speed:.2f} m/s         ", end='', flush=True)
    
    except KeyboardInterrupt:
        pass
    
    finally:
        teleop.stop()
        print("\n\nRobot stopped. Goodbye!")
        teleop.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
