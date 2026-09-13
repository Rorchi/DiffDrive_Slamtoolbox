<!--
Amaç: Projenin genel yapısını ve başlangıç adımlarını açıklar.
Çalışma: Çalışma alanını derleme ve seri köprüyü başlatma komutlarını sunar;
ayrıntılı donanım, seri protokol ve kurulum belgelerine yönlendirir.
-->

# DiffDrive Arduino Bridge

Bu çalışma alanı Arduino Mega2560 Pro Mini'den Jetson'a seri hat üzerinden
sensör ve encoder verisi aktarır. RPLidar sürücüsü proje içine kopyalanmaz;
Jetson'ın sistem geneline kurulu ROS 2 paketi kullanılır.

## Başlangıç

```bash
cd ~/DiffDrive_Slamtoolbox
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 run arduino_bridge serial_bridge
```

Donanımı bağlamadan önce `docs/serial-protocol.md` ve
`scripts/usb_serial/99-kasif-usb-serial.rules` dosyalarını okuyun.

## Dizinler

```text
arduino/                 Arduino firmware'i ve kart belgeleri
docs/                    Bağlantı ve seri veri sözleşmesi
scripts/usb_serial/      Jetson'da kalıcı seri cihaz adı için udev kuralları
src/arduino_bridge/      Arduino USB-seri ROS 2 köprüsü
src/robot_bringup/       Donanım, mapping, localization ve navigation launch'ları
```

Köprünün ROS 2 paket adı `arduino_bridge`'dir.

## Veri akışı

`Arduino -> USB-seri (/dev/arduino) -> arduino_bridge -> /odom, /imu/data,
/joint_states`

Detaylı mesaj biçimi: `docs/serial-protocol.md`.

## RPLidar sistem bağımlılığı

RPLidar sürücüsü Git deposuna dahil edilmez. Jetson'a bir kez kurulur:

```bash
sudo apt install ros-humble-rplidar-ros
```

`~/.bashrc` içindeki `source /opt/ros/humble/setup.bash` satırı, sürücüyü her
yeni terminalde kullanılabilir yapar. Donanım `/dev/rplidar` olarak görünür ve
sürücü `sensor_msgs/msg/LaserScan` verisini `/scan` konusuna yayınlar.
Modeline uygun başlatma komutları ve kurulum notları için `docs/rplidar.md`
dosyasını okuyun.

## Donanımı birlikte başlatma

Arduino ile RPLidar A1'i tek komutla başlatmak için:

```bash
ros2 launch robot_bringup hardware.launch.py
```

Paket yapısı ve sonraki mapping/localization/navigation adımları için
`docs/robot_bringup.md` dosyasını okuyun.
