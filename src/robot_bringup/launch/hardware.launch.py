"""Start the Arduino bridge and RPLidar A1 driver for the robot."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    """Create the hardware-only launch description."""
    package_share = get_package_share_directory('robot_bringup')
    arduino_config = os.path.join(
        package_share, 'config', 'arduino_bridge.yaml'
    )
    rplidar_share = get_package_share_directory('rplidar_ros')

    arduino_bridge = Node(
        package='arduino_bridge',
        executable='serial_bridge',
        name='serial_bridge_node',
        output='screen',
        parameters=[arduino_config],
    )

    rplidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(rplidar_share, 'launch', 'rplidar_a1_launch.py')
        ),
        launch_arguments={
            'serial_port': '/dev/rplidar',
            'serial_baudrate': '115200',
            'frame_id': 'laser',
        }.items(),
    )

    return LaunchDescription([arduino_bridge, rplidar])
