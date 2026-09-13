"""Start the real robot on a saved map with EKF and AMCL localization."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Create the saved-map localization launch description."""
    description_share = get_package_share_directory('robot_description')
    bringup_share = get_package_share_directory('robot_bringup')

    xacro_file = os.path.join(
        description_share, 'urdf', 'kasif_celebi.urdf.xacro'
    )
    ekf_config = os.path.join(bringup_share, 'config', 'ekf.yaml')
    amcl_config = os.path.join(bringup_share, 'config', 'amcl.yaml')
    rviz_config = os.path.join(bringup_share, 'config', 'mapping.rviz')
    default_map = os.path.join(bringup_share, 'maps', 'map3.yaml')

    map_file = LaunchConfiguration('map')
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rviz = LaunchConfiguration('rviz')

    declare_map = DeclareLaunchArgument(
        'map',
        default_value=default_map,
        description='Kullanılacak occupancy map YAML dosyasının tam yolu.',
    )
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Rosbag playback dışında false bırakılmalıdır.',
    )
    declare_rviz = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        description='Lokalizasyon RViz görünümünü başlatır.',
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
            'use_sim_time': use_sim_time,
        }],
    )

    ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config, {'use_sim_time': use_sim_time}],
    )

    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{
            'yaml_filename': ParameterValue(map_file, value_type=str),
            'use_sim_time': use_sim_time,
        }],
    )

    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[amcl_config, {'use_sim_time': use_sim_time}],
    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'autostart': True,
            'node_names': ['map_server', 'amcl'],
            'bond_timeout': 4.0,
        }],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(use_rviz),
    )

    return LaunchDescription([
        declare_map,
        declare_use_sim_time,
        declare_rviz,
        hardware,
        robot_state_publisher,
        ekf,
        map_server,
        amcl,
        lifecycle_manager,
        rviz,
    ])
