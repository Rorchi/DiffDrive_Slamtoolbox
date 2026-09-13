<!--
Amaç: Kaşif Çelebi robotunun güncel ROS 2 mimarisini, kurulumunu ve çalışma
modlarını açıklar. Ayrıntılı kalibrasyon ve hata analizi docs/ altındadır.
-->

# Kaşif Çelebi — ROS 2 SLAM ve Lokalizasyon

Bu çalışma alanı, diferansiyel sürüşlü Kaşif Çelebi robotunun Jetson Orin
üzerinde ROS 2 Humble ile çalıştırılmasını sağlar. Arduino'dan gelen encoder ve
IMU verileri `robot_localization` EKF ile birleştirilir; RPLidar A1 kullanılarak
`slam_toolbox` ile harita oluşturulur ve kayıtlı haritada Nav2 AMCL ile
lokalizasyon yapılır.

## Güncel durum

| Aşama | Durum | Açıklama |
|---|---|---|
| Arduino seri köprü | Tamamlandı | IMU, encoder, odometri, joint-state ve batarya topic'leri yayınlanıyor. |
| Robot modeli ve TF | Tamamlandı | URDF/Xacro ve tek TF yayıncısı sorumlulukları yapılandırıldı. |
| Encoder + IMU EKF | Tamamlandı | `robot_localization` ile yerel odometri üretiliyor. |
| SLAM | Tamamlandı | Yön ve wheel-base kalibrasyonundan sonra düzgün harita elde edildi. |
| Kayıtlı harita | Tamamlandı | Varsayılan harita `map3.pgm + map3.yaml`. |
| AMCL lokalizasyonu | Yapılandırıldı | Map server, AMCL ve lifecycle manager tek launch dosyasına eklendi. |
| Nav2 navigasyon | Planlanan | Costmap, planner, controller ve davranış ağacı henüz eklenmedi. |

Nihai hareket kalibrasyonu:

```yaml
wheel_radius: 0.04
wheel_base: 0.20
encoder_ticks_per_rev: 7000.0
imu_gyro_z_scale: 1.0
wheel_yaw_scale: -1.0
```

Bu değerler rosbag analizi, URDF geometrisi ve fiziksel sağ/sol dönüş testleri
sonucunda belirlenmiştir.

## Sistem mimarisi

### Haritalama modu

```text
Arduino encoder ─► /wheel/odometry_raw ─┐
                                         ├─► robot_localization EKF
Arduino IMU ─────► /imu/data_raw ────────┘          │
                                                     ├─► /odometry/filtered
                                                     └─► odom → base_link

RPLidar ─────────► /scan ───────────────► slam_toolbox
                                                ├─► /map
                                                └─► map → odom
```

### Kayıtlı haritada lokalizasyon modu

```text
map3.yaml + map3.pgm ─► map_server ─► /map ─┐
                                                ├─► AMCL ─► map → odom
RPLidar ──────────────► /scan ───────────────┘

Arduino encoder + IMU ─► robot_localization EKF ─► odom → base_link
URDF/Xacro ────────────► robot_state_publisher ──► sensör/tekerlek TF'leri
```

TF yayıncıları kesin olarak ayrılmıştır:

| TF | Haritalama | Lokalizasyon |
|---|---|---|
| `map → odom` | `slam_toolbox` | AMCL |
| `odom → base_link` | EKF | EKF |
| `base_link → laser_frame`, `imu_link`, tekerlekler | `robot_state_publisher` | `robot_state_publisher` |

> **Önemli:** `mapping.launch.py` ile `localization.launch.py` aynı anda
> çalıştırılmamalıdır. Aksi durumda `map → odom` TF çakışması oluşur.

## Donanım ve yazılım

- NVIDIA Jetson Orin, Ubuntu 22.04
- ROS 2 Humble
- Arduino Mega2560 sınıfı kontrol kartı
- Tekerlek encoderleri
- IMU; doğrusal ivme ve açısal hız
- RPLidar A1
- Diferansiyel sürüş şasisi

Kullanılan temel ROS paketleri:

- `arduino_bridge`
- `robot_description`
- `robot_bringup`
- `robot_localization`
- `slam_toolbox`
- `rplidar_ros`
- `nav2_map_server`
- `nav2_amcl`
- `nav2_lifecycle_manager`
- `teleop_twist_keyboard`

## Kurulum

### ROS bağımlılıkları

```bash
sudo apt update
sudo apt install \
  ros-humble-rplidar-ros \
  ros-humble-robot-localization \
  ros-humble-slam-toolbox \
  ros-humble-nav2-map-server \
  ros-humble-nav2-amcl \
  ros-humble-nav2-lifecycle-manager \
  ros-humble-teleop-twist-keyboard \
  ros-humble-xacro
```

### Kalıcı USB cihaz adları

Arduino ve lidarın `/dev/ttyUSB*` sırası yeniden başlatmalarda değişebileceği
için udev kuralları kullanılır:

```bash
cd ~/DiffDrive_Slamtoolbox
sudo install -m 644 \
  scripts/usb_serial/99-kasif-usb-serial.rules \
  /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -aG dialout $USER
```

