# Amaç: Robot model paketinin ament_cmake kurulumunu tanımlar.
# Çalışma: CMake urdf dizinini paketin share dizinine kopyalanacak şekilde kaydeder;
# ament_package çağrısı paketi ROS 2 ortamında bulunabilir hâle getirir.

cmake_minimum_required(VERSION 3.8)
project(robot_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    urdf
    
  DESTINATION share/${PROJECT_NAME}
)

ament_package()