# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node, SetParameter


def generate_launch_description():
    # Get package directories
    pkg_robot_simulation = get_package_share_directory('robot_simulation')
    pkg_robot_navigation2 = get_package_share_directory('robot_navigation2')
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')

    # Get actual map path
    map_yaml_path = '/home/utilisateur/slam/test/map2mapping7.yaml'

    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    map_yaml_file = LaunchConfiguration('map', default=map_yaml_path)
    params_file = LaunchConfiguration('params_file', default=os.path.join(
        pkg_robot_navigation2, 'config', 'nav2_params.yaml'))

    # Launch Gazebo headless with your robot
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_simulation, 'launch', 'gazebo_headless.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true'
        }.items()
    )

    # Localization (Map Server + AMCL)
    localization_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_navigation2, 'launch', 'localization_simple.launch.py')
        ),
        launch_arguments={
            'map': map_yaml_path,
            'use_sim_time': use_sim_time,
            'params_file': params_file
        }.items()
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='Use simulation (Gazebo) clock if true'),

        DeclareLaunchArgument(
            'map',
            default_value=map_yaml_file,
            description='Full path to the map YAML file'),

        DeclareLaunchArgument(
            'params_file',
            default_value=params_file,
            description='Full path to the ROS2 parameters file'),

        gazebo_launch,
        localization_launch,
    ])