Grup değişikliğinin etkinleşmesi için oturumu kapatıp açın. Ardından:

```bash
lsusb
ls -l /dev/arduino /dev/rplidar
groups
```

Beklenen cihaz adları:

```text
/dev/arduino
/dev/rplidar
```

## Derleme ve test

```bash
cd ~/DiffDrive_Slamtoolbox
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

Testler:

```bash
colcon test
colcon test-result --verbose
```

Son doğrulanan sonuç:

```text
8 test, 0 hata, 0 başarısızlık, 1 atlanan test
```

## Çalıştırma modları

Her yeni terminalde önce:

```bash
source /opt/ros/humble/setup.bash
source ~/DiffDrive_Slamtoolbox/install/setup.bash
```

### 1. Yalnız donanım

Arduino seri köprü ve RPLidar sürücüsünü başlatır:

```bash
ros2 launch robot_bringup hardware.launch.py
```

### 2. Robot modeli ve EKF testi

Donanım, robot modeli, EKF ve RViz'i SLAM olmadan başlatır:

```bash
ros2 launch robot_bringup hardwareRobotmodel.launch.py
```

### 3. SLAM ile yeni harita oluşturma

Başka bringup süreçleri kapalıyken:

```bash
ros2 launch robot_bringup mapping.launch.py
```

Farklı terminalde düşük hızlı teleop:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -p speed:=0.08 \
  -p turn:=0.25 \
  -p repeat_rate:=10.0 \
  -p key_timeout:=0.5
```

Teleop yönleri:

```text
I → ileri
, → geri
J → sol
L → sağ
```

Haritayı kaydetme:

```bash
ros2 run nav2_map_server map_saver_cli \
  -f ~/DiffDrive_Slamtoolbox/yeni_harita
```

Bu komut `yeni_harita.pgm` ve `yeni_harita.yaml` üretir. SLAM Toolbox
lokalizasyonu veya haritalamaya devam etmek için occupancy haritasına ek olarak
pose graph da kaydedilmelidir:

```bash
ros2 service call /slam_toolbox/serialize_map \
  slam_toolbox/srv/SerializePoseGraph \
  "{filename: '/home/orin/DiffDrive_Slamtoolbox/yeni_harita_posegraph'}"
```

### 4. `map3` üzerinde AMCL lokalizasyonu

Mapping sürecini tamamen kapattıktan sonra:

```bash
ros2 launch robot_bringup localization.launch.py
```

Launch dosyası varsayılan olarak paket içindeki `map3.yaml` dosyasını açar.
Başka bir harita kullanmak için:

```bash
ros2 launch robot_bringup localization.launch.py \
  map:=/tam/yol/harita.yaml
```

RViz açıldığında `2D Pose Estimate` aracını kullanarak robotun haritadaki
yaklaşık konumunu ve baktığı yönü belirtin. AMCL başlangıç pozu almadan
`map → odom` TF'sini üretmeyebilir.

Lokalizasyon kontrolü:

```bash
ros2 lifecycle get /map_server
ros2 lifecycle get /amcl
ros2 topic echo /amcl_pose --once
ros2 run tf2_ros tf2_echo map odom
ros2 run tf2_ros tf2_echo map base_link
```

`map_server` ve `amcl` için beklenen lifecycle durumu `active [3]` değeridir.

## Ana topic'ler

| Topic | Tür | Yayıncı | Amaç |
|---|---|---|---|
| `/imu/data_raw` | `sensor_msgs/Imu` | `serial_bridge` | Ham IMU ivme ve gyro verisi |
| `/wheel/encoders` | `std_msgs/Int64MultiArray` | `serial_bridge` | Sol/sağ kümülatif encoder tick'leri |
| `/wheel/odometry_raw` | `nav_msgs/Odometry` | `serial_bridge` | EKF öncesi wheel odometry |
| `/odometry/filtered` | `nav_msgs/Odometry` | EKF | Encoder + IMU birleşik yerel odometri |
| `/scan` | `sensor_msgs/LaserScan` | RPLidar | SLAM ve AMCL lidar girdisi |
| `/map` | `nav_msgs/OccupancyGrid` | SLAM veya map server | Occupancy grid haritası |
| `/amcl_pose` | `geometry_msgs/PoseWithCovarianceStamped` | AMCL | Harita üzerindeki robot pozu |
| `/particle_cloud` | `nav2_msgs/ParticleCloud` | AMCL | AMCL parçacık dağılımı |
| `/cmd_vel` | `geometry_msgs/Twist` | Teleop/Nav2 | Hareket komutu |
| `/tf`, `/tf_static` | TF | EKF, SLAM/AMCL, RSP | Koordinat dönüşümleri |

Seri köprü ayrıca batarya ve joint-state topic'lerini yayınlar. Tam protokol
için [seri protokol belgesine](docs/serial-protocol.md) bakın.

## `map3` haritası

Varsayılan lokalizasyon haritası:

```text
src/robot_bringup/maps/map3.pgm
src/robot_bringup/maps/map3.yaml
```

Harita özellikleri:

