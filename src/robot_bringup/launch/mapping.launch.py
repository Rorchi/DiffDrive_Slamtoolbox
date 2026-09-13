# Amaç: Gerçek robotta çevrim içi SLAM haritalamasını başlatır.
# Çalışma: Donanım launch dosyasını dahil eder; Xacro modelini yayımlar, EKF ile
# odometri üretir ve slam_toolbox çevrim içi asenkron launch dosyasını
# slam_toolbox.yaml ile çalıştırır. RViz’i mapping.rviz ile açar.

"""Start hardware, state estimation, slam_toolbox, and mapping RViz."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Create the real-robot online mapping launch description."""
    description_share = get_package_share_directory('robot_description')
    bringup_share = get_package_share_directory('robot_bringup')
    slam_share = get_package_share_directory('slam_toolbox')

    xacro_file = os.path.join(
        description_share, 'urdf', 'kasif_celebi.urdf.xacro'
    )
    ekf_config = os.path.join(bringup_share, 'config', 'ekf.yaml')
    slam_config = os.path.join(
        bringup_share, 'config', 'slam_toolbox.yaml'
    )
    rviz_config = os.path.join(
        bringup_share, 'config', 'mapping.rviz'
    )

    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, 'launch', 'hardware.launch.py')
        )
    )

    robot_description = ParameterValue(
        Command(['xacro ', xacro_file]), value_type=str
    )
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': False,
        }],
    )

    ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config],
    )

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_share, 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'false',
            'slam_params_file': slam_config,
        }.items(),
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': False}],
    )

    return LaunchDescription([
        hardware,
        robot_state_publisher,
        ekf,
        slam,
        rviz,
    ])
