#!/usr/bin/env python3
"""
Test Launch — Runs the FULL Nav2 navigation stack with FAKE hardware.

Use this to verify everything works WITHOUT the real Arduino/LiDAR:
  - Map loads and shows in RViz ✓
  - Robot model appears on the map ✓
  - You can set "2D Pose Estimate" ✓
  - You can send "2D Nav Goal" ✓
  - Path is planned and drawn (green line) ✓
  - Controller sends /cmd_vel ✓
  - Robot moves on the map ✓

Usage:
  ros2 launch robot_hardware test_nav.launch.py
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction, ExecuteProcess
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # ── Package directories ──
    pkg_robot_hardware = get_package_share_directory('robot_hardware')
    pkg_robot_description = get_package_share_directory('robot_description')
    pkg_robot_simulation = get_package_share_directory('robot_simulation')

    # ── File paths ──
    urdf_file = os.path.join(pkg_robot_description, 'urdf', 'robot.urdf.xacro')
    default_map = '/home/utilisateur/slam/test/map2mapping7.yaml'
    nav2_params = os.path.join(pkg_robot_hardware, 'config', 'nav2_real_params.yaml')
    hardware_params = os.path.join(pkg_robot_hardware, 'config', 'hardware_params.yaml')
    rviz_config = os.path.join(pkg_robot_hardware, 'rviz', 'real_nav.rviz')

    # ── Launch arguments ──
    map_yaml_file = LaunchConfiguration('map', default=default_map)
    params_file = LaunchConfiguration('params_file', default=nav2_params)

    # ── URDF ──
    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]),
        value_type=str
    )

    # =========================================================================
    # 1. ROBOT STATE PUBLISHER (URDF TF tree)
    # =========================================================================
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

    # =========================================================================
    # 2. FAKE HARDWARE (replaces Arduino + LiDAR)
    # =========================================================================
    fake_hardware_node = Node(
        package='robot_hardware',
        executable='fake_hardware',
        name='fake_hardware',
        output='screen',
        parameters=[hardware_params],
    )

    # =========================================================================
    # 2b. SERIAL MONITOR (shows what commands Nav2 would send to Arduino)
    # =========================================================================
    serial_monitor_node = Node(
        package='robot_hardware',
        executable='serial_monitor',
        name='serial_monitor',
        output='screen',
    )

    # =========================================================================
    # 3. ENCODER ODOMETRY (reads fake ticks → publishes /odom + TF)
    # =========================================================================
    encoder_odometry_node = Node(
        package='robot_hardware',
        executable='encoder_odometry',
        name='encoder_odometry',
        output='screen',
        parameters=[hardware_params],
    )

    # =========================================================================
    # 4. MAP SERVER
    # =========================================================================
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

    # =========================================================================
    # 5. AMCL
    # =========================================================================
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

    # =========================================================================
    # 6. NAV2 SERVERS
    # =========================================================================
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

    # =========================================================================
    # 7. LIFECYCLE MANAGER
    # =========================================================================
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

    # =========================================================================
    # 8. RVIZ2 (with preconfigured nav display)
    # =========================================================================
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': False}],
    )

    # =========================================================================
    # 9. AUTO INITIAL POSE
    # =========================================================================
    publish_initial_pose = TimerAction(
        period=8.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    'ros2', 'topic', 'pub', '--once',
                    '/initialpose',
                    'geometry_msgs/msg/PoseWithCovarianceStamped',
                    '{header: {frame_id: "map"}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}, covariance: [0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.06853892326654787]}}'
                ],
                output='screen'
            )
        ]
    )

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=default_map,
                             description='Full path to the map YAML file'),
        DeclareLaunchArgument('params_file', default_value=nav2_params,
                             description='Full path to the Nav2 parameters file'),

        # Robot TF tree
        robot_state_publisher_node,

        # Fake hardware (replaces Arduino + LiDAR)
        fake_hardware_node,
        encoder_odometry_node,

        # Serial monitor (shows M<V>:<W> commands in terminal)
        serial_monitor_node,

        # Nav2 stack
        map_server_node,
        amcl_node,
        controller_server_node,
        planner_server_node,
        behavior_server_node,
        bt_navigator_node,
        lifecycle_manager_node,

        # Visualization
        rviz_node,

        # Auto initial pose
        publish_initial_pose,
    ])
