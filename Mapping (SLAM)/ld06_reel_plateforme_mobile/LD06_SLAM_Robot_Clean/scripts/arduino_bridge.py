#!/usr/bin/env python3
"""
Arduino to ROS2 Odometry Bridge
Reads encoder data from Arduino, publishes odometry, and sends velocity commands
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Quaternion, TransformStamped, Twist
from tf2_ros import TransformBroadcaster
import serial
import math
import time

class ArduinoOdometryBridge(Node):
    def __init__(self):
        super().__init__('arduino_odometry_bridge')
        
        # Declare parameters
        self.declare_parameter('serial_port', '/dev/ttyACM0')  # Arduino on VirtualBox USB passthrough
        self.declare_parameter('baud_rate', 115200)
        self.declare_parameter('wheel_diameter', 0.065)  # meters
        self.declare_parameter('wheel_base', 0.15)  # meters
        
        # Get parameters
        self.serial_port = self.get_parameter('serial_port').value
        self.baud_rate = self.get_parameter('baud_rate').value
        self.wheel_diameter = self.get_parameter('wheel_diameter').value
        self.wheel_base = self.get_parameter('wheel_base').value
        
        # Publishers
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # Subscriber for velocity commands
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10
        )
        
        # Odometry variables
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_time = self.get_clock().now()
        self.steering_angle = 0.0  # Current steering angle from Arduino (degrees)
        self.last_steering_cmd = 0.0  # Last commanded steering
        self.linear_speed = 0.0  # Latest linear speed from Arduino
        self.angular_velocity = 0.0  # Latest angular velocity
        
        # Tricycle robot parameters
        self.wheel_base = 0.15  # Distance from rear axle to front wheel (m)
        
        # Odometry filter parameters
        self.odom_alpha = 0.3  # Low-pass filter for steering (reduce noise)
        self.filtered_steering = 0.0
        
        # Try to connect to Arduino
        self.serial_conn = None
        self.connect_arduino()
        
        # Timer to read serial data AND always publish TF
        self.timer = self.create_timer(0.05, self.read_and_publish)  # 20 Hz
        
        self.get_logger().info('Arduino Odometry Bridge started')
        self.get_logger().info(f'Port: {self.serial_port}, Baud: {self.baud_rate}')
    
    def connect_arduino(self):
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=1.0
            )
            time.sleep(2)  # Wait for Arduino to reset
            self.get_logger().info('Connected to Arduino')
        except Exception as e:
            self.get_logger().error(f'Failed to connect to Arduino: {e}')
            self.serial_conn = None
    
    def read_and_publish(self):
        # Read serial data if available
        if self.serial_conn is not None and self.serial_conn.is_open:
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    self.process_arduino_data(line)
            except Exception as e:
                self.get_logger().warn(f'Error reading serial: {e}')
        
        # ALWAYS publish TF and odom (even without new serial data)
        # This ensures SLAM Toolbox always has a fresh odom->base_link transform
        current_time = self.get_clock().now()
        self.publish_odometry(current_time, self.linear_speed, self.angular_velocity)
    
    def process_arduino_data(self, line):
        """Parse Arduino data: RPM:xxx,Speed:xxx"""
        try:
            # Parse the data
            parts = line.split(',')
            rpm = 0.0
            linear_speed = 0.0
            
            for part in parts:
                if 'RPM:' in part:
                    rpm = float(part.split(':')[1])
                elif 'Speed:' in part:
                    linear_speed = float(part.split(':')[1])
                elif 'Steering:' in part:
                    self.steering_angle = float(part.split(':')[1])
            
            # Calculate odometry
            current_time = self.get_clock().now()
            dt = (current_time - self.last_time).nanoseconds / 1e9
            
            if dt > 0.0 and dt < 1.0:  # Sanity check
                # Apply low-pass filter to steering angle to reduce noise
                self.filtered_steering = (self.odom_alpha * self.steering_angle + 
                                         (1.0 - self.odom_alpha) * self.filtered_steering)
                
                # Tricycle (Ackermann) steering kinematics
                # Convert steering angle from degrees to radians
                steering_rad = math.radians(self.filtered_steering)
                
                # Calculate angular velocity from Ackermann geometry
                # omega = v * tan(delta) / L
                # where v = linear speed, delta = steering angle, L = wheelbase
                if abs(steering_rad) > 0.01:  # If turning
                    angular_velocity = linear_speed * math.tan(steering_rad) / self.wheel_base
                    # Limit unrealistic angular velocities (servo might not be at commanded angle)
                    angular_velocity = max(-2.0, min(2.0, angular_velocity))
                else:  # Straight line
                    angular_velocity = 0.0
                
                # Update robot pose using velocity model
                # For small dt, we can use simple integration
                if abs(angular_velocity) < 0.01:  # Straight line motion
                    delta_x = linear_speed * math.cos(self.theta) * dt
                    delta_y = linear_speed * math.sin(self.theta) * dt
                    delta_theta = 0.0
                else:  # Curved motion (arc)
                    # Radius of curvature
                    radius = linear_speed / angular_velocity
                    # Change in orientation
                    delta_theta = angular_velocity * dt
                    # Arc motion
                    delta_x = radius * (math.sin(self.theta + delta_theta) - math.sin(self.theta))
                    delta_y = radius * (-math.cos(self.theta + delta_theta) + math.cos(self.theta))
                
                # Update pose
                self.x += delta_x
                self.y += delta_y
                self.theta += delta_theta
                # Normalize theta to [-pi, pi]
                self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))
                
                # Store velocities for continuous publishing in read_and_publish
                self.linear_speed = linear_speed
                self.angular_velocity = angular_velocity
            
            self.last_time = current_time
            
        except Exception as e:
            self.get_logger().warn(f'Error processing data "{line}": {e}')
    
    def publish_odometry(self, current_time, linear_vel, angular_vel):
        """Publish odometry message and TF transform"""
        
        # Create quaternion from yaw
        quat = self.euler_to_quaternion(0, 0, self.theta)
        
        # Publish TF transform
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation = quat
        self.tf_broadcaster.sendTransform(t)
        
        # Publish odometry message
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        
        # Position
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation = quat
        
        # Covariance - higher uncertainty during turns (no servo encoder feedback)
        # Increase uncertainty proportional to steering angle
        steering_uncertainty = 1.0 + 5.0 * abs(self.filtered_steering / 45.0)  # Max 6x at full turn
        
        # Position covariance [x, y, z, rot_x, rot_y, rot_z]
        odom.pose.covariance[0] = 0.01 * steering_uncertainty  # x
        odom.pose.covariance[7] = 0.01 * steering_uncertainty  # y
        odom.pose.covariance[14] = 1e6  # z (not used)
        odom.pose.covariance[21] = 1e6  # rot_x (not used)
        odom.pose.covariance[28] = 1e6  # rot_y (not used)
        odom.pose.covariance[35] = 0.05 * steering_uncertainty  # rot_z (yaw) - high uncertainty
        
        # Velocity
        odom.twist.twist.linear.x = linear_vel
        odom.twist.twist.angular.z = angular_vel
        
        # Velocity covariance
        odom.twist.covariance[0] = 0.01  # linear x
        odom.twist.covariance[35] = 0.1 * steering_uncertainty  # angular z
        
        self.odom_pub.publish(odom)
    
    def cmd_vel_callback(self, msg):
        """Receive velocity commands and send to Arduino"""
        if self.serial_conn is None or not self.serial_conn.is_open:
            return
        
        try:
            # Extract linear and angular velocity
            linear_x = msg.linear.x  # Forward/backward speed [m/s]
            angular_z = msg.angular.z  # Rotation speed [rad/s]
            
            # Convert angular velocity to steering angle (-1.0 to 1.0)
            # Assuming max angular velocity of 1.0 rad/s = full steering
            steering = max(-1.0, min(1.0, angular_z / 1.0))
            
            # Store commanded steering for comparison
            self.last_steering_cmd = steering * 45.0  # Convert to degrees
            
            # Send both commands together (no delay between them)
            speed_cmd = f"S{linear_x:.3f}\n"
            steering_cmd = f"T{steering:.3f}\n"
            combined = speed_cmd + steering_cmd
            self.serial_conn.write(combined.encode())
            self.serial_conn.flush()
            
        except Exception as e:
            self.get_logger().warn(f'Error sending command: {e}')
    
    def euler_to_quaternion(self, roll, pitch, yaw):
        """Convert Euler angles to quaternion"""
        qx = math.sin(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) - math.cos(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        qy = math.cos(roll/2) * math.sin(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.cos(pitch/2) * math.sin(yaw/2)
        qz = math.cos(roll/2) * math.cos(pitch/2) * math.sin(yaw/2) - math.sin(roll/2) * math.sin(pitch/2) * math.cos(yaw/2)
        qw = math.cos(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
        
        q = Quaternion()
        q.x = qx
        q.y = qy
        q.z = qz
        q.w = qw
        return q
    
    def __del__(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

def main(args=None):
    rclpy.init(args=args)
    node = ArduinoOdometryBridge()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
