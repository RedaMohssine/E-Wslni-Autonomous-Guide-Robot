#!/usr/bin/env python3
"""
Real Robot Navigation Launch File

Launches everything needed for the REAL robot to navigate using an existing map:
  1. robot_state_publisher    — URDF TF tree (base_footprint → base_link → lidar_link)
  2. LD06 LiDAR driver        — Publishes /scan from real LiDAR
  3. cmd_vel_to_arduino       — Bridge /cmd_vel → Serial → Arduino motors
  4. encoder_odometry         — Bridge encoder ticks → /odom + TF(odom → base_footprint)
  5. map_server               — Serves the saved map (map2mapping7.yaml)
  6. AMCL                     — Localization using /scan + /odom + map
  7. controller_server        — Local path following (DWB)
  8. planner_server           — Global path planning (NavFn)
  9. behavior_server          — Recovery behaviors (spin, backup, wait)
 10. bt_navigator             — Behavior tree navigation coordinator
 11. lifecycle_manager        — Manages all Nav2 node lifecycles
 12. RViz2                    — Visualization (optional)

NO Gazebo is launched. The real LiDAR and Arduino are the hardware.

Usage:
  ros2 launch robot_hardware real_robot_nav.launch.py

  # With custom map:
  ros2 launch robot_hardware real_robot_nav.launch.py map:=/path/to/map2mapping7.yaml

  # Specify serial ports:
  ros2 launch robot_hardware real_robot_nav.launch.py serial_port_arduino:=/dev/ttyUSB0 serial_port_lidar:=/dev/ttyUSB1

  # Without RViz:
  ros2 launch robot_hardware real_robot_nav.launch.py use_rviz:=false
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, Command, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch.actions import GroupAction
from launch.actions import DeclareLaunchArgument, TimerAction, ExecuteProcess


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

    # ── RViz config ──
    rviz_config_file = os.path.join(pkg_robot_hardware, 'rviz', 'real_nav.rviz')

    # ── Launch arguments ──
    map_yaml_file = LaunchConfiguration('map', default=default_map)
    params_file = LaunchConfiguration('params_file', default=nav2_params)
    use_rviz = LaunchConfiguration('use_rviz', default='true')
    # Arduino Mega uses native USB → /dev/ttyACM0
    # LD06 LiDAR uses CP2102 USB-UART → /dev/ttyUSB0
    serial_port_arduino = LaunchConfiguration('serial_port_arduino', default='/dev/ttyACM0')
    serial_port_lidar = LaunchConfiguration('serial_port_lidar', default='/dev/ttyUSB0')

    # ── Process robot description (URDF) ──
    # The same URDF is used, but Gazebo plugins are ignored since
    # Gazebo is not running — only the TF tree matters.
    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]),
        value_type=str
    )

    # =========================================================================
    # 1. ROBOT STATE PUBLISHER
    # Publishes the URDF TF tree: base_footprint → base_link → lidar_link
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
    # 2. LD06 LIDAR DRIVER
    # Publishes /scan from the real LiDAR hardware
    # frame_id='lidar_link' matches the URDF TF tree (no extra static TF needed)
    # =========================================================================
    ldlidar_node = Node(
        package='ldlidar_stl_ros2',
        executable='ldlidar_stl_ros2_node',
        name='ldlidar_publisher',
        output='screen',
        parameters=[
            {'product_name': 'LDLiDAR_LD06'},
            {'topic_name': 'scan'},
            {'frame_id': 'lidar_link'},
            {'port_name': serial_port_lidar},
            {'port_baudrate': 230400},
            {'laser_scan_dir': True},
            {'enable_angle_crop_func': False},
            {'angle_crop_min': 135.0},
            {'angle_crop_max': 225.0},
        ]
    )

    # =========================================================================
    # 3. CMD_VEL TO ARDUINO BRIDGE
    # Subscribes to /cmd_vel, sends motor commands to Arduino via serial
    # =========================================================================
    cmd_vel_to_arduino_node = Node(
        package='robot_hardware',
        executable='cmd_vel_to_arduino',
        name='cmd_vel_to_arduino',
        output='screen',
        parameters=[
            hardware_params,
            {'serial_port': serial_port_arduino},
        ],
    )

    # =========================================================================
    # 4. ENCODER ODOMETRY
    # Subscribes to /encoder_ticks, publishes /odom + TF(odom→base_footprint)
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
    # Serves the saved map for AMCL and the global costmap
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
    # 5. AMCL — Adaptive Monte Carlo Localization
    # Uses /scan + /odom + map to localize the robot
    # Publishes TF: map → odom
    # =========================================================================
    amcl_node = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[
            params_file,
            {'use_sim_time': False}
            # Initial pose is set via RViz "2D Pose Estimate" — do NOT force (0,0) here
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
    # Manages all Nav2 nodes (configure → activate in order)
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
    # 8. RVIZ2 (optional) — delayed 6s so map_server is active first
    # =========================================================================
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
    # =========================================================================
    # 9. GLOBAL LOCALIZATION + STARTUP SPIN (autonomous self-localization)
    #
    # Step 1 (t=8s): Spread AMCL particles across the whole map once all
    #   Nav2 nodes are active. Without this the robot has no initial pose.
    #
    # Step 2 (t=10s): Spin the robot ~180° at 0.3 rad/s for 10 seconds.
    #   A stationary robot cannot resolve orientation because the scan looks
    #   the same at many angles. Rotating gives AMCL diverse scan viewpoints
    #   so its particle filter converges on both position AND heading.
    #   The spin stops automatically; Nav2 goals can be given after t≈20s.
    # =========================================================================
    global_localization = TimerAction(
        period=8.0,
        actions=[
            ExecuteProcess(
                cmd=['ros2', 'service', 'call',
                     '/reinitialize_global_localization',
                     'std_srvs/srv/Empty', '{}'],
                output='screen'
            )
        ]
    )

    startup_spin = TimerAction(
        period=10.0,
        actions=[
            ExecuteProcess(
                # Full 360° spin: 0.56 rad/s × 11.2 s ≈ 6.28 rad ≈ 360°
                # Must be a full rotation so the robot ends at the same heading
                # it started at — a ~180° spin caused AMCL to converge on the
                # mirrored pose (180° ambiguity in corridor environments).
                cmd=['ros2', 'topic', 'pub',
                     '--rate', '10', '--times', '112',
                     '/cmd_vel', 'geometry_msgs/msg/Twist',
                     '{angular: {z: 0.56}}'],
                output='screen'
            )
        ]
    )

    # Clear the local costmap right after the spin finishes (t=10+11.2+2=23s).
    # The rotation marks obstacles at many angles; clearing ensures those
    # temporary scan artifacts don't block the first navigation goal.
    clear_costmap_after_spin = TimerAction(
        period=23.0,
        actions=[
            ExecuteProcess(
                cmd=['ros2', 'service', 'call',
                     '/local_costmap/clear_entirely_local_costmap',
                     'nav2_msgs/srv/ClearEntireCostmap', '{}'],
                output='screen'
            )
        ]
    )


    # =========================================================================
    # RETURN LAUNCH DESCRIPTION
    # =========================================================================
    return LaunchDescription([
        # Launch arguments
        DeclareLaunchArgument('map', default_value=default_map,
                             description='Full path to the map YAML file'),
        DeclareLaunchArgument('params_file', default_value=nav2_params,
                             description='Full path to the Nav2 parameters file'),
        DeclareLaunchArgument('use_rviz', default_value='true',
                             description='Launch RViz2 (true/false)'),
        # Arduino Mega native USB = ttyACM0, LD06 CP2102 bridge = ttyUSB0
        DeclareLaunchArgument('serial_port_arduino', default_value='/dev/ttyACM0',
                             description='Serial port for Arduino (motors/encoders)'),
        DeclareLaunchArgument('serial_port_lidar', default_value='/dev/ttyUSB0',
                             description='Serial port for LD06 LiDAR'),

        # 1. Robot description TF tree
        robot_state_publisher_node,

        # 2. LiDAR driver (LD06 → /scan)
        ldlidar_node,

        # 3. Hardware bridges (real robot ↔ ROS2)
        cmd_vel_to_arduino_node,
        encoder_odometry_node,

        # 4. Localization
        map_server_node,
        amcl_node,

        # 5. Navigation
        controller_server_node,
        planner_server_node,
        behavior_server_node,
        bt_navigator_node,

        # 6. Lifecycle manager
        lifecycle_manager_node,

        # 7. Visualization
        rviz_node,
        

        # 8. Autonomous self-localization sequence
        global_localization,          # t=8s : spread AMCL particles across map
        startup_spin,                 # t=10s: spin 360° so AMCL resolves orientation
        clear_costmap_after_spin,     # t=28s: clear scan artifacts from the spin
    ])
  
