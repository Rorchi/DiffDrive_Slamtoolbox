<!--
Amaç: Robotun donanım, model ve haritalama başlatma akışlarını açıklar.
Çalışma: Launch komutlarını, düğümlerin görevlerini ve parametre dosyalarını
anlatarak robot_bringup paketinin kullanımına rehberlik eder.
-->

# Robot bringup paketi

## Amaç

`robot_bringup`, robotun kendi paketlerini ve sistem geneli kurulu sürücüleri
tek bir komutla başlatır. Bu pakette sürücü kaynak kodu bulunmaz; yalnızca
robotun kullandığı parametreler ve başlatma sırası bulunur.

## İlk launch: donanım

`hardware.launch.py` iki düğüm başlatır:

```text
arduino_bridge/serial_bridge   → /imu/data_raw, /wheel/odometry_raw,
                                  /joint_states
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
ros2 topic echo /imu/data_raw --once
ros2 topic echo /wheel/odometry_raw --once
ros2 topic echo /scan --once
```

## Sonraki aşamalar

Bu paket altında ileride şu launch dosyaları eklenir:

- `mapping.launch.py`: donanım + robot tanımı + EKF + slam_toolbox.
- `localization.launch.py`: donanım + robot tanımı + EKF + kayıtlı harita + AMCL.
- `navigation.launch.py`: localization bileşenleri + Nav2.

Bu modlar aynı anda değil, ihtiyaca göre birer çalışma modu olarak başlatılır.

## Haritalama

Gerçek robotta Arduino, RPLidar, robot modeli, EKF, slam_toolbox ve RViz'i tek
komutla başlatmak için:

```bash
ros2 launch robot_bringup mapping.launch.py
```

Haritalama sırasında `slam_toolbox` yalnızca `map -> odom`, EKF ise yalnızca
`odom -> base_link` TF'sini yayınlar. Robot düşük hızda teleop ile sürülür:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Harita tamamlanınca occupancy grid kaydedilir:

```bash
mkdir -p ~/maps
ros2 run nav2_map_server map_saver_cli -f ~/maps/kasif_map
```

## Robot modeli ve EKF

`hardwareRobotmodel.launch.py`, donanıma ek olarak robot modelini, RViz'i ve
`robot_localization` EKF düğümünü başlatır. Arduino köprüsü ham odometriyi
`/wheel/odometry_raw` üzerinde yayınlar. Köprüde `publish_odom_tf: false`
olduğu için `odom -> base_link` TF'sinin tek yayıncısı EKF'dir; böylece TF
çakışması oluşmaz. Filtrelenmiş odometri `/odometry/filtered` üzerindedir.

## Kayıtlı haritada AMCL lokalizasyonu

`localization.launch.py`, donanım ve EKF'ye ek olarak paket içindeki `map3`
haritasını, AMCL'yi ve Nav2 lifecycle manager'ı başlatır:

```bash
sudo apt install ros-humble-nav2-amcl \
  ros-humble-nav2-lifecycle-manager

cd ~/DiffDrive_Slamtoolbox
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select robot_bringup
source install/setup.bash
ros2 launch robot_bringup localization.launch.py
```

Farklı bir harita seçmek için:

```bash
ros2 launch robot_bringup localization.launch.py \
  map:=/tam/yol/harita.yaml
```

RViz açıldığında `2D Pose Estimate` aracını seçip robotun haritadaki yaklaşık
konumunu ve yönünü verin. AMCL `map -> odom`, EKF `odom -> base_link` TF'sini
yayımlar. Bu modda `mapping.launch.py` veya başka bir `slam_toolbox` süreci
aynı anda çalıştırılmamalıdır.
