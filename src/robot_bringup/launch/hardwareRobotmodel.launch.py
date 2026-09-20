# Amaç: Donanım, robot modeli ve yerel odometriyi RViz'de birlikte incelemek.
# Çalışma: Arduino köprüsü ve RPLidar başlatılır. Ana Xacro dosyası URDF'ye
# dönüştürülür; robot_state_publisher gövde, sensör ve tekerlek TF'lerini üretir.
# EKF, ekf.yaml ile encoder/IMU hızlarını birleştirerek /odometry/filtered ve
# odom -> base_link TF'sini yayımlar. RViz robot_model.rviz ile açılır.
# Harita ve map -> odom dönüşümü üreten bir lokalizasyon düğümü başlatılmaz.
# Kullanım: ros2 launch robot_bringup hardwareRobotmodel.launch.py

"""Start the robot hardware, state publisher, and RViz."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Create the complete hardware and visualization launch description."""
    description_share = get_package_share_directory('robot_description')
    bringup_share = get_package_share_directory('robot_bringup')
    rplidar_share = get_package_share_directory('rplidar_ros')

    xacro_file = os.path.join(
        description_share,
        'urdf',
        'kasif_celebi.urdf.xacro',
    )
    arduino_config = os.path.join(
        bringup_share,
        'config',
        'arduino_bridge.yaml',
    )
    ekf_config = os.path.join(
        bringup_share,
        'config',
        'ekf.yaml',
    )
    rviz_config = os.path.join(
        bringup_share,
        'config',
        'robot_model.rviz',
    )

    robot_description = ParameterValue(
        Command(['xacro ', xacro_file]),
        value_type=str,
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

    arduino_bridge = Node(
        package='arduino_bridge',
        executable='serial_bridge',
        name='serial_bridge_node',
        output='screen',
        parameters=[arduino_config],
    )

    ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config],
    )

    rplidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(rplidar_share, 'launch', 'rplidar_a1_launch.py')
        ),
        launch_arguments={
            'serial_port': '/dev/rplidar',
            'serial_baudrate': '115200',
            'frame_id': 'laser_frame',
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
        robot_state_publisher,
        arduino_bridge,
        ekf,
        rplidar,
        rviz,
    ])
