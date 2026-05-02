#!/usr/bin/env python3
"""
Custom SLAM launch file that correctly sets use_sim_time=false
and includes all necessary nodes for the robot.
"""

from launch import LaunchDescription
from launch_ros.actions import Node
import os

def generate_launch_description():
    config_dir = os.path.join(
        os.path.expanduser('~'),
        'ld06_reel_plateforme_mobile/LD06_SLAM_Robot_Clean/config'
    )
    
    slam_params_file = os.path.join(config_dir, 'mapper_params_online_async.yaml')

    # SLAM Toolbox node with use_sim_time explicitly FALSE
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

    return LaunchDescription([
        slam_toolbox_node
    ])
