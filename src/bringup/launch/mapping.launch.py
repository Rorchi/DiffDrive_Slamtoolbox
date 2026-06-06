import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    # Paket dizinlerini al
    pkg_bringup = get_package_share_directory('bringup')
    pkg_description = get_package_share_directory('description')
    pkg_rplidar = get_package_share_directory('rplidar_ros')
    pkg_slam = get_package_share_directory('slam_toolbox')

    # 1. URDF / XACRO İşleme
    xacro_file = os.path.join(pkg_description, 'urdf', 'kasif_celebi.urdf.xacro')
    robot_description_raw = xacro.process_file(xacro_file).toxml()
    
    # 2. ROBOT & JOINT STATE PUBLISHER
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description_raw}]
    )


    # 3. DONANIM DÜĞÜMLERİ (Lidar, Arduino ve Kamera)
    rplidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_rplidar, 'launch', 'rplidar.launch.py'))
    )

    serial_bridge_node = Node(
        package='arduino_bridge',
        executable='serial_bridge',
        parameters=[{'port': '/dev/arduino'}]
    )

    # ---> YENİ EKLENEN KAMERA DÜĞÜMÜ <---
    image_proc_node = Node(
        package='img_proc',
        executable='image_proc_label',
        name='oak_camera_node',
        output='screen'
    )

    # 4. EKF (5 saniye gecikmeli - Sensörlerin ısınması için)
    ekf_config_path = os.path.join(pkg_bringup, 'config', 'ekf.yaml')
    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        parameters=[ekf_config_path]
    )
    delayed_ekf = TimerAction(period=5.0, actions=[ekf_node])

    # 5. SLAM TOOLBOX (8 saniye gecikmeli - EKF'nin stabilize olması için)
    slam_config_path = os.path.join(pkg_bringup, 'config', 'mapper_params_online_async.yaml')
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_slam, 'launch', 'online_async_launch.py')),
        launch_arguments={
            'slam_params_file': slam_config_path,
            'use_sim_time': 'false'
        }.items()
    )
    delayed_slam = TimerAction(period=8.0, actions=[slam_launch])

    return LaunchDescription([
        node_robot_state_publisher,
        rplidar_launch,
        serial_bridge_node,
        image_proc_node,  
        delayed_ekf,
        delayed_slam
    ])
