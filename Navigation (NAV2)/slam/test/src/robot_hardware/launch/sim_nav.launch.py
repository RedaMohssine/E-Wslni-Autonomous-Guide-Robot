#!/usr/bin/env python3
"""
Simulation Navigation Launch — Full Nav2 without real hardware.

Replaces:
  - Arduino / cmd_vel_to_arduino  → REMOVED (no real motors)
  - LD06 LiDAR driver             → REMOVED
  - encoder_odometry              → KEPT (reads fake ticks from fake_hardware)
  
Adds:
  - fake_hardware node            → Converts /cmd_vel → /encoder_ticks + /scan

Result: The robot can be navigated with goals in RViz and will move correctly
        on the map using only software — no Arduino or LiDAR needed.

Usage:
  ros2 launch robot_hardware sim_nav.launch.py
  ros2 launch robot_hardware sim_nav.launch.py map:=/path/to/map2mapping7.yaml
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_robot_hardware = get_package_share_directory('robot_hardware')
    pkg_robot_description = get_package_share_directory('robot_description')
    pkg_robot_simulation = get_package_share_directory('robot_simulation')

    urdf_file = os.path.join(pkg_robot_description, 'urdf', 'robot.urdf.xacro')
    default_map = '/home/utilisateur/slam/test/map2mapping7.yaml'
    nav2_params = os.path.join(pkg_robot_hardware, 'config', 'nav2_real_params.yaml')
    hardware_params = os.path.join(pkg_robot_hardware, 'config', 'hardware_params.yaml')
    rviz_config_file = os.path.join(pkg_robot_hardware, 'rviz', 'real_nav.rviz')

    map_yaml_file = LaunchConfiguration('map', default=default_map)
    params_file = LaunchConfiguration('params_file', default=nav2_params)
    use_rviz = LaunchConfiguration('use_rviz', default='true')

    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]),
        value_type=str
    )

    # ── 1. Robot State Publisher (URDF TF tree) ──
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

    # ── 2. FAKE HARDWARE (replaces Arduino + LiDAR) ──
    # Subscribes to /cmd_vel → publishes /encoder_ticks + /scan
    fake_hardware_node = Node(
        package='robot_hardware',
        executable='fake_hardware',
        name='fake_hardware',
        output='screen',
        parameters=[hardware_params],
    )

    # ── 3. ENCODER ODOMETRY (reads fake ticks → publishes /odom + TF) ──
    encoder_odometry_node = Node(
        package='robot_hardware',
        executable='encoder_odometry',
        name='encoder_odometry',
        output='screen',
        parameters=[hardware_params],
    )

    # ── 4. MAP SERVER ──
    map_server_node = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[
            params_file,
            {'yaml_filename': map_yaml_file, 'use_sim_time': False}
        ],
    )

    # ── 5. AMCL ──
    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[
            params_file,
            {
                'use_sim_time': False,
                'set_initial_pose': True,
                'initial_pose': {'x': 0.0, 'y': 0.0, 'z': 0.0, 'yaw': 0.0},
                'always_reset_initial_pose': True,
            }
        ],
    )

    # ── 6. Nav2 servers ──
    controller_server_node = Node(
        package='nav2_controller',
        executable='controller_server',
        name='controller_server',
        output='screen',
        parameters=[params_file, {'use_sim_time': False}],
    )

    planner_server_node = Node(
        package='nav2_planner',
        executable='planner_server',
        name='planner_server',
        output='screen',
        parameters=[params_file, {'use_sim_time': False}],
    )

    behavior_server_node = Node(
        package='nav2_behaviors',
        executable='behavior_server',
        name='behavior_server',
        output='screen',
        parameters=[params_file, {'use_sim_time': False}],
    )

    bt_navigator_node = Node(
        package='nav2_bt_navigator',
        executable='bt_navigator',
        name='bt_navigator',
        output='screen',
        parameters=[params_file, {'use_sim_time': False}],
    )

    # ── 7. LIFECYCLE MANAGER ──
    lifecycle_manager_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time': False,
            'autostart': True,
            'bond_timeout': 0.0,
            'node_names': [
                'map_server',
                'amcl',
                'controller_server',
                'planner_server',
                'behavior_server',
                'bt_navigator',
            ]
        }]
    )

    # ── 8. RVIZ2 (delayed 6s so map_server is active) ──
    rviz_node = TimerAction(
        period=6.0,
        actions=[
            Node(
                package='rviz2',
                executable='rviz2',
                name='rviz2',
                output='screen',
                parameters=[{'use_sim_time': False}],
                arguments=['-d', rviz_config_file],
                condition=IfCondition(use_rviz),
            )
        ]
    )

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=default_map,
                              description='Full path to the map YAML file'),
        DeclareLaunchArgument('params_file', default_value=nav2_params,
                              description='Full path to Nav2 params file'),
        DeclareLaunchArgument('use_rviz', default_value='true',
                              description='Launch RViz2'),

        robot_state_publisher_node,
        fake_hardware_node,       # ← replaces Arduino + LiDAR
        encoder_odometry_node,
        map_server_node,
        amcl_node,
        controller_server_node,
        planner_server_node,
        behavior_server_node,
        bt_navigator_node,
        lifecycle_manager_node,
        rviz_node,
    ])
