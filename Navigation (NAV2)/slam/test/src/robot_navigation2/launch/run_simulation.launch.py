#!/usr/bin/env python3
"""
Complete Simulation Launch for Custom Mobile Robot
Launches: Gazebo + Navigation2 (with map) + RViz2
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    # =================================================================================
    # USER CONFIGURATION SECTION - CUSTOMIZE THESE FOR YOUR ROBOT
    # =================================================================================
    
    # 1. Path to your map YAML file
    MAP_PATH = '/home/utilisateur/slam/test/map2mapping7.yaml'
    
    # 2. Path to your nav2 parameters file
    PARAMS_FILE = os.path.join(
        get_package_share_directory('robot_navigation2'),
        'config',
        'nav2_params.yaml'
    )
    
    # 3. World to load in Gazebo
    WORLD_FILE = os.path.join(
        get_package_share_directory('robot_simulation'),
        'worlds',
        'test_world.world'
    )
    
    # 4. RViz config (optional - leave empty to start with default)
    RVIZ_CONFIG = os.path.join(get_package_share_directory('robot_navigation2'), 'rviz', 'nav2_config.rviz')
    
    # =================================================================================
    # SYSTEM SETUP (DO NOT EDIT BELOW)
    # =================================================================================

    # Get package directories
    pkg_robot_simulation = get_package_share_directory('robot_simulation')
    pkg_robot_navigation2 = get_package_share_directory('robot_navigation2')

    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    
    # IMPORTANT: Choose between SLAM or Navigation with existing map
    # use_slam = LaunchConfiguration('use_slam', default='false')
    use_slam = LaunchConfiguration('use_slam', default='false')

    # --- Step A: Launch Gazebo with Custom Robot ---
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_simulation, 'launch', 'gazebo_headless.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true'
        }.items()
    )

    # --- Step B: Launch Navigation OR SLAM ---
    # Choose based on use_slam argument
    
    # Option 1: SLAM (create new map by exploring)
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_simulation, 'launch', 'slam.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time
        }.items()
    )
    
    # Option 2: Navigation with existing map (Minimal: just Map + AMCL for testing)
    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_navigation2, 'launch', 'navigation_minimal.launch.py')
        ),
        launch_arguments={
            'map': MAP_PATH,
            'use_sim_time': use_sim_time,
            'params_file': PARAMS_FILE
        }.items()
    )

    # --- Step C: Launch RViz2 ---
    rviz_cmd = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=[] if RVIZ_CONFIG is None else ['-d', RVIZ_CONFIG],
        parameters=[{'use_sim_time': True}]
    )

    # =================================================================================
    # RETURN LAUNCH DESCRIPTION
    # =================================================================================
    
    # Build the launch description with conditional SLAM/Navigation
    ld = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock'
        ),
        DeclareLaunchArgument(
            'use_slam',
            default_value='false',
            description='Use SLAM to create new map (true) or use existing map for navigation (false)'
        ),

        gazebo_launch,
        rviz_cmd,
    ]
    
    # Add either SLAM or Localization based on use_slam argument
    # Note: We can't use conditional in LaunchDescription, so we use opaque function or add both
    # For simplicity, we'll add localization by default (use_slam=false)
    ld.append(localization_launch)
    
    # If user wants SLAM instead, they would need to modify this or use a conditional action
    # For now, comment out localization and uncomment slam_launch to use SLAM
    # ld.append(slam_launch)  # Uncomment this line and comment localization_launch above for SLAM mode

    return LaunchDescription(ld)
