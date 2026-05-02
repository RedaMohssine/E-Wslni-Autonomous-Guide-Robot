import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.substitutions import LaunchConfiguration, Command
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    
    # Get package directories
    pkg_robot_description = get_package_share_directory('robot_description')
    pkg_robot_simulation = get_package_share_directory('robot_simulation')
    pkg_gazebo_ros = get_package_share_directory('gazebo_ros')
    
    # Paths
    urdf_file = os.path.join(pkg_robot_description, 'urdf', 'robot.urdf.xacro')
    world_file = os.path.join(pkg_robot_simulation, 'worlds', 'test_world.world')
    
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world = LaunchConfiguration('world', default=world_file)
    headless = LaunchConfiguration('headless', default='false')
    
    # Process robot description
    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]),
        value_type=str
    )
    
    # Gazebo launch (headless mode option)
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={
            'world': world,
            'verbose': 'false',
            'gui': 'true'  # Show Gazebo GUI
        }.items()
    )
    
    # Robot State Publisher
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': use_sim_time
        }]
    )
    
    # Spawn robot in Gazebo
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_entity',
        output='screen',
        arguments=[
            '-topic', '/robot_description',
            '-entity', 'mobile_robot',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.2',
            '-timeout', '30.0'
        ]
    )
    
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation time'
        ),
        DeclareLaunchArgument(
            'world',
            default_value=world_file,
            description='Path to world file'
        ),
        DeclareLaunchArgument(
            'headless',
            default_value='false',
            description='Run Gazebo headless (no GUI)'
        ),
        gazebo,
        robot_state_publisher,
        spawn_entity
    ])
