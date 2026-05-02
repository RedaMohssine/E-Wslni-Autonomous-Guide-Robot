#!/usr/bin/env python3
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_robot_simulation = get_package_share_directory('robot_simulation')
    slam_params_file = os.path.join(pkg_robot_simulation, 'config', 'mapper_params_online_async.yaml')
    
    use_sim_time = LaunchConfiguration('use_sim_time')
    
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    )
    
    # Static TF: odom = base_footprint (identité)
    # Cela dit à SLAM que odom et base_footprint sont au même endroit
    static_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='odom_base_identity',
        arguments=['0', '0', '0', '0', '0', '0', 'odom', 'base_footprint'],
        parameters=[{'use_sim_time': use_sim_time}]
    )
    
    # SLAM Toolbox node
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_params_file,
            {'use_sim_time': use_sim_time}
        ]
    )
    
    ld = LaunchDescription()
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(static_tf_node)
    ld.add_action(slam_toolbox_node)
    
    return ld