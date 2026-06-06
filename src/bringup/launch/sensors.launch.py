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
    
    # 1. XACRO İşleme (URDF Modeli)
    xacro_file = os.path.join(pkg_description, 'urdf', 'kasif_celebi.urdf.xacro')
    robot_description_raw = xacro.process_file(xacro_file).toxml()
    
    # 2. Robot State Publisher (TF Zinciri için en kritik düğüm)
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_raw}]
    )

    # 3. Joint State Publisher
    node_joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher'
    )

    # 4. EKF Yapılandırma dosyası yolu
    ekf_config_path = os.path.join(pkg_bringup, 'config', 'ekf.yaml')

    # 5. RPLIDAR LAUNCH
    rplidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_rplidar, 'launch', 'rplidar.launch.py')
        )
    )

    # 2. IMAGE PROCESSING NODE (OAK-1 Kamera)
    image_proc_node = Node(
        package='img_proc',
        executable='image_proc',
        name='oak_camera_node',
        output='screen'
    )

    # 3. ARDUINO BRIDGE (Encoder, IMU ve Oksijen)
    serial_bridge_node = Node(
        package='arduino_bridge',
        executable='serial_bridge',
        name='serial_bridge_node',
        output='screen',
        parameters=[{'port': '/dev/ttyUSB1'}]
    )

    # 4. EKF NODE (Filtreleme Düğümü)
    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config_path]
    )

    # EKF'yi 5 saniye geciktiriyoruz
    delayed_ekf_node = TimerAction(
        period=5.0,
        actions=[ekf_node]
    )

    # Hepsini tek bir LaunchDescription içinde döndür
    return LaunchDescription([
        node_robot_state_publisher,
        node_joint_state_publisher,
        rplidar_launch,
        image_proc_node,
        serial_bridge_node,
        delayed_ekf_node
    ])