```text
çözünürlük: 0.05 m/piksel
boyut:       171 × 331 piksel
alan:        yaklaşık 8.55 × 16.55 m
origin:      [-3.68, -4.09, 0.0]
mod:         trinary
```

PGM dosyasını normal görüntüleyiciyle açmak için:

```bash
eog ~/DiffDrive_Slamtoolbox/map3.pgm
```

## Farklı bilgisayardan RViz kullanımı

Jetson ve laptop aynı ROS domain'ini kullanmalıdır. Jetson'ın mevcut domain'i
`30` olarak ayarlanmıştır. Laptop terminalinde:

```bash
source /opt/ros/humble/setup.bash
export ROS_DOMAIN_ID=30
export ROS_LOCALHOST_ONLY=0
ros2 daemon stop
ros2 daemon start
rviz2
```

Bağlantıyı kontrol edin:

```bash
ros2 node list
ros2 topic info /map --verbose
ros2 topic echo /map \
  --qos-durability transient_local \
  --qos-reliability reliable \
  --once \
  --field info
```

RViz ayarları:

```text
Global Options / Fixed Frame: map
Map / Topic:                  /map
Map / Reliability Policy:     Reliable
Map / Durability Policy:      Transient Local
```

Map server haritayı `TRANSIENT_LOCAL` olarak saklar. Laptopta Map display
`VOLATILE` kalırsa topic görünmesine rağmen daha önce yayımlanan harita
görüntülenmeyebilir.

## Rosbag kaydı

Haritalama ve lokalizasyon sorunlarını tekrar üretmek için önerilen kayıt:

```bash
ros2 bag record \
  -o localization_check \
  /scan \
  /map \
  /imu/data_raw \
  /wheel/odometry_raw \
  /wheel/encoders \
  /odometry/filtered \
  /amcl_pose \
  /particle_cloud \
  /initialpose \
  /tf \
  /tf_static \
  /diagnostics \
  /cmd_vel \
  /rosout
```

## Hızlı sorun giderme

### Robot hareketsizken RViz pozu sıçrıyor

Birden fazla EKF, seri köprü, lidar veya launch süreci çalışıyor olabilir:

```bash
ps aux | grep -E \
  "ekf_node|serial_bridge|robot_state_publisher|rplidar|slam_toolbox|amcl" \
  | grep -v grep
```

Her bileşenden yalnız bir tane bulunmalıdır.

### `/map` var ama RViz'de harita görünmüyor

- Fixed Frame alanına elle `map` yazın.
- Map topic'ini `/map` seçin.
- Durability değerini `Transient Local` yapın.
- Reliability değerini `Reliable` yapın.
- AMCL için `2D Pose Estimate` ile başlangıç pozu verin.

### `Gecersiz seri paket yok sayildi`

Arduino satırı geçerli JSON değil, zorunlu alan eksik veya `NaN/Inf` içeriyor
olabilir. Açılışta tek uyarı yarım başlangıç satırından kaynaklanabilir; sürekli
tekrarlanıyorsa baudrate ve firmware mesaj biçimi kontrol edilmelidir.

### `cmd_vel zaman asimi`

0.5 saniye yeni hareket komutu gelmediğinde seri köprü güvenlik amacıyla
Arduino'ya dur (`S`) komutu gönderir. Teleop kapanmasında bu beklenen davranıştır.

## Proje dizinleri

```text
arduino/mega2560/          Firmware için ayrılmış dizin ve entegrasyon notları
docs/                      Kurulum, protokol ve SLAM teknik raporları
scripts/usb_serial/        Kalıcı /dev/arduino ve /dev/rplidar udev kuralları
src/arduino_bridge/        Arduino USB/JSON ↔ ROS 2 köprüsü ve testleri
src/robot_bringup/         Launch, EKF, SLAM, AMCL, RViz ve harita ayarları
src/robot_description/     URDF/Xacro robot, tekerlek ve sensör geometrisi
```

Arduino üzerinde çalışan gerçek `.ino` firmware kaynağı henüz bu depoda
bulunmamaktadır. Firmware güncellendiğinde pin bağlantıları, motor yönleri,
encoder çözünürlüğü ve seri protokolüyle birlikte sürüm kontrolüne eklenmelidir.

## Ayrıntılı belgeler

- [Robot bringup ve çalışma modları](docs/robot_bringup.md)
- [Arduino–Jetson seri protokolü](docs/serial-protocol.md)
- [RPLidar kurulum notları](docs/rplidar.md)
- [SLAM hazırlık ve hata giderme raporu](docs/slam-mapping-calibration-report.md)
- [LibreOffice Writer teknik raporu](docs/slam-mapping-calibration-report-writer.odt)

## Sonraki aşama

AMCL lokalizasyonu fiziksel sürüş ve rosbag ile doğrulandıktan sonra Nav2 için
şu bileşenler eklenecektir:

1. Robot footprint ve inflation ayarları
2. Global ve local costmap
3. Global planner
4. Yerel controller
5. Velocity smoother ve güvenlik sınırları
6. Behavior tree ve recovery davranışları
7. RViz `Nav2 Goal` uçtan uca testi
