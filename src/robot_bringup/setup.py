# Amaç: Robot başlatma paketinin kurulacak dosyalarını tanımlar.
# Çalışma: setuptools ile Python paketini, ament kaydını, launch dosyalarını ve
# YAML/RViz ayarlarını ROS 2 paket paylaşım dizinine kurar.

import os
from glob import glob

from setuptools import setup


package_name = 'robot_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name],
        ),
        ('share/' + package_name, ['package.xml']),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py'),
        ),
        (
            os.path.join('share', package_name, 'config'),
            glob('config/*.yaml') + glob('config/*.rviz'),
        ),
        (
            os.path.join('share', package_name, 'behavior_trees'),
            glob('behavior_trees/*.xml'),
        ),
        (
            os.path.join('share', package_name, 'maps'),
            glob('maps/*.yaml') + glob('maps/*.pgm'),
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='orin',
    maintainer_email='orin@todo.todo',
    description='Launch and configuration package for the DiffDrive robot.',
    license='TODO: License declaration',
    tests_require=['pytest'],
)
