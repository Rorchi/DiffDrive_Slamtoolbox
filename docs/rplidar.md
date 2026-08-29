# RPLidar kurulumu ve kullanım notu

## Neler yaptık?

1. Jetson'ın RPLidar USB-seri dönüştürücüsünü algıladığını doğruladık:

   ```text
   10c4:ea60 Silicon Labs CP210x UART Bridge
   ```

2. Udev kuralı bu cihaz için kalıcı port adı oluşturur:

   ```text
   /dev/rplidar -> /dev/ttyUSB0
   ```

   Böylece Arduino'nun `/dev/arduino` portu ile lidar portu karışmaz.

3. ROS 2 sürücüsünü proje içine koymak yerine Jetson'ın sistem geneline
   kurma kararı aldık. Kurulum komutu:

   ```bash
   sudo apt install ros-humble-rplidar-ros
   ```

   Paket `/opt/ros/humble` altında bulunur. Bu nedenle proje dizinine
   `rplidar_ros` klonlanmaz ve GitHub'a sürücü kaynak kodu gönderilmez.

4. `~/.bashrc` zaten aşağıdaki satırı içerir; her yeni terminalde sistem
   paketleri otomatik kullanılabilir olur:

   ```bash
   source /opt/ros/humble/setup.bash
   ```

## Doğrulama

```bash
lsusb
ls -l /dev/rplidar
ros2 pkg prefix rplidar_ros
```

Son komutun çıktısı `/opt/ros/humble` olmalıdır.

## Çalıştırma

Lidar modeline uygun launch dosyasını kullanın. A1 için örnek:

```bash
ros2 launch rplidar_ros rplidar_a1_launch.py \
  serial_port:=/dev/rplidar \
  serial_baudrate:=115200 \
  frame_id:=laser
```

Model A2/A3/S1/S2/S3/C1/T1 ise karşılık gelen `rplidar_<model>_launch.py`
dosyasını seçin. Baud hızı modele bağlıdır; yanlış baud hızıyla başlatmayın.

Veri kontrolü:

```bash
ros2 topic echo /scan --once
ros2 topic hz /scan
```

Beklenen konu `/scan`, mesaj türü `sensor_msgs/msg/LaserScan`'dir.
