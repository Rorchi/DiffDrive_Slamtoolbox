# Amaç: Kayıtlı haritada Smac 2D global planlama ve RPP yol takibiyle Nav2'yi açar.
# Çalışma: İsteğe bağlı lokalizasyon; planner/controller kendi costmap'lerini
# oluşturur. BT Navigator hedefleri yürütür, behavior_server yalnız bekler.
# Komut zinciri: /cmd_vel_nav -> smoother -> /cmd_vel_smoothed -> collision
# monitor -> /cmd_vel -> Arduino. Hedef verilmeden hareket başlatılmaz.
# Costmap ayarları ve footprint mevcut ortak YAML dosyalarından yüklenir.
# Kullanım: ros2 launch robot_bringup navigation.launch.py rviz:=true
# Lokalizasyon zaten açıksa start_localization:=false kullanılır.
# Global/local costmap'leri Nav2 sunucuları oluşturur.
# Seçenekler: map:=/tam/yol/harita.yaml, use_sim_time:=false, rviz:=false.

"""Start low-speed Smac 2D and RPP navigation on the saved map."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Connect navigation servers to the shared localization and costmaps."""
    share = get_package_share_directory('robot_bringup')
    sim_time = ParameterValue(LaunchConfiguration('use_sim_time'), value_type=bool)
    params = [
        os.path.join(share, 'config', 'nav2_navigation.yaml'),
        os.path.join(share, 'config', 'nav2_costmaps.yaml'),
        os.path.join(share, 'config', 'nav2_footprint.yaml'),
        {'use_sim_time': sim_time},
    ]
    declarations = [
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('start_localization', default_value='true'),
        DeclareLaunchArgument('map', default_value=os.path.join(share, 'maps', 'map3.yaml')),
    ]
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'localization.launch.py')),
        condition=IfCondition(LaunchConfiguration('start_localization')),
        launch_arguments={
            'map': LaunchConfiguration('map'),
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'rviz': 'false',
        }.items(),
    )
    specifications = [
        ('nav2_collision_monitor', 'collision_monitor', []),
        ('nav2_velocity_smoother', 'velocity_smoother', [
            ('cmd_vel', '/cmd_vel_nav'), ('cmd_vel_smoothed', '/cmd_vel_smoothed'),
        ]),
        ('nav2_planner', 'planner_server', []),
        ('nav2_controller', 'controller_server', [('cmd_vel', '/cmd_vel_nav')]),
        ('nav2_behaviors', 'behavior_server', [('cmd_vel', '/cmd_vel_nav')]),
    ]
    servers = [
        Node(package=pkg, executable=name, name=name, output='screen',
             parameters=params, remappings=remaps)
        for pkg, name, remaps in specifications
    ]
    navigator = Node(
        package='nav2_bt_navigator', executable='bt_navigator', name='bt_navigator',
        output='screen', parameters=params + [{
            'default_nav_to_pose_bt_xml': os.path.join(
                share, 'behavior_trees', 'navigate_to_pose.xml'),
            'default_nav_through_poses_bt_xml': os.path.join(
                share, 'behavior_trees', 'navigate_through_poses.xml'),
        }],
    )
    manager = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_navigation', output='screen',
        parameters=[{
            'use_sim_time': sim_time, 'autostart': True, 'bond_timeout': 4.0,
            'node_names': [name for _, name, _ in specifications] + ['bt_navigator'],
        }],
    )
    rviz = Node(
        package='rviz2', executable='rviz2', name='navigation_rviz',
        arguments=['-d', os.path.join(share, 'config', 'navigation.rviz')],
        parameters=[{'use_sim_time': sim_time}],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )
    return LaunchDescription(declarations + [localization, *servers, navigator, manager, rviz])
