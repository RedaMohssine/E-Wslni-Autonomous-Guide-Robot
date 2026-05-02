import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    # Utiliser nav2_bringup avec sa configuration par défaut (le plus simple !)
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # Lancement simple avec paramètres par défaut
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'autostart': 'true'
        }.items()
    )

    return LaunchDescription([
        nav2_launch
    ])