#!/usr/bin/env python3
"""
Complete robot SLAM launch file.
Launches: Robot State Publisher (URDF), LD06 LiDAR, Arduino Bridge, SLAM Toolbox.

Usage:
  source /opt/ros/humble/setup.bash
  source ~/ld06_reel_plateforme_mobile/LD06_SLAM_Robot_Clean/install/setup.bash
  ros2 launch ~/ld06_reel_plateforme_mobile/LD06_SLAM_Robot_Clean/launch/robot_slam_launch.py
"""

from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction
from launch_ros.actions import Node
import os

def generate_launch_description():
    project_dir = os.path.join(
        os.path.expanduser('~'),
        'ld06_reel_plateforme_mobile/LD06_SLAM_Robot_Clean'
    )
    config_dir = os.path.join(project_dir, 'config')
    scripts_dir = os.path.join(project_dir, 'scripts')
    slam_params_file = os.path.join(config_dir, 'mapper_params_online_async.yaml')
    urdf_file = os.path.join(config_dir, 'robot.urdf')

    # Read URDF file content for robot_state_publisher
    with open(urdf_file, 'r') as f:
        robot_description = f.read()

    # ── 1. Robot State Publisher (publishes TF from URDF, including base_link→base_laser)
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': False,
        }]
    )

    # ── 2. LD06 LiDAR node ──────────────────────────────────────────────
    ldlidar_node = Node(
        package='ldlidar_stl_ros2',
        executable='ldlidar_stl_ros2_node',
        name='LD06',
        output='screen',
        parameters=[
            {'product_name': 'LDLiDAR_LD06'},
            {'topic_name': 'scan'},
            {'frame_id': 'base_laser'},
            {'port_name': '/dev/ttyUSB0'},
            {'port_baudrate': 230400},
            {'laser_scan_dir': True},
            {'enable_angle_crop_func': False},
            {'angle_crop_min': 135.0},
            {'angle_crop_max': 225.0},
        ]
    )

    # ── 3. Arduino Bridge (odometry + TF odom→base_link) ────────────────
    arduino_bridge = ExecuteProcess(
        cmd=['python3', os.path.join(scripts_dir, 'arduino_bridge.py')],
        output='screen'
    )

    # ── 4. SLAM Toolbox (delayed 3s to let TF and scans stabilize) ──────
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_params_file,
            {'use_sim_time': False}  # CRITICAL: must be False for real robot
        ]
    )

    # Delay SLAM startup to let LiDAR and odometry publish first
    delayed_slam = TimerAction(
        period=3.0,
        actions=[slam_toolbox_node]
    )

    return LaunchDescription([
        robot_state_publisher_node,
        ldlidar_node,
        arduino_bridge,
        delayed_slam,
    ])
