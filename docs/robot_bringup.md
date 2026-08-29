# Robot bringup paketi

## Amaç

`robot_bringup`, robotun kendi paketlerini ve sistem geneli kurulu sürücüleri
tek bir komutla başlatır. Bu pakette sürücü kaynak kodu bulunmaz; yalnızca
robotun kullandığı parametreler ve başlatma sırası bulunur.

## İlk launch: donanım

`hardware.launch.py` iki düğüm başlatır:

```text
arduino_bridge/serial_bridge   → /imu/data, /odom, /joint_states
rplidar_ros/rplidar_node      → /scan
```

Arduino ayarları `config/arduino_bridge.yaml` içinde tutulur. RPLidar, sistem
genelindeki `rplidar_ros` paketinin resmî `rplidar_a1_launch.py` dosyası
eklenerek başlatılır. Böylece tek başına çalışan A1 launch komutu ile birleşik
donanım launch'ı aynı sürücü ayarlarını kullanır.

## Çalıştırma

```bash
cd ~/DiffDrive_Slamtoolbox
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select robot_bringup
source install/setup.bash
ros2 launch robot_bringup hardware.launch.py
```

Doğrulama için başka bir terminalde:

```bash
source /opt/ros/humble/setup.bash
source ~/DiffDrive_Slamtoolbox/install/setup.bash
ros2 topic list
ros2 topic echo /imu/data --once
ros2 topic echo /odom --once
ros2 topic echo /scan --once
```

## Sonraki aşamalar

Bu paket altında ileride şu launch dosyaları eklenir:

- `mapping.launch.py`: donanım + robot tanımı + EKF + slam_toolbox.
- `localization.launch.py`: donanım + robot tanımı + EKF + kayıtlı harita + AMCL.
- `navigation.launch.py`: localization bileşenleri + Nav2.

Bu modlar aynı anda değil, ihtiyaca göre birer çalışma modu olarak başlatılır.
