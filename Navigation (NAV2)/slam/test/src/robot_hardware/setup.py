from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'robot_hardware'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # Install launch files
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*.launch.py'))),
        # Install config files
        (os.path.join('share', package_name, 'config'),
            glob(os.path.join('config', '*.yaml'))),
        # Install arduino sketches (for reference)
        (os.path.join('share', package_name, 'arduino'),
            glob(os.path.join('arduino', '*.ino'))),
        # Install rviz config files
        (os.path.join('share', package_name, 'rviz'),
            glob(os.path.join('rviz', '*.rviz'))),
    ],
    install_requires=['setuptools', 'pyserial'],
    zip_safe=True,
    maintainer='utilisateur',
    maintainer_email='utilisateur@todo.todo',
    description='Real robot hardware bridge: cmd_vel to Arduino and encoder-based odometry',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'cmd_vel_to_arduino = robot_hardware.cmd_vel_to_arduino:main',
            'encoder_odometry = robot_hardware.encoder_odometry:main',
            'fake_hardware = robot_hardware.fake_hardware:main',
            'serial_monitor = robot_hardware.serial_monitor:main',
            'odom_simulator = robot_hardware.odom_simulator:main',
        ],
    },
)
