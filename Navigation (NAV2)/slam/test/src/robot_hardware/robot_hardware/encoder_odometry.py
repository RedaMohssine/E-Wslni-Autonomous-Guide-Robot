#!/usr/bin/env python3
"""
encoder_odometry — Compute /odom + TF from Arduino wheel velocity measurements.

The Arduino does NOT send raw encoder ticks — it sends processed telemetry:
  RPM:<avg>,Speed:<V_m/s>,W_mes:<W_rad/s>,...

cmd_vel_to_arduino parses that and publishes:
  /wheel_velocities  →  Float32MultiArray: [linear_V (m/s), angular_W (rad/s)]

This node subscribes to /wheel_velocities and integrates the velocities over
time to produce the odometry pose (x, y, θ) and re-publishes:
  /odom                       (nav_msgs/Odometry)
  TF: odom → base_footprint

Frame convention:
    map → odom → base_footprint → base_link → lidar_link

    This node publishes: odom → base_footprint
    AMCL publishes:      map  → odom
    robot_state_publisher: base_footprint → base_link → lidar_link

Robot geometry (from Arduino):
    RAYON_ROUE = 0.10 m
    ENTRAXE    = 0.488 m
    resolution = 64 CPR,  rapport_reducteur = 131 → 8384 ticks/rev
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import Float32MultiArray
from geometry_msgs.msg import TransformStamped, Quaternion
import tf2_ros
import math


class EncoderOdometry(Node):
    def __init__(self):
        super().__init__('encoder_odometry')

        # ── Parameters ──
        self.declare_parameter('wheel_separation', 0.488)   # ENTRAXE (m)
        self.declare_parameter('wheel_radius',     0.10)    # RAYON_ROUE (m)
        self.declare_parameter('odom_frame',       'odom')
        self.declare_parameter('base_frame',       'base_footprint')
        self.declare_parameter('velocity_timeout', 0.5)     # s — zero odom if no data

        self.wheel_separation  = self.get_parameter('wheel_separation').value
        self.wheel_radius      = self.get_parameter('wheel_radius').value
        self.odom_frame        = self.get_parameter('odom_frame').value
        self.base_frame        = self.get_parameter('base_frame').value
        self.velocity_timeout  = self.get_parameter('velocity_timeout').value

        # ── Odometry state ──
        self.x     = 0.0
        self.y     = 0.0
        self.theta = 0.0
        self.vx    = 0.0   # last measured linear velocity
        self.vth   = 0.0   # last measured angular velocity

        self.last_time     = self.get_clock().now()
        self.last_msg_time = self.get_clock().now()

        # ── Publishers ──
        self.odom_pub = self.create_publisher(Odometry, '/odom', 50)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # ── Subscriber: [linear_V, angular_W] from cmd_vel_to_arduino ──
        self.vel_sub = self.create_subscription(
            Float32MultiArray,
            '/wheel_velocities',
            self.velocity_callback,
            10
        )

        self.get_logger().info(
            f'encoder_odometry started (velocity-based):\n'
            f'  Input topic  : /wheel_velocities [V_m/s, W_rad/s]\n'
            f'  Wheel separation : {self.wheel_separation} m\n'
            f'  Wheel radius     : {self.wheel_radius} m\n'
            f'  Frames: {self.odom_frame} → {self.base_frame}'
        )

    # ──────────────────────────────────────────────────────────────
    def velocity_callback(self, msg: Float32MultiArray):
        """
        Receive [linear_V (m/s), angular_W (rad/s)] from Arduino telemetry
        and integrate to update the odometry pose.

        Arduino publishes at ~12.8 Hz (every 10 cycles at 128 Hz).
        """
        if len(msg.data) < 2:
            self.get_logger().warn('wheel_velocities: expected [V, W], got < 2 values')
            return

        linear_v  = float(msg.data[0])   # m/s  (Arduino "Speed")
        angular_w = float(msg.data[1])   # rad/s (Arduino "W_mes")

        current_time    = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9

        # Guard: skip if dt is unreasonably large (node just started) or zero
        if dt <= 0.0 or dt > 1.0:
            self.last_time     = current_time
            self.last_msg_time = current_time
            self.vx  = linear_v
            self.vth = angular_w
            return

        # ── Integrate pose ──
        delta_theta = angular_w * dt
        dist_center = linear_v  * dt

        if abs(delta_theta) < 1e-6:
            # Straight-line motion
            self.x += dist_center * math.cos(self.theta)
            self.y += dist_center * math.sin(self.theta)
        else:
            # Arc motion — midpoint integration
            mid_theta = self.theta + delta_theta / 2.0
            self.x += dist_center * math.cos(mid_theta)
            self.y += dist_center * math.sin(mid_theta)

        self.theta += delta_theta
        # Normalize to [-π, π]
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))

        self.vx  = linear_v
        self.vth = angular_w

        self.last_time     = current_time
        self.last_msg_time = current_time

        # ── Publish ──
        q = self._yaw_to_quaternion(self.theta)
        self._publish_tf(current_time, q)
        self._publish_odom(current_time, q)

    # ──────────────────────────────────────────────────────────────
    def _publish_tf(self, stamp, q):
        t = TransformStamped()
        t.header.stamp    = stamp.to_msg()
        t.header.frame_id = self.odom_frame
        t.child_frame_id  = self.base_frame
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation = q
        self.tf_broadcaster.sendTransform(t)

    def _publish_odom(self, stamp, q):
        odom = Odometry()
        odom.header.stamp    = stamp.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id  = self.base_frame

        odom.pose.pose.position.x  = self.x
        odom.pose.pose.position.y  = self.y
        odom.pose.pose.position.z  = 0.0
        odom.pose.pose.orientation = q

        # Pose covariance [x, y, z, roll, pitch, yaw] — row-major 6×6
        odom.pose.covariance[0]  = 0.02   # x
        odom.pose.covariance[7]  = 0.02   # y
        odom.pose.covariance[14] = 1e6    # z (planar, don't trust)
        odom.pose.covariance[21] = 1e6    # roll
        odom.pose.covariance[28] = 1e6    # pitch
        odom.pose.covariance[35] = 0.05   # yaw

        odom.twist.twist.linear.x  = self.vx
        odom.twist.twist.linear.y  = 0.0
        odom.twist.twist.angular.z = self.vth

        # Twist covariance
        odom.twist.covariance[0]  = 0.02
        odom.twist.covariance[7]  = 0.02
        odom.twist.covariance[14] = 1e6
        odom.twist.covariance[21] = 1e6
        odom.twist.covariance[28] = 1e6
        odom.twist.covariance[35] = 0.05

        self.odom_pub.publish(odom)

    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _yaw_to_quaternion(yaw: float) -> Quaternion:
        q = Quaternion()
        q.x = 0.0
        q.y = 0.0
        q.z = math.sin(yaw / 2.0)
        q.w = math.cos(yaw / 2.0)
        return q


def main(args=None):
    rclpy.init(args=args)
    node = EncoderOdometry()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
