import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    # Get package directories
    pkg_robot_simulation = get_package_share_directory('robot_simulation')
    pkg_robot_navigation2 = get_package_share_directory('robot_navigation2')

    # Launch Gazebo with your robot
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_simulation, 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={
            'world': os.path.join(pkg_robot_simulation, 'worlds', 'test_world.world'),
            'use_sim_time': 'true'
        }.items()
    )

    # Launch nav2 with your map
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_robot_navigation2, 'launch', 'simple_nav2.launch.py')
        )
    )

    # Map server with your saved map
    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'yaml_filename': '/home/utilisateur/slam/test/maps/test_world_map.yaml'
        }]
    )

    # Lifecycle manager for map server
    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': ['map_server']
        }]
    )

    return LaunchDescription([
        gazebo_launch,
        map_server,
        lifecycle_manager,
        nav2_launch
    ])